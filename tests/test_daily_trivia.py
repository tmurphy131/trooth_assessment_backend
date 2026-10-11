"""Tests for the daily trivia question, streaks, rewards, reminders and timezone (spec 002)."""
import pytest
from uuid import uuid4
from datetime import date, datetime, UTC, timedelta

from app.main import app
from app.core.settings import settings
from app.models.user import User, UserRole
from app.models.device_token import DeviceToken, DevicePlatform
from app.models.trivia import (
    TriviaQuestion, TriviaCategory, TriviaDifficulty, TriviaCorrectOption, TriviaQuestionType,
)
from app.models.daily_trivia import (
    DailyTriviaQuestion, DailyTriviaAnswer, DailyTriviaStreak, DailyTriviaReward, DailyTriviaRewardStatus,
)
from app.services import daily_trivia as daily_svc
from app.services import shopify_admin
from app.services.shopify_admin import PrizeCode
from app.services.auth import get_current_user
from app.services.account_deletion import _clear_shared_user_references

# 15:00 UTC on Nov 5 2026 is 10:00 in New York (EST, UTC-5)
T0 = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
D0 = date(2026, 11, 5)
CRON = {"X-Cron-Secret": "test-cron-secret"}


class Clock:
    def __init__(self, now):
        self.now = now

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock(monkeypatch):
    c = Clock(T0)
    monkeypatch.setattr(daily_svc, "_now", lambda: c.now)
    return c


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(settings, "shopify_client_id", "")
    monkeypatch.setattr(settings, "shopify_client_secret", "")
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def pushes(monkeypatch):
    sent = {"reward": [], "reminder": []}
    monkeypatch.setattr(daily_svc, "notify_daily_trivia_reward",
                        lambda db, user_id, tier, percent: sent["reward"].append((user_id, tier, percent)))
    monkeypatch.setattr(daily_svc, "notify_daily_trivia_reminder",
                        lambda db, user_id, streak, cat, diff, d: sent["reminder"].append((user_id, streak, d)))
    return sent


@pytest.fixture
def emails(monkeypatch):
    sent = []
    real = daily_svc.email_svc.send_daily_trivia_reward_email

    def _record(db, user, reward, replaced_percent=None):
        sent.append((user.id, reward.tier, reward.percent, reward.discount_code, replaced_percent))
        return real(db, user, reward, replaced_percent=replaced_percent)

    monkeypatch.setattr(daily_svc.email_svc, "send_daily_trivia_reward_email", _record)
    return sent


@pytest.fixture
def shop(monkeypatch):
    """Fake Shopify that hands out real-looking discount ids and records deactivations."""
    state = {"created": [], "deactivated": [], "fail": False}

    def _create(tier, percent, title, starts_at, ends_at):
        if state["fail"]:
            raise shopify_admin.ShopifyAdminError("store down")
        n = len(state["created"]) + 1
        state["created"].append((tier, percent))
        return PrizeCode(code=f"TROOTH-STREAK{tier}-CODE{n}", discount_id=f"gid://shopify/DiscountCodeNode/{n}")

    monkeypatch.setattr(shopify_admin, "create_percentage_code", _create)
    monkeypatch.setattr(shopify_admin, "deactivate_code", lambda discount_id: state["deactivated"].append(discount_id))
    return state


