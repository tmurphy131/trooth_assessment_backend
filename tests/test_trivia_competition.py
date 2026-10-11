"""Tests for trivia leaderboard competitions: window, eligibility, ties, finalization."""
import pytest
from uuid import uuid4
from datetime import datetime, UTC, timedelta

from app.main import app
from app.core.settings import settings
from app.models.user import User, UserRole
from app.models.trivia import (
    TriviaCompetition, TriviaCompetitionWinner, TriviaSingleScore,
    TriviaCategory, TriviaDifficulty, TriviaQuestion, TriviaCorrectOption, TriviaSingleSession,
)
from app.services import trivia_competition as comp_svc
from app.services import shopify_admin
from app.services.auth import get_current_user

START = datetime(2026, 11, 1, 4, 0, tzinfo=UTC)
END = datetime(2026, 12, 31, 5, 0, tzinfo=UTC)
DURING = START + timedelta(days=10)
AFTER = END + timedelta(hours=1)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(settings, "trivia_competition_excluded_emails", [])
    monkeypatch.setattr(settings, "trivia_competition_admin_emails", ["admin@example.com"])
    monkeypatch.setattr(settings, "shopify_client_id", "")
    monkeypatch.setattr(settings, "shopify_client_secret", "")
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def pushes(monkeypatch):
    sent = []
    monkeypatch.setattr(comp_svc, "notify_trivia_competition_won",
                        lambda db, user_id, place, name: sent.append((user_id, place)))
    return sent


@pytest.fixture
def emails(monkeypatch):
    sent = []
    real = comp_svc.email_svc.send_trivia_prize_email

    def _record(db, user, winner, comp, label):
        sent.append((user.id, winner.place, winner.discount_code))
        return real(db, user, winner, comp, label)

    monkeypatch.setattr(comp_svc.email_svc, "send_trivia_prize_email", _record)
    return sent


def _set_now(monkeypatch, now):
    monkeypatch.setattr(comp_svc, "_now", lambda: now)


def _act_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _competition(db):
    comp = TriviaCompetition(
        slug="launch-test", name="60-Day Launch Competition", difficulty="challenger",
        starts_at=START, ends_at=END, code_valid_days=90,
        prizes=[
            {"place": 1, "amount": 59, "label": "$59 off — any merch item free"},
            {"place": 2, "amount": 30, "label": "$30 off ONLY BLV merch"},
            {"place": 3, "amount": 15, "label": "$15 off ONLY BLV merch"},
        ],
    )
    db.add(comp)
    db.commit()
    return comp


def _user(db, name, role=UserRole.apprentice, email=None):
    u = User(id=str(uuid4()), name=name, email=email or f"{name.lower()}-{uuid4().hex[:6]}@example.com",
             role=role, created_at=datetime.now(UTC))
    db.add(u)
    db.commit()
    return u


def _score(db, user, score, at=DURING, difficulty=TriviaDifficulty.challenger, verified=True):
    db.add(TriviaSingleScore(
        user_id=user.id, category=TriviaCategory.old_testament, difficulty=difficulty,
        score=score, streak_length=score // 100, correct_count=score // 100, created_at=at,
        verified=verified,
    ))
    db.commit()


def test_standings_ignore_unverified_scores(db_session):
    comp = _competition(db_session)
    a, b = _user(db_session, "Alice"), _user(db_session, "Bob")
    _score(db_session, a, 9900, verified=False)   # legacy client-graded submit
    _score(db_session, a, 400)
    _score(db_session, b, 700)

    standings = comp_svc.compute_standings(db_session, comp)
    assert [(s.user.id, s.score) for s in standings] == [(b.id, 700), (a.id, 400)]


def _open_session(db, user, started_at, last_activity_at, served_at=None):
    db.add(TriviaQuestion(
        category=TriviaCategory.old_testament, difficulty=TriviaDifficulty.challenger,
        question_text="Q?", option_a="A", option_b="B", option_c="C", option_d="D",
        correct_option=TriviaCorrectOption.a,
    ))
    db.flush()
    s = TriviaSingleSession(
        user_id=user.id, category=TriviaCategory.old_testament, difficulty=TriviaDifficulty.challenger,
        question_ids=[1], answers=[
            {"index": 0, "question_id": 1, "selected": "a", "correct": True, "correct_option": "a",
             "timed_out": False, "graced": False, "elapsed_ms": 1000},
        ],
        current_index=1, score=100, streak=1, max_streak=1, correct_count=1,
        created_at=started_at, last_activity_at=last_activity_at, current_served_at=served_at,
    )
    db.add(s)
    db.commit()
    return s


