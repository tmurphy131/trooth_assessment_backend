"""Multiplayer challenge rules from spec 001: premium-only creation, current-question answers."""
import pytest
from uuid import uuid4
from datetime import datetime, UTC, timedelta

from app.main import app
from app.models.user import User, UserRole, SubscriptionTier
from app.models.trivia import (
    TriviaQuestion, TriviaChallenge, TriviaChallengeStatus,
    TriviaCategory, TriviaDifficulty, TriviaCorrectOption,
)
from app.routes import trivia as trivia_routes
from app.services import trivia as trivia_svc
from app.services.auth import get_current_user


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def pushes(monkeypatch):
    sent = []
    for name in ("notify_trivia_challenge_received", "notify_trivia_question_unlocked",
                 "notify_trivia_challenge_result", "notify_trivia_nudge"):
        monkeypatch.setattr(trivia_routes, name, lambda *a, _n=name, **k: sent.append(_n))
    return sent


@pytest.fixture
def questions(db_session):
    for i in range(25):
        db_session.add(TriviaQuestion(
            category=TriviaCategory.old_testament, difficulty=TriviaDifficulty.beginner,
            question_text=f"Q{i}?", option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option=TriviaCorrectOption.a,
        ))
    db_session.commit()


def _user(db, name, tier=SubscriptionTier.free, expires_at=None, role=UserRole.mentor):
    u = User(id=str(uuid4()), name=name, email=f"{name.lower()}-{uuid4().hex[:6]}@example.com",
             role=role, created_at=datetime.now(UTC),
             subscription_tier=tier, subscription_expires_at=expires_at)
    db.add(u)
    db.commit()
    return u


def _act_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _create(client, opponent):
    return client.post("/trivia/challenges", json={
        "challenged_email": opponent.email, "category": "old_testament",
        "difficulty": "beginner", "num_questions": 20,
    })


# ---------- Premium-only creation ----------

def test_free_user_cannot_create_challenge(client, db_session, questions, pushes):
    free, opponent = _user(db_session, "Free"), _user(db_session, "Opp")
    _act_as(free)
    r = _create(client, opponent)
    assert r.status_code == 403
    assert r.json()["detail"]["error"] == "premium_required"
    assert db_session.query(TriviaChallenge).count() == 0
    assert pushes == []


def test_expired_premium_cannot_create_challenge(client, db_session, questions, pushes):
    lapsed = _user(db_session, "Lapsed", tier=SubscriptionTier.mentor_premium,
                   expires_at=datetime.now(UTC) - timedelta(days=1))
    _act_as(lapsed)
    assert _create(client, _user(db_session, "Opp")).status_code == 403


@pytest.mark.parametrize("tier,role", [
    (SubscriptionTier.mentor_premium, UserRole.mentor),
    (SubscriptionTier.apprentice_premium, UserRole.apprentice),
    (SubscriptionTier.mentor_gifted, UserRole.apprentice),
])
def test_premium_tiers_can_create_challenge(client, db_session, questions, pushes, tier, role):
    _act_as(_user(db_session, "Prem", tier=tier, role=role))
    r = _create(client, _user(db_session, "Opp"))
    assert r.status_code == 200, r.text
    assert pushes == ["notify_trivia_challenge_received"]


def test_admin_can_create_challenge(client, db_session, questions, pushes):
    _act_as(_user(db_session, "Admin", role=UserRole.admin))
    assert _create(client, _user(db_session, "Opp")).status_code == 200


def test_free_challenged_user_can_play_to_completion(client, db_session, questions, pushes):
    premium = _user(db_session, "Prem", tier=SubscriptionTier.mentor_premium)
    free = _user(db_session, "Free")
    _act_as(premium)
    challenge_id = _create(client, free).json()["id"]

    _act_as(free)
    assert client.post(f"/trivia/challenges/{challenge_id}/accept").status_code == 200
    assert client.post(f"/trivia/challenges/{challenge_id}/nudge").status_code == 200

    challenge = db_session.get(TriviaChallenge, challenge_id)
    for qid in list(challenge.question_ids):
        for player in (premium, free):
            _act_as(player)
            r = client.post(f"/trivia/challenges/{challenge_id}/answer",
                            json={"answer": {"question_id": qid, "selected": "a", "time_used_ms": 1000}})
            assert r.status_code == 200, r.text
    db_session.expire_all()
    assert db_session.get(TriviaChallenge, challenge_id).status == TriviaChallengeStatus.complete