@pytest.fixture
def bank(db_session):
    """Two questions per category/level pair, plus ones the daily question must never use."""
    for cat in daily_svc.DAILY_CATEGORIES:
        for diff in daily_svc.DAILY_DIFFICULTIES:
            for i in range(2):
                db_session.add(TriviaQuestion(
                    category=cat, difficulty=diff,
                    question_text=f"{cat.value} {diff.value} {i}?", option_a="right", option_b="wrong b",
                    option_c="wrong c", option_d="wrong d", correct_option=TriviaCorrectOption.a,
                    question_type=TriviaQuestionType.multiple_choice,
                ))
    db_session.add(TriviaQuestion(
        category=TriviaCategory.old_testament, difficulty=TriviaDifficulty.expert,
        question_text="Expert?", option_a="right", option_b="wrong", correct_option=TriviaCorrectOption.a,
        question_type=TriviaQuestionType.true_false,
    ))
    db_session.add(TriviaQuestion(
        category=TriviaCategory.random, difficulty=TriviaDifficulty.beginner,
        question_text="Random bucket?", option_a="right", option_b="wrong", correct_option=TriviaCorrectOption.a,
        question_type=TriviaQuestionType.true_false,
    ))
    db_session.add(TriviaQuestion(
        category=TriviaCategory.new_testament, difficulty=TriviaDifficulty.beginner,
        question_text="Unapproved?", option_a="right", option_b="wrong", correct_option=TriviaCorrectOption.a,
        question_type=TriviaQuestionType.true_false, is_approved=False,
    ))
    db_session.commit()


def _user(db, name="Player", tz=None, push=True, device=False):
    u = User(id=str(uuid4()), name=name, email=f"{name.lower()}-{uuid4().hex[:6]}@example.com",
             role=UserRole.apprentice, created_at=datetime.now(UTC), timezone=tz, push_enabled=push)
    db.add(u)
    if device:
        db.add(DeviceToken(user_id=u.id, fcm_token=f"tok-{uuid4().hex}", platform=DevicePlatform.ios))
    db.commit()
    return u


def _act_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _correct(db, d=D0):
    return db.query(DailyTriviaQuestion).filter(DailyTriviaQuestion.date == d).one().correct_option


def _wrong(db, d=D0):
    q = db.query(DailyTriviaQuestion).filter(DailyTriviaQuestion.date == d).one()
    return next(k for k, v in q.options.items() if v is not None and k != q.correct_option)


def _answer(client, db, user, correct=True, d=D0):
    _act_as(user)
    client.get("/trivia/daily/today")
    option = _correct(db, d) if correct else _wrong(db, d)
    return client.post("/trivia/daily/today/answer", json={"question_date": d.isoformat(), "option": option})


def _set_streak(db, user, current, last=D0 - timedelta(days=1), perfect=True, freezes=0, tiers=None,
                started=None):
    s = DailyTriviaStreak(
        user_id=user.id, current_streak=current, longest_streak=current, last_answered_date=last,
        streak_started_on=started or (last - timedelta(days=current - 1)), freezes_available=freezes,
        perfect_run=perfect, freeze_dates=[], tiers_earned=tiers or [],
    )
    db.add(s)
    db.commit()
    return s


# ---------- US1: today's question ----------