def test_finalize_waits_for_game_in_progress_then_counts_it(db_session, pushes, emails):
    comp = _competition(db_session)
    player = _user(db_session, "Late")
    started = END - timedelta(minutes=10)
    check = END + timedelta(minutes=5)
    session = _open_session(db_session, player, started_at=started,
                            last_activity_at=check - timedelta(seconds=10),
                            served_at=check - timedelta(seconds=10))

    # Still mid-question when the job runs: wait
    first = comp_svc.finalize_competition(db_session, comp.id, now=check)
    assert first["status"] == "waiting_for_games"

    # A minute later the question has expired: closed, dated by its start, and it wins
    result = comp_svc.finalize_competition(db_session, comp.id, now=check + timedelta(minutes=1))
    assert result["status"] == "finalized"
    db_session.expire_all()
    score = db_session.query(TriviaSingleScore).filter_by(session_id=session.id).one()
    assert score.verified is True
    assert comp_svc._aware(score.created_at) == started
    assert [w["display_name"] for w in result["winners"]] == ["Late"]


# ---------- Standings ----------

def test_standings_only_count_window_and_difficulty(db_session):
    comp = _competition(db_session)
    a, b = _user(db_session, "Alice"), _user(db_session, "Bob")
    _score(db_session, a, 9000, at=START - timedelta(minutes=1))   # before window
    _score(db_session, a, 9000, at=END)                              # end is exclusive
    _score(db_session, a, 9000, difficulty=TriviaDifficulty.expert)  # wrong difficulty
    _score(db_session, a, 500)
    _score(db_session, b, 800, at=START)                             # start is inclusive

    standings = comp_svc.compute_standings(db_session, comp)
    assert [(s.user.id, s.score, s.rank) for s in standings] == [(b.id, 800, 1), (a.id, 500, 2)]


def test_standings_use_best_score_and_share_rank_on_ties(db_session):
    comp = _competition(db_session)
    a, b, c, d = (_user(db_session, n) for n in ("Ann", "Ben", "Cal", "Dee"))
    _score(db_session, a, 300)
    _score(db_session, a, 1000)
    _score(db_session, b, 1000)
    _score(db_session, c, 700)
    _score(db_session, d, 400)

    ranks = {s.user.id: s.rank for s in comp_svc.compute_standings(db_session, comp)}
    assert ranks == {a.id: 1, b.id: 1, c.id: 3, d.id: 4}


def test_admins_and_excluded_emails_are_not_eligible(db_session, monkeypatch):
    monkeypatch.setattr(settings, "trivia_competition_excluded_emails", ["@onlyblv.com", "tester@example.com"])
    comp = _competition(db_session)
    admin = _user(db_session, "Admin", role=UserRole.admin)
    staff = _user(db_session, "Staff", email="Staff@OnlyBLV.com")
    tester = _user(db_session, "Tester", email="tester@example.com")
    player = _user(db_session, "Player")
    for u, s in ((admin, 5000), (staff, 4000), (tester, 3000), (player, 100)):
        _score(db_session, u, s)

    standings = comp_svc.compute_standings(db_session, comp)
    assert [(s.user.id, s.rank) for s in standings] == [(player.id, 1)]


# ---------- GET /trivia/competition ----------

def test_competition_endpoint_status_transitions(client, db_session, monkeypatch):
    _competition(db_session)
    me, other = _user(db_session, "Me"), _user(db_session, "Other")
    _score(db_session, me, 600)
    _score(db_session, other, 900)
    _act_as(me)

    _set_now(monkeypatch, START - timedelta(days=29))
    body = client.get("/trivia/competition").json()
    assert body["status"] == "upcoming"
    assert body["standings"] == [] and body["my_rank"] is None
    assert [p["amount"] for p in body["prizes"]] == [59, 30, 15]

    _set_now(monkeypatch, DURING)
    body = client.get("/trivia/competition").json()
    assert body["status"] == "active"
    assert [s["display_name"] for s in body["standings"]] == ["Other", "Me"]
    assert body["my_rank"] == 2 and body["my_score"] == 600

    _set_now(monkeypatch, AFTER)
    body = client.get("/trivia/competition").json()
    assert body["status"] == "ended"
    assert body["winners"] == [] and body["finalized"] is False


def test_competition_endpoint_returns_null_without_competitions(client, db_session):
    _act_as(_user(db_session, "Lonely"))
    r = client.get("/trivia/competition")
    assert r.status_code == 200
    assert r.json() is None


def test_ended_competition_shows_winners_but_code_only_to_owner(client, db_session, monkeypatch, pushes, emails):
    comp = _competition(db_session)
    winner, loser = _user(db_session, "Winner"), _user(db_session, "Loser")
    _score(db_session, winner, 2000)
    comp_svc.finalize_competition(db_session, comp.id, now=AFTER)
    _set_now(monkeypatch, AFTER)

    _act_as(loser)
    body = client.get("/trivia/competition").json()
    assert body["finalized"] is True
    assert body["winners"] == [{"place": 1, "display_name": "Winner", "score": 2000, "is_me": False}]
    assert body["my_prize"] is None
    assert "DRYRUN" not in str(body)

    _act_as(winner)
    body = client.get("/trivia/competition").json()
    assert body["winners"][0]["is_me"] is True
    assert body["my_prize"]["discount_code"].startswith("DRYRUN-TROOTH-1ST-")
    assert body["my_prize"]["label"] == "$59 off — any merch item free"


