"""Tests for server-run single-player trivia sessions and the legacy flow gate (spec 001)."""
import pytest
from uuid import uuid4
from datetime import datetime, UTC, timedelta

from app.main import app
from app.core.settings import settings
from app.models.user import User, UserRole
from app.models.trivia import (
    TriviaQuestion, TriviaSingleScore, TriviaSingleSession, TriviaSessionStatus,
    TriviaCategory, TriviaDifficulty, TriviaCorrectOption, TriviaQuestionType,
)
from app.services import trivia_session
from app.services.auth import get_current_user

T0 = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
POOL = 55


class Clock:
    def __init__(self, now):
        self.now = now

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock(monkeypatch):
    c = Clock(T0)
    monkeypatch.setattr(trivia_session, "_now", lambda: c.now)
    return c


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(settings, "trivia_legacy_single_enabled", True)
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def pool(db_session):
    for i in range(POOL):
        db_session.add(TriviaQuestion(
            category=TriviaCategory.old_testament, difficulty=TriviaDifficulty.challenger,
            question_text=f"Question {i}?", option_a=f"right {i}", option_b=f"wrong b{i}",
            option_c=f"wrong c{i}", option_d=f"wrong d{i}",
            correct_option=TriviaCorrectOption.a, question_type=TriviaQuestionType.multiple_choice,
        ))
    for i in range(3):
        db_session.add(TriviaQuestion(
            category=TriviaCategory.new_testament, difficulty=TriviaDifficulty.beginner,
            question_text=f"Easy {i}?", option_a="True", option_b="False",
            correct_option=TriviaCorrectOption.a, question_type=TriviaQuestionType.true_false,
        ))
    db_session.commit()


def _user(db, name="Player"):
    u = User(id=str(uuid4()), name=name, email=f"{name.lower()}-{uuid4().hex[:6]}@example.com",
             role=UserRole.apprentice, created_at=datetime.now(UTC))
    db.add(u)
    db.commit()
    return u


def _act_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _start(client, category="old_testament", difficulty="challenger"):
    r = client.post("/trivia/single/start", json={"category": category, "difficulty": difficulty})
    assert r.status_code == 200, r.text
    return r.json()


def _right_letter(db, state):
    """Find the shuffled letter holding the question's correct text (test-side grading)."""
    q = state["question"]
    real = db.get(TriviaQuestion, q["id"])
    correct_text = getattr(real, f"option_{real.correct_option.value}")
    return next(l for l in "abcd" if q.get(f"option_{l}") == correct_text)


def _wrong_letter(db, state):
    right = _right_letter(db, state)
    return next(l for l in "abcd" if l != right and state["question"].get(f"option_{l}"))


def _answer(client, state, selected, expect=200):
    r = client.post(f"/trivia/single/{state['session_id']}/answer",
                    json={"question_id": state["question"]["id"], "selected": selected})
    assert r.status_code == expect, r.text
    return r.json()


def _scores(db, user):
    db.expire_all()
    return db.query(TriviaSingleScore).filter_by(user_id=user.id).all()


# ---------- Full game, no answer leaks ----------