def test_same_question_for_everyone_and_no_answer_leak(client, db_session, bank, clock):
    a, b = _user(db_session, "Ann"), _user(db_session, "Ben")
    _act_as(a)
    ra = client.get("/trivia/daily/today")
    _act_as(b)
    rb = client.get("/trivia/daily/today")
    assert ra.status_code == rb.status_code == 200
    assert ra.json()["question"] == rb.json()["question"]
    q = ra.json()["question"]
    assert q["date"] == D0.isoformat()
    assert "correct_option" not in q
    assert "right" in [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
    assert ra.json()["answer"] is None
    assert db_session.query(DailyTriviaQuestion).count() == 1


def test_question_is_beginner_or_challenger_in_a_real_category(client, db_session, bank, clock):
    for i in range(20):
        row = daily_svc.get_or_create_question(db_session, D0 + timedelta(days=i))
        assert row.category in daily_svc.DAILY_CATEGORIES
        assert row.difficulty in daily_svc.DAILY_DIFFICULTIES
        assert row.question_text not in ("Expert?", "Random bucket?", "Unapproved?")
    out = daily_svc.question_out(row)
    assert out["category_label"] in daily_svc.CATEGORY_LABELS.values()
    assert out["difficulty_label"] in ("Beginner", "Challenger")


def test_no_repeat_until_bank_exhausted_then_least_recent(db_session, bank):
    pool = 4 * 2 * 2
    used = [daily_svc.get_or_create_question(db_session, D0 + timedelta(days=i)).question_id for i in range(pool)]
    assert len(set(used)) == pool
    # Bank exhausted inside the 180-day window: reuse the one used longest ago
    again = daily_svc.get_or_create_question(db_session, D0 + timedelta(days=pool))
    assert again.question_id == used[0]


def test_answer_reveals_correct_option_and_only_once(client, db_session, bank, clock):
    u = _user(db_session)
    r = _answer(client, db_session, u, correct=True)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"]["correct"] is True
    assert body["answer"]["correct_option"] == _correct(db_session)
    assert body["streak"]["current_streak"] == 1
    assert body["streak"]["answered_today"] is True

    again = client.post("/trivia/daily/today/answer", json={"question_date": D0.isoformat(), "option": "b"})
    assert again.status_code == 409
    assert again.json()["detail"] == "already_answered"

    today = client.get("/trivia/daily/today").json()
    assert today["answer"]["selected_option"] == _correct(db_session)
    assert db_session.query(DailyTriviaAnswer).count() == 1


def test_wrong_answer_is_graded(client, db_session, bank, clock):
    u = _user(db_session)
    body = _answer(client, db_session, u, correct=False).json()
    assert body["answer"]["correct"] is False
    assert body["streak"]["current_streak"] == 1
    assert body["streak"]["perfect_run"] is False


def test_answer_for_another_date_is_refused(client, db_session, bank, clock):
    u = _user(db_session)
    _act_as(u)
    client.get("/trivia/daily/today")
    r = client.post("/trivia/daily/today/answer",
                    json={"question_date": (D0 - timedelta(days=1)).isoformat(), "option": "a"})
    assert r.status_code == 409
    assert r.json()["detail"] == "question_expired"


def test_option_not_on_question_is_refused(client, db_session, clock):
    db_session.add(TriviaQuestion(
        category=TriviaCategory.new_testament, difficulty=TriviaDifficulty.beginner,
        question_text="Jesus wept?", option_a="True", option_b="False", correct_option=TriviaCorrectOption.a,
        question_type=TriviaQuestionType.true_false,
    ))
    db_session.commit()
    u = _user(db_session)
    _act_as(u)
    assert client.get("/trivia/daily/today").json()["question"]["option_c"] is None
    r = client.post("/trivia/daily/today/answer", json={"question_date": D0.isoformat(), "option": "c"})
    assert r.status_code == 422
    r = client.post("/trivia/daily/today/answer", json={"question_date": D0.isoformat(), "option": "z"})
    assert r.status_code == 422
    assert db_session.query(DailyTriviaAnswer).count() == 0


def test_empty_bank_returns_503(client, db_session, clock):
    _act_as(_user(db_session))
    r = client.get("/trivia/daily/today")
    assert r.status_code == 503
    assert r.json()["detail"] == "daily_question_unavailable"


def test_requires_auth(client):
    app.dependency_overrides.pop(get_current_user, None)
    assert client.get("/trivia/daily/today").status_code in (401, 403)
    assert client.get("/trivia/daily/streak").status_code in (401, 403)
    assert client.post("/trivia/daily/today/answer",
                       json={"question_date": D0.isoformat(), "option": "a"}).status_code in (401, 403)


# ---------- US2: streaks ----------

def test_consecutive_days_count_up(client, db_session, bank, clock):
    u = _user(db_session)
    for day in range(3):
        d = D0 + timedelta(days=day)
        body = _answer(client, db_session, u, d=d).json()
        assert body["streak"]["current_streak"] == day + 1
        clock.advance(days=1)
    s = db_session.query(DailyTriviaStreak).filter_by(user_id=u.id).one()
    assert s.longest_streak == 3
    assert s.streak_started_on == D0


def test_freezes_earned_every_15_and_capped_at_2(db_session, bank):
    u = _user(db_session)
    earned_at = []
    for day in range(46):
        res = daily_svc._advance_streak(db_session, u.id, D0 + timedelta(days=day), True)
        if res["freeze_earned"]:
            earned_at.append(res["streak"].current_streak)
        db_session.commit()
    assert earned_at == [15, 30]
    assert db_session.query(DailyTriviaStreak).filter_by(user_id=u.id).one().freezes_available == 2


def test_freezes_bridge_missed_days(client, db_session, bank, clock):
    u = _user(db_session)
    _set_streak(db_session, u, current=20, last=D0 - timedelta(days=3), freezes=2)
    body = _answer(client, db_session, u).json()
    assert body["freezes_used"] == 2
    assert body["streak_reset"] is False
    assert body["streak"]["current_streak"] == 21
    assert body["streak"]["freezes_available"] == 0
    freeze_days = {c["date"] for c in body["streak"]["calendar"] if c["status"] == "freeze"}
    assert freeze_days == {(D0 - timedelta(days=2)).isoformat(), (D0 - timedelta(days=1)).isoformat()}


def test_gap_longer_than_freezes_resets(client, db_session, bank, clock):
    u = _user(db_session)
    _set_streak(db_session, u, current=20, last=D0 - timedelta(days=3), freezes=1, perfect=False, tiers=[])
    body = _answer(client, db_session, u).json()
    assert body["streak_reset"] is True
    assert body["streak"]["current_streak"] == 1
    assert body["streak"]["freezes_available"] == 0
    assert body["streak"]["perfect_run"] is True
    assert body["streak"]["streak_started_on"] == D0.isoformat()
    assert db_session.query(DailyTriviaStreak).filter_by(user_id=u.id).one().longest_streak == 20


def test_wrong_answer_keeps_streak_but_ends_perfect_run(db_session, bank):
    u = _user(db_session)
    daily_svc._advance_streak(db_session, u.id, D0, True)
    daily_svc._advance_streak(db_session, u.id, D0 + timedelta(days=1), False)
    res = daily_svc._advance_streak(db_session, u.id, D0 + timedelta(days=2), True)
    assert res["streak"].current_streak == 3
    assert res["streak"].perfect_run is False


def test_lapsed_streak_reads_as_zero_without_writing(client, db_session, bank, clock):
    u = _user(db_session)
    _set_streak(db_session, u, current=30, last=D0 - timedelta(days=3), freezes=1)
    _act_as(u)
    body = client.get("/trivia/daily/streak").json()
    assert body["current_streak"] == 0
    assert body["freezes_available"] == 0
    assert body["streak_started_on"] is None
    assert body["next_milestone"]["tier"] == 45
    db_session.expire_all()
    assert db_session.query(DailyTriviaStreak).filter_by(user_id=u.id).one().current_streak == 30


def test_streak_shows_projected_freeze_use(client, db_session, bank, clock):
    u = _user(db_session)
    _set_streak(db_session, u, current=30, last=D0 - timedelta(days=2), freezes=2)
    _act_as(u)
    body = client.get("/trivia/daily/streak").json()
    assert body["current_streak"] == 30
    assert body["freezes_available"] == 1
    assert {"date": (D0 - timedelta(days=1)).isoformat(), "status": "freeze"} in body["calendar"]


def test_new_user_streak_state(client, db_session, clock):
    _act_as(_user(db_session))
    body = client.get("/trivia/daily/streak").json()
    assert body["current_streak"] == 0
    assert body["calendar"] == []
    assert body["next_milestone"] == {"tier": 45, "days_remaining": 45, "percent": 15, "percent_if_perfect": 25}
    assert body["active_reward"] is None
    assert body["max_freezes"] == 2


def test_calendar_marks_correct_and_wrong(client, db_session, bank, clock):
    u = _user(db_session)
    _answer(client, db_session, u, correct=True)
    clock.advance(days=1)
    body = _answer(client, db_session, u, correct=False, d=D0 + timedelta(days=1)).json()
    assert body["streak"]["calendar"] == [
        {"date": D0.isoformat(), "status": "correct"},
        {"date": (D0 + timedelta(days=1)).isoformat(), "status": "wrong"},
    ]


# ---------- US3: rewards ----------

def test_day_45_issues_15_percent_code(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=44, perfect=False)
    body = _answer(client, db_session, u).json()
    assert body["new_reward"]["tier"] == 45
    assert body["new_reward"]["percent"] == 15
    assert body["new_reward"]["status"] == "pending"

    # Background task has run by the time TestClient returns
    db_session.expire_all()
    r = db_session.query(DailyTriviaReward).filter_by(user_id=u.id).one()
    assert r.status == DailyTriviaRewardStatus.active
    assert r.discount_code == "TROOTH-STREAK45-CODE1"
    assert daily_svc._aware(r.expires_at) == T0 + timedelta(days=60)
    assert shop["created"] == [(45, 15)]
    assert [e[:3] for e in emails] == [(u.id, 45, 15)]
    assert pushes["reward"] == [(u.id, 45, 15)]

    streak = client.get("/trivia/daily/streak").json()
    assert streak["active_reward"]["discount_code"] == "TROOTH-STREAK45-CODE1"
    assert streak["active_reward"]["shop_url"] == settings.shop_url
    assert streak["next_milestone"]["tier"] == 60


def test_perfect_run_adds_10_percent(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=44, perfect=True)
    body = _answer(client, db_session, u, correct=True).json()
    assert body["new_reward"]["percent"] == 25
    assert body["new_reward"]["perfect"] is True


def test_wrong_answer_on_milestone_day_loses_bonus(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=44, perfect=True)
    body = _answer(client, db_session, u, correct=False).json()
    assert body["new_reward"]["percent"] == 15


def test_day_60_supersedes_and_deactivates_45(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=44, perfect=False)
    _answer(client, db_session, u)
    s = db_session.query(DailyTriviaStreak).filter_by(user_id=u.id).one()
    s.current_streak = 59
    s.last_answered_date = D0 + timedelta(days=14)
    db_session.commit()
    clock.advance(days=15)
    body = _answer(client, db_session, u, d=D0 + timedelta(days=15)).json()
    assert body["new_reward"]["percent"] == 35

    db_session.expire_all()
    rewards = {r.tier: r for r in db_session.query(DailyTriviaReward).filter_by(user_id=u.id)}
    assert rewards[45].status == DailyTriviaRewardStatus.superseded
    assert rewards[45].deactivated_at is not None
    assert rewards[60].status == DailyTriviaRewardStatus.active
    assert rewards[60].replaces_reward_id == rewards[45].id
    assert shop["deactivated"] == ["gid://shopify/DiscountCodeNode/1"]
    assert emails[-1][4] == 15   # the email mentions the replaced 15% code

    assert client.get("/trivia/daily/streak").json()["active_reward"]["tier"] == 60
    # A re-run deactivates nothing twice
    daily_svc.run_hourly(db_session, clock.now)
    assert shop["deactivated"] == ["gid://shopify/DiscountCodeNode/1"]


def test_day_90_is_the_last_reward(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=89, perfect=True, tiers=[45, 60])
    body = _answer(client, db_session, u).json()
    assert body["new_reward"]["percent"] == 60
    assert body["streak"]["next_milestone"] is None
    clock.advance(days=1)
    body = _answer(client, db_session, u, d=D0 + timedelta(days=1)).json()
    assert body["new_reward"] is None
    assert body["streak"]["current_streak"] == 91


def test_process_reward_is_idempotent(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=44)
    _answer(client, db_session, u)
    reward_id = db_session.query(DailyTriviaReward.id).filter_by(user_id=u.id).scalar()
    daily_svc.process_reward(db_session, reward_id, clock.now)
    daily_svc.process_reward(db_session, reward_id, clock.now)
    daily_svc.run_hourly(db_session, clock.now)
    assert len(shop["created"]) == 1
    assert len(emails) == 1
    assert len(pushes["reward"]) == 1


def test_shopify_failure_keeps_answer_and_retries(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=44)
    shop["fail"] = True
    r = _answer(client, db_session, u)
    assert r.status_code == 200
    db_session.expire_all()
    reward = db_session.query(DailyTriviaReward).filter_by(user_id=u.id).one()
    assert reward.status == DailyTriviaRewardStatus.pending
    assert db_session.query(DailyTriviaStreak).filter_by(user_id=u.id).one().current_streak == 45
    assert emails == []

    shop["fail"] = False
    out = daily_svc.run_hourly(db_session, clock.now)
    assert out["rewards_processed"] == 1
    db_session.expire_all()
    assert db_session.get(DailyTriviaReward, reward.id).status == DailyTriviaRewardStatus.active
    assert len(emails) == 1


def test_rewards_expire_after_60_days(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=44)
    _answer(client, db_session, u)
    assert daily_svc.expire_rewards(db_session, T0 + timedelta(days=59)) == 0
    assert daily_svc.expire_rewards(db_session, T0 + timedelta(days=60)) == 1
    clock.advance(days=61)
    _act_as(u)
    assert client.get("/trivia/daily/streak").json()["active_reward"] is None


def test_new_streak_can_earn_45_again(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    old = D0 - timedelta(days=200)
    db_session.add(DailyTriviaReward(user_id=u.id, streak_started_on=old, tier=45, percent=15,
                                     status=DailyTriviaRewardStatus.expired, discount_code="OLD"))
    db_session.commit()
    _set_streak(db_session, u, current=44, perfect=False)
    body = _answer(client, db_session, u).json()
    assert body["new_reward"]["tier"] == 45


def test_lower_tier_never_replaces_a_better_held_code(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    old_start = D0 - timedelta(days=120)
    db_session.add(DailyTriviaReward(user_id=u.id, streak_started_on=old_start, tier=60, percent=35,
                                     status=DailyTriviaRewardStatus.active, discount_code="KEEP",
                                     shopify_discount_id="gid://x/1", expires_at=T0 + timedelta(days=30)))
    db_session.commit()
    _set_streak(db_session, u, current=44, perfect=True)   # new streak would earn 25%
    body = _answer(client, db_session, u).json()
    assert body["new_reward"] is None
    assert body["streak"]["active_reward"]["discount_code"] == "KEEP"
    assert shop["created"] == []
    assert 45 in db_session.query(DailyTriviaStreak).filter_by(user_id=u.id).one().tiers_earned


def test_reward_email_renders(db_session):
    u = _user(db_session)
    r = DailyTriviaReward(user_id=u.id, streak_started_on=D0, tier=60, percent=45, perfect=True,
                          status=DailyTriviaRewardStatus.active, discount_code="TROOTH-STREAK60-ABC123",
                          expires_at=T0 + timedelta(days=60))
    db_session.add(r)
    db_session.commit()
    env = daily_svc.email_svc.get_email_template_env()
    html = env.get_template("campaigns/daily_trivia_reward.html").render(
        name=u.name, tier=60, percent=45, perfect=True, replaced_percent=25,
        discount_code=r.discount_code, expires="January 4, 2027", shop_url=settings.shop_url, logo_url="",
    )
    assert "TROOTH-STREAK60-ABC123" in html
    assert "45% off" in html
    assert "earlier 25% code" in html


# ---------- US4: reminders ----------

def test_cron_requires_secret(client):
    assert client.post("/scheduled/daily-trivia").status_code == 403
    assert client.post("/scheduled/daily-trivia", headers={"X-Cron-Secret": "nope"}).status_code == 403


def test_reminder_only_at_local_9am(client, db_session, bank, pushes):
    # 14:00 UTC = 09:00 New York (EST) = 08:00 Chicago (CST)
    ny = _user(db_session, "Nyc", tz="America/New_York", device=True)
    chi = _user(db_session, "Chi", tz="America/Chicago", device=True)
    default = _user(db_session, "Def", tz=None, device=True)
    now = datetime(2026, 11, 5, 14, 0, tzinfo=UTC)
    out = daily_svc.run_hourly(db_session, now)
    reminded = {p[0] for p in pushes["reminder"]}
    assert reminded == {ny.id, default.id}
    assert out["reminded"] == 2
    assert chi.id not in reminded

    # An hour later it's 9am in Chicago
    daily_svc.run_hourly(db_session, now + timedelta(hours=1))
    assert chi.id in {p[0] for p in pushes["reminder"]}


def test_no_reminder_if_answered_disabled_or_no_device(client, db_session, bank, pushes, clock):
    answered = _user(db_session, "Done", tz="America/New_York", device=True)
    disabled = _user(db_session, "Off", tz="America/New_York", push=False, device=True)
    no_device = _user(db_session, "Nodev", tz="America/New_York")
    clock.now = datetime(2026, 11, 5, 13, 30, tzinfo=UTC)   # 8:30 NY: answer before the reminder
    _answer(client, db_session, answered)
    out = daily_svc.run_hourly(db_session, datetime(2026, 11, 5, 14, 5, tzinfo=UTC))
    assert out["reminded"] == 0
    assert pushes["reminder"] == []
    assert {disabled.id, no_device.id}.isdisjoint({p[0] for p in pushes["reminder"]})


def test_reminder_sent_once_per_date(client, db_session, bank, pushes):
    _user(db_session, "Nyc", tz="America/New_York", device=True)
    now = datetime(2026, 11, 5, 14, 0, tzinfo=UTC)
    daily_svc.run_hourly(db_session, now)
    r = client.post("/scheduled/daily-trivia", headers=CRON)
    assert r.status_code == 200
    daily_svc.run_hourly(db_session, now + timedelta(minutes=20))
    assert len(pushes["reminder"]) == 1


def test_reminder_mentions_streak(client, db_session, bank, pushes):
    u = _user(db_session, "Nyc", tz="America/New_York", device=True)
    _set_streak(db_session, u, current=12, last=D0 - timedelta(days=1))
    daily_svc.run_hourly(db_session, datetime(2026, 11, 5, 14, 0, tzinfo=UTC))
    assert pushes["reminder"] == [(u.id, 12, D0.isoformat())]


# ---------- US5: timezone ----------

def test_set_timezone_moves_the_date(client, db_session, bank, clock):
    u = _user(db_session)
    _act_as(u)
    r = client.put("/users/me/timezone", json={"timezone": "Pacific/Kiritimati"})   # UTC+14
    assert r.status_code == 200
    assert r.json() == {"timezone": "Pacific/Kiritimati"}
    db_session.refresh(u)
    assert u.timezone == "Pacific/Kiritimati"
    assert client.get("/trivia/daily/today").json()["question"]["date"] == (D0 + timedelta(days=1)).isoformat()


def test_invalid_timezone_is_refused(client, db_session):
    u = _user(db_session, tz="America/Chicago")
    _act_as(u)
    for bad in ("Mars/Olympus", "../etc/passwd", "", "America"):
        r = client.put("/users/me/timezone", json={"timezone": bad})
        assert r.status_code == 422
    db_session.refresh(u)
    assert u.timezone == "America/Chicago"


def test_timezone_requires_auth(client):
    app.dependency_overrides.pop(get_current_user, None)
    assert client.put("/users/me/timezone", json={"timezone": "America/Chicago"}).status_code in (401, 403)


def test_moving_timezone_back_cannot_answer_an_earlier_date(client, db_session, bank, clock):
    u = _user(db_session, tz="Pacific/Kiritimati")
    _answer(client, db_session, u, d=D0 + timedelta(days=1))
    u.timezone = "America/New_York"
    db_session.commit()
    _act_as(u)
    client.get("/trivia/daily/today")
    r = client.post("/trivia/daily/today/answer", json={"question_date": D0.isoformat(), "option": "a"})
    assert r.status_code == 409
    assert r.json()["detail"] == "already_answered"


# ---------- Account deletion ----------

def test_account_deletion_removes_daily_trivia_data(client, db_session, bank, clock, shop, emails, pushes):
    u = _user(db_session)
    _set_streak(db_session, u, current=44)
    _answer(client, db_session, u)
    counts = {}
    _clear_shared_user_references(db_session, u.id, counts)
    db_session.commit()
    assert counts["daily_trivia_answers"] == 1
    assert counts["daily_trivia_streaks"] == 1
    assert counts["daily_trivia_rewards"] == 1
    assert db_session.query(DailyTriviaQuestion).count() == 1