# ---------- Finalization ----------

def test_finalize_is_noop_before_end(db_session, pushes, emails):
    comp = _competition(db_session)
    _score(db_session, _user(db_session, "Early"), 1000)
    result = comp_svc.finalize_competition(db_session, comp.id, now=END - timedelta(seconds=1))
    assert result["status"] == "not_ended"
    assert db_session.query(TriviaCompetitionWinner).count() == 0
    assert emails == []


def test_finalize_awards_ties_and_is_idempotent(db_session, monkeypatch, pushes, emails):
    comp = _competition(db_session)
    a, b, c, d = (_user(db_session, n) for n in ("Ann", "Ben", "Cal", "Dee"))
    _score(db_session, a, 1000)
    _score(db_session, b, 1000)
    _score(db_session, c, 700)
    _score(db_session, d, 400)

    created = []
    real_create = shopify_admin.create_prize_code

    def _count(**kw):
        created.append(kw["amount"])
        return real_create(**kw)

    monkeypatch.setattr(shopify_admin, "create_prize_code", _count)

    result = comp_svc.finalize_competition(db_session, comp.id, now=AFTER)
    assert result["status"] == "finalized"
    winners = {w.user_id: w for w in db_session.query(TriviaCompetitionWinner).all()}
    assert {uid: w.place for uid, w in winners.items()} == {a.id: 1, b.id: 1, c.id: 3}
    assert sorted(created) == [15, 59, 59]
    assert len({w.discount_code for w in winners.values()}) == 3
    assert all(w.emailed_at and w.pushed_at for w in winners.values())
    expected_expiry = (END + timedelta(days=90)).replace(tzinfo=None)
    assert all(w.code_expires_at.replace(tzinfo=None) == expected_expiry for w in winners.values())
    assert sorted(p for _, p in pushes) == [1, 1, 3]

    # Second run: nothing new
    again = comp_svc.finalize_competition(db_session, comp.id, now=AFTER + timedelta(hours=1))
    assert again["status"] == "already_finalized"
    assert len(created) == 3 and len(emails) == 3 and len(pushes) == 3


def test_finalize_retries_failed_shopify_call(db_session, monkeypatch, pushes, emails):
    comp = _competition(db_session)
    a, b = _user(db_session, "Ann"), _user(db_session, "Ben")
    _score(db_session, a, 1000)
    _score(db_session, b, 500)

    real_create = shopify_admin.create_prize_code
    calls = {"n": 0}

    def _flaky(**kw):
        calls["n"] += 1
        if kw["place"] == 2 and calls["n"] <= 2:
            raise shopify_admin.ShopifyAdminError("boom")
        return real_create(**kw)

    monkeypatch.setattr(shopify_admin, "create_prize_code", _flaky)

    first = comp_svc.finalize_competition(db_session, comp.id, now=AFTER)
    assert first["status"] == "incomplete"
    assert len(first["errors"]) == 1
    assert [e[1] for e in emails] == [1]   # 1st place still got their code + email

    second = comp_svc.finalize_competition(db_session, comp.id, now=AFTER + timedelta(hours=1))
    assert second["status"] == "finalized"
    assert sorted(e[1] for e in emails) == [1, 2]   # 1st place not emailed twice
    assert db_session.query(TriviaCompetitionWinner).count() == 2


def test_finalize_with_no_players_finalizes_empty(db_session, pushes, emails):
    comp = _competition(db_session)
    result = comp_svc.finalize_competition(db_session, comp.id, now=AFTER)
    assert result["status"] == "finalized"
    assert result["winners"] == []


def test_scheduled_endpoint_requires_cron_secret_and_finalizes(client, db_session, monkeypatch, pushes, emails):
    from app.routes import scheduled_tasks
    comp = _competition(db_session)
    _score(db_session, _user(db_session, "Champ"), 3000)
    _set_now(monkeypatch, AFTER)

    assert client.post("/scheduled/trivia-competition-finalize").status_code == 403

    r = client.post("/scheduled/trivia-competition-finalize",
                    headers={"X-Cron-Secret": "test-cron-secret"})
    assert r.status_code == 200, r.text
    assert r.json()["results"][0]["status"] == "finalized"
    db_session.expire_all()
    assert db_session.get(TriviaCompetition, comp.id).finalized_at is not None


# ---------- Shopify client ----------

def test_shopify_refuses_dry_run_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(shopify_admin.ShopifyAdminError):
        shopify_admin.create_prize_code(place=1, amount=59, title="t", starts_at=START, ends_at=END)


def test_prize_input_is_fixed_amount_single_use():
    payload = shopify_admin.build_prize_input("TROOTH-1ST-ABC123", "t", 59, START, END)
    assert payload["customerGets"]["value"] == {"discountAmount": {"amount": "59.00", "appliesOnEachItem": False}}
    assert payload["usageLimit"] == 1 and payload["appliesOncePerCustomer"] is True
    assert payload["customerGets"]["items"]["collections"]["add"] == [settings.shopify_prize_collection_id]