def test_full_game_never_leaks_answers_and_ends_when_pool_used(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _start(client)
    assert state["total_questions"] == POOL
    assert state["question_number"] == 1 and state["last_answer"] is None

    seen = set()
    for n in range(POOL):
        assert "correct_option" not in state["question"]
        assert state["question"]["id"] not in seen
        seen.add(state["question"]["id"])
        clock.advance(seconds=2)
        state = _answer(client, state, _right_letter(db_session, state))
        assert state["last_answer"]["correct"] is True
        if n < POOL - 1:
            assert state["status"] == "active"

    assert state["status"] == "finished" and state["question"] is None
    assert state["correct_count"] == POOL
    # 4×100 + 5×200 + 5×300 + 5×400 + 36×500
    assert state["score"] == 400 + 1000 + 1500 + 2000 + 36 * 500
    assert state["result"]["score"] == state["score"]
    [score] = _scores(db_session, user)
    assert score.verified is True and score.session_id == state["session_id"]
    assert score.streak_length == POOL


def test_score_follows_streak_multiplier(client, db_session, pool, clock):
    _act_as(_user(db_session))
    state = _start(client)
    expected = 0
    for n in range(1, 7):
        state = _answer(client, state, _right_letter(db_session, state))
        expected += 100 * (1 if n < 5 else 2)
        assert state["score"] == expected and state["streak"] == n


# ---------- Cheats refused ----------

def test_answer_for_other_question_is_rejected(client, db_session, pool, clock):
    _act_as(_user(db_session))
    state = _start(client)
    other = next(q.id for q in db_session.query(TriviaQuestion).all() if q.id != state["question"]["id"])
    r = client.post(f"/trivia/single/{state['session_id']}/answer",
                    json={"question_id": other, "selected": "a"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Answer is not for the current question"
    session = db_session.get(TriviaSingleSession, state["session_id"])
    db_session.refresh(session)
    assert session.answers == [] and session.current_index == 0


def test_late_answer_counts_as_wrong(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _start(client)
    clock.advance(seconds=33, milliseconds=1)
    state = _answer(client, state, _right_letter(db_session, state))
    assert state["last_answer"]["timed_out"] is True
    assert state["last_answer"]["correct"] is False
    assert state["status"] == "finished"
    assert _scores(db_session, user)[0].score == 0


def test_answer_inside_allowance_still_counts(client, db_session, pool, clock):
    _act_as(_user(db_session))
    state = _start(client)
    clock.advance(seconds=32)
    state = _answer(client, state, _right_letter(db_session, state))
    assert state["last_answer"]["correct"] is True and state["status"] == "active"


def test_wrong_answer_without_token_ends_game_and_reveals_answer(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _start(client)
    state = _answer(client, state, _right_letter(db_session, state))
    right = _right_letter(db_session, state)
    state = _answer(client, state, _wrong_letter(db_session, state))
    assert state["status"] == "finished"
    assert state["last_answer"]["correct_option"] == right
    assert state["result"]["score"] == 100
    scores = _scores(db_session, user)
    assert len(scores) == 1 and scores[0].verified is True


def test_finished_game_rejects_answers(client, db_session, pool, clock):
    _act_as(_user(db_session))
    state = _start(client)
    sid = state["session_id"]
    client.post(f"/trivia/single/{sid}/finish")
    r = client.post(f"/trivia/single/{sid}/answer",
                    json={"question_id": state["question"]["id"], "selected": "a"})
    assert r.status_code == 409 and r.json()["detail"] == "Game is over"
    r = client.post(f"/trivia/single/{sid}/grace", json={"use": True})
    assert r.status_code == 409


# ---------- Retries ----------

def test_retrying_last_answer_replays_without_regrading(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _start(client)
    first_q = dict(state)
    state = _answer(client, state, _right_letter(db_session, state))
    replay = _answer(client, first_q, "a")
    assert replay["score"] == state["score"] == 100
    assert replay["question"]["id"] == state["question"]["id"]
    assert replay["last_answer"] == state["last_answer"]


def test_retrying_game_ending_answer_replays_finished_state(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _start(client)
    before = dict(state)
    ended = _answer(client, state, _wrong_letter(db_session, state))
    assert ended["status"] == "finished"
    replay = _answer(client, before, _wrong_letter(db_session, before))
    assert replay["status"] == "finished" and replay["result"] == ended["result"]
    assert len(_scores(db_session, user)) == 1


# ---------- Grace tokens ----------

def _play_correct(client, db, state, n):
    for _ in range(n):
        state = _answer(client, state, _right_letter(db, state))
    return state


def test_grace_token_earned_and_used_keeps_streak(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _play_correct(client, db_session, _start(client), 10)
    assert state["grace_tokens"] == 1
    score_before = state["score"]

    retry_of = dict(state)
    state = _answer(client, state, _wrong_letter(db_session, state))
    assert state["status"] == "awaiting_grace" and state["question"] is None
    assert state["grace_expires_in_ms"] == 13000

    # retrying the answer that triggered grace replays (no 409)
    replay = _answer(client, retry_of, "b")
    assert replay["status"] == "awaiting_grace"

    # answering while a grace decision is pending is refused
    r = client.post(f"/trivia/single/{state['session_id']}/answer",
                    json={"question_id": 999999, "selected": "a"})
    assert r.status_code == 409 and r.json()["detail"] == "Grace decision pending"

    clock.advance(seconds=5)
    r = client.post(f"/trivia/single/{state['session_id']}/grace", json={"use": True})
    assert r.status_code == 200
    state = r.json()
    assert state["status"] == "active" and state["grace_tokens"] == 0 and state["grace_tokens_used"] == 1
    assert state["score"] == score_before
    state = _answer(client, state, _right_letter(db_session, state))
    assert state["streak"] == 11
    assert state["score"] == score_before + 300   # streak 11 → 3×


def test_grace_after_deadline_finishes(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _play_correct(client, db_session, _start(client), 10)
    state = _answer(client, state, _wrong_letter(db_session, state))
    clock.advance(seconds=13, milliseconds=1)
    r = client.post(f"/trivia/single/{state['session_id']}/grace", json={"use": True})
    assert r.status_code == 200 and r.json()["status"] == "finished"
    [score] = _scores(db_session, user)
    assert score.grace_tokens_used == 0


def test_grace_declined_finishes(client, db_session, pool, clock):
    _act_as(_user(db_session))
    state = _play_correct(client, db_session, _start(client), 10)
    state = _answer(client, state, _wrong_letter(db_session, state))
    r = client.post(f"/trivia/single/{state['session_id']}/grace", json={"use": False})
    assert r.json()["status"] == "finished"


def test_grace_without_pending_decision_is_409(client, db_session, pool, clock):
    _act_as(_user(db_session))
    state = _start(client)
    r = client.post(f"/trivia/single/{state['session_id']}/grace", json={"use": True})
    assert r.status_code == 409 and r.json()["detail"] == "No grace decision pending"


# ---------- Ownership, finish, lifecycle ----------

def test_other_users_session_is_404(client, db_session, pool, clock):
    owner, intruder = _user(db_session, "Owner"), _user(db_session, "Intruder")
    _act_as(owner)
    state = _start(client)
    _act_as(intruder)
    sid = state["session_id"]
    assert client.post(f"/trivia/single/{sid}/answer",
                       json={"question_id": state["question"]["id"], "selected": "a"}).status_code == 404
    assert client.post(f"/trivia/single/{sid}/grace", json={"use": True}).status_code == 404
    assert client.post(f"/trivia/single/{sid}/finish").status_code == 404


def test_finish_is_idempotent(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _play_correct(client, db_session, _start(client), 3)
    first = client.post(f"/trivia/single/{state['session_id']}/finish")
    second = client.post(f"/trivia/single/{state['session_id']}/finish")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() and first.json()["score"] == 300
    assert len(_scores(db_session, user)) == 1


def test_starting_new_game_finishes_unfinished_one(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    old = _play_correct(client, db_session, _start(client), 2)
    _start(client)
    db_session.expire_all()
    assert db_session.get(TriviaSingleSession, old["session_id"]).status == TriviaSessionStatus.finished
    assert [s.score for s in _scores(db_session, user)] == [200]


def test_no_questions_is_400(client, db_session, pool, clock):
    _act_as(_user(db_session))
    r = client.post("/trivia/single/start", json={"category": "theology_doctrine", "difficulty": "expert"})
    assert r.status_code == 400 and r.json()["detail"] == "No questions available"


def test_unknown_category_is_422(client, db_session, pool, clock):
    _act_as(_user(db_session))
    r = client.post("/trivia/single/start", json={"category": "nope", "difficulty": "expert"})
    assert r.status_code == 422


def test_random_category_and_true_false(client, db_session, pool, clock):
    _act_as(_user(db_session))
    state = _start(client, category="random", difficulty="beginner")
    assert state["total_questions"] == 3
    q = state["question"]
    assert q["question_type"] == "true_false" and q["option_c"] is None
    state = _answer(client, state, _right_letter(db_session, state))
    assert state["last_answer"]["correct"] is True


def test_score_is_dated_by_game_start(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _play_correct(client, db_session, _start(client), 1)
    clock.advance(hours=3)
    client.post(f"/trivia/single/{state['session_id']}/finish")
    [score] = _scores(db_session, user)
    assert trivia_session._aware(score.created_at) == T0


def test_finish_stale_closes_game_once_question_expires(client, db_session, pool, clock):
    """Leaving the app doesn't pause the clock: an expired question ends the game."""
    user = _user(db_session)
    _act_as(user)
    state = _play_correct(client, db_session, _start(client), 2)
    clock.advance(seconds=20)
    assert trivia_session.finish_stale(db_session, now=clock.now) == 0
    clock.advance(seconds=14)   # 34 s after the question was served, no grace token
    assert trivia_session.finish_stale(db_session, now=clock.now) == 1
    [score] = _scores(db_session, user)
    assert score.score == 200 and score.session_id == state["session_id"]


def test_finish_stale_waits_for_grace_window_when_player_has_token(client, db_session, pool, clock):
    _act_as(_user(db_session))
    _play_correct(client, db_session, _start(client), 10)
    clock.advance(seconds=40)   # past the question, still inside the grace window they'd get
    assert trivia_session.finish_stale(db_session, now=clock.now) == 0
    clock.advance(seconds=7)    # 47 s
    assert trivia_session.finish_stale(db_session, now=clock.now) == 1


def test_late_answer_with_token_gets_rest_of_grace_window(client, db_session, pool, clock):
    _act_as(_user(db_session))
    state = _play_correct(client, db_session, _start(client), 10)
    clock.advance(seconds=35)
    state = _answer(client, state, _right_letter(db_session, state))
    assert state["last_answer"]["timed_out"] is True
    assert state["status"] == "awaiting_grace"
    assert state["grace_expires_in_ms"] == 8000   # window started at the 30 s mark


def test_away_past_grace_window_ends_game_without_offer(client, db_session, pool, clock):
    """Backgrounding to look up the answer and coming back doesn't work, even with a token."""
    user = _user(db_session)
    _act_as(user)
    state = _play_correct(client, db_session, _start(client), 10)
    clock.advance(seconds=44)
    state = _answer(client, state, _right_letter(db_session, state))
    assert state["last_answer"]["timed_out"] is True and state["last_answer"]["correct"] is False
    assert state["status"] == "finished" and state["grace_tokens"] == 1
    [score] = _scores(db_session, user)
    assert score.grace_tokens_used == 0 and score.correct_count == 10


def test_finish_stale_closes_expired_grace(client, db_session, pool, clock):
    user = _user(db_session)
    _act_as(user)
    state = _play_correct(client, db_session, _start(client), 10)
    _answer(client, state, _wrong_letter(db_session, state))
    clock.advance(seconds=14)
    assert trivia_session.finish_stale(db_session, now=clock.now) == 1


# ---------- Legacy flow ----------

def test_legacy_flow_works_but_scores_are_unverified(client, db_session, pool):
    user = _user(db_session)
    _act_as(user)
    r = client.get("/trivia/questions/draw?category=old_testament&difficulty=challenger&count=5")
    assert r.status_code == 200 and len(r.json()) == 5
    q = r.json()[0]
    r = client.post("/trivia/single/submit", json={
        "category": "old_testament", "difficulty": "challenger", "grace_tokens_used": 0,
        "answers": [{"question_id": q["id"], "selected": q["correct_option"], "time_used_ms": 1000}],
    })
    assert r.status_code == 200 and r.json()["score"] == 100
    [score] = _scores(db_session, user)
    assert score.verified is False and score.session_id is None


def test_legacy_flow_disabled_returns_426(client, db_session, pool, monkeypatch):
    monkeypatch.setattr(settings, "trivia_legacy_single_enabled", False)
    user = _user(db_session)
    _act_as(user)
    r = client.get("/trivia/questions/draw?category=old_testament&difficulty=challenger")
    assert r.status_code == 426
    assert r.json()["detail"] == "Please update the app to keep playing trivia."
    r = client.post("/trivia/single/submit", json={
        "category": "old_testament", "difficulty": "challenger", "grace_tokens_used": 0,
        "answers": [{"question_id": 1, "selected": "a", "time_used_ms": 1000}],
    })
    assert r.status_code == 426
    assert _scores(db_session, user) == []