def test_free_challenged_user_can_forfeit(client, db_session, questions, pushes):
    premium, free = _user(db_session, "Prem", tier=SubscriptionTier.mentor_premium), _user(db_session, "Free")
    _act_as(premium)
    challenge_id = _create(client, free).json()["id"]
    _act_as(free)
    client.post(f"/trivia/challenges/{challenge_id}/accept")
    assert client.post(f"/trivia/challenges/{challenge_id}/forfeit").status_code == 200


# ---------- Current-question check ----------

def _active_challenge(db, a, b, question_ids):
    c = TriviaChallenge(
        challenger_id=a.id, challenged_id=b.id, category=TriviaCategory.old_testament,
        difficulty=TriviaDifficulty.beginner, num_questions=len(question_ids),
        question_ids=question_ids, challenger_answers=[], challenged_answers=[],
        status=TriviaChallengeStatus.active,
    )
    db.add(c)
    db.commit()
    return c


def test_answer_for_other_question_is_rejected(client, db_session, questions, pushes):
    a, b = _user(db_session, "A"), _user(db_session, "B")
    ids = [q.id for q in db_session.query(TriviaQuestion).limit(20)]
    c = _active_challenge(db_session, a, b, ids)
    _act_as(a)
    r = client.post(f"/trivia/challenges/{c.id}/answer",
                    json={"answer": {"question_id": ids[1], "selected": "a", "time_used_ms": 1000}})
    assert r.status_code == 400 and r.json()["detail"] == "Answer is not for the current question"
    db_session.expire_all()
    assert db_session.get(TriviaChallenge, c.id).challenger_answers == []

    r = client.post(f"/trivia/challenges/{c.id}/answer",
                    json={"answer": {"question_id": ids[0], "selected": "a", "time_used_ms": 1000}})
    assert r.status_code == 200


def test_time_used_is_clamped(client, db_session, questions, pushes):
    a, b = _user(db_session, "A"), _user(db_session, "B")
    ids = [q.id for q in db_session.query(TriviaQuestion).limit(20)]
    c = _active_challenge(db_session, a, b, ids)
    _act_as(a)
    client.post(f"/trivia/challenges/{c.id}/answer",
                json={"answer": {"question_id": ids[0], "selected": "a", "time_used_ms": -5}})
    _act_as(b)
    client.post(f"/trivia/challenges/{c.id}/answer",
                json={"answer": {"question_id": ids[0], "selected": "a", "time_used_ms": 99999}})
    db_session.expire_all()
    c = db_session.get(TriviaChallenge, c.id)
    assert c.challenger_answers[0]["time_used_ms"] == 0
    assert c.challenged_answers[0]["time_used_ms"] == 30000


# ---------- Expiry job (existing bug: returned int, route called len()) ----------

def test_expire_stale_challenges_returns_ids(db_session, questions):
    a, b = _user(db_session, "A"), _user(db_session, "B")
    ids = [q.id for q in db_session.query(TriviaQuestion).limit(20)]
    stale = _active_challenge(db_session, a, b, ids)
    stale.last_activity_at = datetime.now(UTC) - timedelta(days=8)
    fresh = _active_challenge(db_session, a, b, ids)
    db_session.commit()
    assert trivia_svc.expire_stale_challenges(db_session) == [stale.id]
    db_session.expire_all()
    assert db_session.get(TriviaChallenge, fresh.id).status == TriviaChallengeStatus.active


def test_trivia_expiry_endpoint_reports_expired_and_finished(client, db_session, questions):
    from app.routes import scheduled_tasks
    a, b = _user(db_session, "A"), _user(db_session, "B")
    ids = [q.id for q in db_session.query(TriviaQuestion).limit(20)]
    stale = _active_challenge(db_session, a, b, ids)
    stale.last_activity_at = datetime.now(UTC) - timedelta(days=8)
    db_session.commit()

    r = client.post("/scheduled/trivia-expiry", headers={"X-Cron-Secret": scheduled_tasks.CRON_SECRET})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["expired_count"] == 1 and body["expired_ids"] == [stale.id]
    assert body["finished_sessions"] == 0
