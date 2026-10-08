"""Daily trivia: one shared question per date, per-user streaks, streak reward codes (spec 002).

- The question for a date is chosen lazily on first request and fixed on its row.
- "Today" is the user's local date (User.timezone, default America/New_York).
- Streak freezes are applied lazily on the next answer; reads compute the effective
  streak without writing (research R4).
- Rewards are created pending inside the answer transaction and turned into Shopify
  codes afterwards by process_reward(), which is idempotent per step and retried by
  the hourly cron (research R5), mirroring trivia_competition._ensure_code/_ensure_notified.
"""
import logging
import random
from datetime import date, datetime, timedelta, UTC
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.daily_trivia import (
    DailyTriviaQuestion, DailyTriviaAnswer, DailyTriviaStreak, DailyTriviaReward, DailyTriviaRewardStatus,
)
from app.models.device_token import DeviceToken
from app.models.trivia import TriviaQuestion, TriviaCategory, TriviaDifficulty
from app.models.user import User
from app.services import shopify_admin
from app.services import email as email_svc
from app.services.push_notification import notify_daily_trivia_reminder, notify_daily_trivia_reward
from app.services.trivia import _shuffle_options

logger = logging.getLogger(__name__)

MILESTONES = {45: 15, 60: 35, 90: 50}   # streak days -> base percent off
PERFECT_BONUS = 10
FREEZE_EVERY = 15
MAX_FREEZES = 2
NO_REPEAT_DAYS = 180
CODE_VALID_DAYS = 60
CALENDAR_DAYS = 62
REMINDER_HOUR = 9
DEFAULT_TZ = "America/New_York"

DAILY_CATEGORIES = [
    TriviaCategory.old_testament, TriviaCategory.new_testament,
    TriviaCategory.theology_doctrine, TriviaCategory.discipleship_living,
]
DAILY_DIFFICULTIES = [TriviaDifficulty.beginner, TriviaDifficulty.challenger]
CATEGORY_LABELS = {
    "old_testament": "Old Testament",
    "new_testament": "New Testament",
    "theology_doctrine": "Theology & Doctrine",
    "discipleship_living": "Discipleship & Living",
}
DIFFICULTY_LABELS = {"beginner": "Beginner", "challenger": "Challenger"}

_OPEN = (DailyTriviaRewardStatus.pending, DailyTriviaRewardStatus.active)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    # SQLite hands back naive datetimes; everything stored is UTC
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# ---------- Time ----------

def is_valid_timezone(name: str) -> bool:
    if not name or len(name) > 100:
        return False
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return False


def _zone(tz_name: Optional[str]) -> ZoneInfo:
    if tz_name and is_valid_timezone(tz_name):
        return ZoneInfo(tz_name)
    return ZoneInfo(DEFAULT_TZ)


def local_now(user, now: Optional[datetime] = None) -> datetime:
    return (now or _now()).astimezone(_zone(getattr(user, "timezone", None)))


def local_today(user, now: Optional[datetime] = None) -> date:
    return local_now(user, now).date()


# ---------- Question of the day ----------

def _pick_question(db: Session, for_date: date) -> Optional[TriviaQuestion]:
    cutoff = for_date - timedelta(days=NO_REPEAT_DAYS)
    recent = select(DailyTriviaQuestion.question_id).where(DailyTriviaQuestion.date > cutoff)

    # Pick the category + level first so each has an equal chance whatever its pool size
    pairs = [(c, d) for c in DAILY_CATEGORIES for d in DAILY_DIFFICULTIES]
    random.shuffle(pairs)
    for category, difficulty in pairs:
        ids = [row.id for row in db.query(TriviaQuestion.id).filter(
            TriviaQuestion.is_approved == True,  # noqa: E712
            TriviaQuestion.category == category,
            TriviaQuestion.difficulty == difficulty,
            TriviaQuestion.id.notin_(recent),
        ).all()]
        if ids:
            return db.get(TriviaQuestion, random.choice(ids))

    # Every eligible question was used inside the window: reuse the one used longest ago
    eligible = db.query(TriviaQuestion).filter(
        TriviaQuestion.is_approved == True,  # noqa: E712
        TriviaQuestion.category.in_(DAILY_CATEGORIES),
        TriviaQuestion.difficulty.in_(DAILY_DIFFICULTIES),
    ).all()
    if not eligible:
        return None
    last_used = dict(
        db.query(DailyTriviaQuestion.question_id, DailyTriviaQuestion.date)
        .order_by(DailyTriviaQuestion.date.asc())
        .all()
    )
    return min(eligible, key=lambda q: (last_used.get(q.id, date.min), q.id))


def get_or_create_question(db: Session, for_date: date) -> Optional[DailyTriviaQuestion]:
    row = db.query(DailyTriviaQuestion).filter(DailyTriviaQuestion.date == for_date).first()
    if row:
        return row
    q = _pick_question(db, for_date)
    if q is None:
        logger.error("[daily-trivia] No approved beginner/challenger questions available")
        return None

    shuffled = _shuffle_options(q)
    row = DailyTriviaQuestion(
        date=for_date,
        question_id=q.id,
        category=q.category,
        difficulty=q.difficulty,
        question_type=q.question_type,
        question_text=q.question_text,
        options={
            "a": shuffled.option_a, "b": shuffled.option_b,
            "c": shuffled.option_c, "d": shuffled.option_d,
        },
        correct_option=shuffled.correct_option.value,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Another request chose this date's question first — use theirs
        db.rollback()
        row = db.query(DailyTriviaQuestion).filter(DailyTriviaQuestion.date == for_date).one()
    logger.info(f"[daily-trivia] Question for {for_date}: #{row.question_id} "
                f"({row.category.value}/{row.difficulty.value})")
    return row


def _require_question(db: Session, for_date: date) -> DailyTriviaQuestion:
    q = get_or_create_question(db, for_date)
    if q is None:
        raise HTTPException(status_code=503, detail="daily_question_unavailable")
    return q


# ---------- Serialisation ----------

def question_out(q: DailyTriviaQuestion) -> dict:
    return {
        "date": q.date,
        "category": q.category.value,
        "category_label": CATEGORY_LABELS.get(q.category.value, q.category.value),
        "difficulty": q.difficulty.value,
        "difficulty_label": DIFFICULTY_LABELS.get(q.difficulty.value, q.difficulty.value),
        "question_type": q.question_type.value,
        "question_text": q.question_text,
        "option_a": q.options.get("a"),
        "option_b": q.options.get("b"),
        "option_c": q.options.get("c"),
        "option_d": q.options.get("d"),
    }


def answer_out(a: DailyTriviaAnswer, q: DailyTriviaQuestion) -> dict:
    return {
        "selected_option": a.selected_option,
        "correct": a.is_correct,
        "correct_option": q.correct_option,
        "answered_at": _aware(a.answered_at),
    }


def reward_out(r: Optional[DailyTriviaReward]) -> Optional[dict]:
    if r is None:
        return None
    return {
        "id": r.id,
        "tier": r.tier,
        "percent": r.percent,
        "perfect": r.perfect,
        "status": r.status.value,
        "discount_code": r.discount_code,
        "expires_at": _aware(r.expires_at),
        "shop_url": settings.shop_url,
    }


# ---------- Streaks ----------

def _get_streak(db: Session, user_id: str, lock: bool = False) -> Optional[DailyTriviaStreak]:
    query = db.query(DailyTriviaStreak).filter(DailyTriviaStreak.user_id == user_id)
    if lock:
        query = query.with_for_update()
    return query.first()


def _effective(s: Optional[DailyTriviaStreak], today: date) -> tuple[int, int, list[date]]:
    """(current streak, freezes left, dates freezes would cover) as of `today`, without writing."""
    if s is None or s.last_answered_date is None or s.current_streak == 0:
        return 0, 0, []
    missed = (today - s.last_answered_date).days - 1
    if missed <= 0:
        return s.current_streak, s.freezes_available, []
    if missed <= s.freezes_available:
        covered = [s.last_answered_date + timedelta(days=i) for i in range(1, missed + 1)]
        return s.current_streak, s.freezes_available - missed, covered
    return 0, 0, []


def _advance_streak(db: Session, user_id: str, d: date, correct: bool) -> dict:
    s = _get_streak(db, user_id, lock=True)
    if s is None:
        s = DailyTriviaStreak(user_id=user_id, current_streak=0, longest_streak=0, freezes_available=0,
                              perfect_run=True, freeze_dates=[], tiers_earned=[])
        db.add(s)
        db.flush()

    freezes_used = 0
    reset = False
    missed = None if s.last_answered_date is None else (d - s.last_answered_date).days - 1
    if missed is None or s.current_streak == 0 or missed > s.freezes_available:
        reset = bool(missed is not None and s.current_streak > 0)
        s.current_streak = 0
        s.freezes_available = 0
        s.perfect_run = True
        s.freeze_dates = []
        s.tiers_earned = []
        s.streak_started_on = d
    elif missed > 0:
        freezes_used = missed
        s.freezes_available -= missed
        s.freeze_dates = list(s.freeze_dates or []) + [
            (s.last_answered_date + timedelta(days=i)).isoformat() for i in range(1, missed + 1)
        ]

    s.current_streak += 1
    s.perfect_run = bool(s.perfect_run and correct)
    freeze_earned = False
    if s.current_streak % FREEZE_EVERY == 0 and s.freezes_available < MAX_FREEZES:
        s.freezes_available += 1
        freeze_earned = True
    s.longest_streak = max(s.longest_streak or 0, s.current_streak)
    s.last_answered_date = d

    reached = None
    if s.current_streak in MILESTONES and s.current_streak not in (s.tiers_earned or []):
        s.tiers_earned = list(s.tiers_earned or []) + [s.current_streak]
        reached = s.current_streak

    return {"streak": s, "freezes_used": freezes_used, "reset": reset,
            "freeze_earned": freeze_earned, "reached_tier": reached}


def _open_reward(db: Session, user_id: str) -> Optional[DailyTriviaReward]:
    """The user's best pending or active reward (normally the only one)."""
    return (
        db.query(DailyTriviaReward)
        .filter(DailyTriviaReward.user_id == user_id, DailyTriviaReward.status.in_(_OPEN))
        .order_by(DailyTriviaReward.percent.desc(), DailyTriviaReward.id.desc())
        .first()
    )


def _create_reward(db: Session, s: DailyTriviaStreak, tier: int) -> Optional[DailyTriviaReward]:
    percent = MILESTONES[tier] + (PERFECT_BONUS if s.perfect_run else 0)
    held = _open_reward(db, s.user_id)
    if held is not None and held.percent >= percent:
        # e.g. a new streak reaches 45 while a 60-day code from an earlier streak is still unused
        logger.info(f"[daily-trivia] User {s.user_id} reached {tier} but keeps a better reward #{held.id}")
        return None
    reward = DailyTriviaReward(
        user_id=s.user_id, streak_started_on=s.streak_started_on, tier=tier,
        percent=percent, perfect=s.perfect_run, status=DailyTriviaRewardStatus.pending,
    )
    db.add(reward)
    return reward


def get_streak_state(db: Session, user, now: Optional[datetime] = None) -> dict:
    today = local_today(user, now)
    s = _get_streak(db, user.id)
    current, freezes, projected = _effective(s, today)
    alive = current > 0

    start = today - timedelta(days=CALENDAR_DAYS - 1)
    days: dict[date, str] = {}
    if s is not None:
        for iso in (s.freeze_dates or []):
            d = date.fromisoformat(iso)
            if d >= start:
                days[d] = "freeze"
        for d in projected:
            days[d] = "freeze"
    for a in db.query(DailyTriviaAnswer).filter(
        DailyTriviaAnswer.user_id == user.id, DailyTriviaAnswer.date >= start, DailyTriviaAnswer.date <= today,
    ).all():
        days[a.date] = "correct" if a.is_correct else "wrong"

    tiers = (s.tiers_earned or []) if (s is not None and alive) else []
    next_milestone = None
    for tier in sorted(MILESTONES):
        if tier > current and tier not in tiers:
            next_milestone = {
                "tier": tier,
                "days_remaining": tier - current,
                "percent": MILESTONES[tier],
                "percent_if_perfect": MILESTONES[tier] + PERFECT_BONUS,
            }
            break

    return {
        "current_streak": current,
        "longest_streak": (s.longest_streak if s else 0) or 0,
        "freezes_available": freezes,
        "max_freezes": MAX_FREEZES,
        "perfect_run": bool(s.perfect_run) if (s is not None and alive) else True,
        "answered_today": bool(s is not None and s.last_answered_date == today),
        "streak_started_on": s.streak_started_on if (s is not None and alive) else None,
        "calendar": [{"date": d, "status": days[d]} for d in sorted(days)],
        "next_milestone": next_milestone,
        "active_reward": reward_out(_open_reward(db, user.id)),
    }


# ---------- Endpoints ----------

def get_today(db: Session, user, now: Optional[datetime] = None) -> dict:
    today = local_today(user, now)
    q = _require_question(db, today)
    a = db.query(DailyTriviaAnswer).filter(
        DailyTriviaAnswer.user_id == user.id, DailyTriviaAnswer.date == today,
    ).first()
    return {
        "question": question_out(q),
        "answer": answer_out(a, q) if a else None,
        "streak": get_streak_state(db, user, now),
    }


def submit_answer(db: Session, user, question_date: date, option: str,
                  now: Optional[datetime] = None) -> tuple[dict, Optional[int]]:
    """Grade today's answer and advance the streak. Returns (response, reward id to process)."""
    today = local_today(user, now)
    if question_date != today:
        raise HTTPException(status_code=409, detail="question_expired")
    q = _require_question(db, today)

    already = db.query(DailyTriviaAnswer.id).filter(
        DailyTriviaAnswer.user_id == user.id, DailyTriviaAnswer.date >= today,
    ).first()
    if already:
        raise HTTPException(status_code=409, detail="already_answered")
    if q.options.get(option) is None:
        raise HTTPException(status_code=422, detail="invalid_option")

    correct = option == q.correct_option
    answer = DailyTriviaAnswer(
        user_id=user.id, date=today, daily_question_id=q.id,
        selected_option=option, is_correct=correct, answered_at=now or _now(),
    )
    db.add(answer)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="already_answered")

    result = _advance_streak(db, user.id, today, correct)
    reward = _create_reward(db, result["streak"], result["reached_tier"]) if result["reached_tier"] else None
    db.commit()
    if reward is not None:
        db.refresh(reward)
        logger.info(f"[daily-trivia] User {user.id} reached {reward.tier} days — reward #{reward.id} "
                    f"({reward.percent}%) pending")

    response = {
        "question": question_out(q),
        "answer": answer_out(answer, q),
        "streak": get_streak_state(db, user, now),
        "freezes_used": result["freezes_used"],
        "streak_reset": result["reset"],
        "freeze_earned": result["freeze_earned"],
        "new_reward": reward_out(reward),
    }
    return response, (reward.id if reward is not None else None)


# ---------- Rewards ----------

def _lock_reward(db: Session, reward_id: int) -> DailyTriviaReward:
    # Row lock so the background task and the cron can't double-create or double-send
    return db.query(DailyTriviaReward).filter(DailyTriviaReward.id == reward_id).with_for_update().one()


def _ensure_code(db: Session, reward_id: int, now: datetime) -> None:
    r = _lock_reward(db, reward_id)
    if r.status != DailyTriviaRewardStatus.pending:
        db.commit()
        return

    better = (
        db.query(DailyTriviaReward)
        .filter(DailyTriviaReward.user_id == r.user_id, DailyTriviaReward.id != r.id,
                DailyTriviaReward.status.in_(_OPEN), DailyTriviaReward.percent > r.percent)
        .first()
    )
    if better is not None:
        # A higher reward overtook this one before its code was made — never issue it
        r.status = DailyTriviaRewardStatus.superseded
        r.superseded_at = now
        r.deactivated_at = now
        r.emailed_at = r.emailed_at or now
        r.pushed_at = r.pushed_at or now
        db.commit()
        return

    expires = now + timedelta(days=CODE_VALID_DAYS)
    code = shopify_admin.create_percentage_code(
        tier=r.tier,
        percent=r.percent,
        title=f"Daily trivia {r.tier}-day streak – {r.percent}% (reward {r.id})",
        starts_at=now,
        ends_at=expires,
    )
    r.discount_code = code.code
    r.shopify_discount_id = code.discount_id
    r.issued_at = now
    r.expires_at = expires
    r.status = DailyTriviaRewardStatus.active

    replaced = (
        db.query(DailyTriviaReward)
        .filter(DailyTriviaReward.user_id == r.user_id, DailyTriviaReward.id != r.id,
                DailyTriviaReward.status == DailyTriviaRewardStatus.active)
        .order_by(DailyTriviaReward.percent.desc())
        .all()
    )
    for old in replaced:
        old.status = DailyTriviaRewardStatus.superseded
        old.superseded_at = now
        if not old.shopify_discount_id or old.shopify_discount_id == "dry-run":
            old.deactivated_at = now
    if replaced:
        r.replaces_reward_id = replaced[0].id
    db.commit()


def _ensure_deactivated(db: Session, user_id: str, now: datetime) -> None:
    pending = (
        db.query(DailyTriviaReward.id)
        .filter(DailyTriviaReward.user_id == user_id,
                DailyTriviaReward.status == DailyTriviaRewardStatus.superseded,
                DailyTriviaReward.deactivated_at.is_(None))
        .all()
    )
    for (old_id,) in pending:
        old = _lock_reward(db, old_id)
        if old.deactivated_at is None:
            shopify_admin.deactivate_code(old.shopify_discount_id)
            old.deactivated_at = now
        db.commit()


def _ensure_notified(db: Session, reward_id: int, now: datetime) -> None:
    r = _lock_reward(db, reward_id)
    if r.status != DailyTriviaRewardStatus.active:
        db.commit()
        return
    user = db.query(User).filter(User.id == r.user_id).first()
    if user is None:
        r.emailed_at = r.emailed_at or now
        r.pushed_at = r.pushed_at or now
        db.commit()
        return

    if not r.emailed_at:
        replaced = db.get(DailyTriviaReward, r.replaces_reward_id) if r.replaces_reward_id else None
        if not email_svc.send_daily_trivia_reward_email(
            db, user, r, replaced_percent=replaced.percent if replaced else None,
        ):
            db.commit()
            raise RuntimeError(f"Reward email failed for reward {r.id}")
        r.emailed_at = now
        db.commit()
        r = _lock_reward(db, reward_id)

    if not r.pushed_at:
        try:
            notify_daily_trivia_reward(db, r.user_id, r.tier, r.percent)
        except Exception as e:  # push is best-effort; email is the delivery of record
            logger.warning(f"[daily-trivia] Push failed for reward {r.id}: {e}")
        r.pushed_at = now
    db.commit()


def process_reward(db: Session, reward_id: int, now: Optional[datetime] = None) -> None:
    """Create the code, retire the code it replaces, then email and push. Safe to re-run."""
    now = now or _now()
    _ensure_code(db, reward_id, now)
    user_id = db.get(DailyTriviaReward, reward_id).user_id
    _ensure_deactivated(db, user_id, now)
    _ensure_notified(db, reward_id, now)


def process_reward_in_new_session(bind, reward_id: int) -> None:
    """Background-task entry point: the request's session is closed by the time this runs."""
    db = Session(bind=bind)
    try:
        process_reward(db, reward_id)
    except Exception as e:
        db.rollback()
        logger.error(f"[daily-trivia] Reward {reward_id} incomplete, cron will retry: {e}", exc_info=True)
    finally:
        db.close()


def _unfinished_reward_ids(db: Session) -> list[int]:
    rows = db.query(DailyTriviaReward.id).filter(
        (DailyTriviaReward.status == DailyTriviaRewardStatus.pending)
        | ((DailyTriviaReward.status == DailyTriviaRewardStatus.active) & DailyTriviaReward.emailed_at.is_(None))
        | ((DailyTriviaReward.status == DailyTriviaRewardStatus.superseded)
           & DailyTriviaReward.deactivated_at.is_(None))
    ).order_by(DailyTriviaReward.id.asc()).all()
    return [row.id for row in rows]


def expire_rewards(db: Session, now: Optional[datetime] = None) -> int:
    now = now or _now()
    count = 0
    for r in db.query(DailyTriviaReward).filter(DailyTriviaReward.status == DailyTriviaRewardStatus.active).all():
        if r.expires_at is not None and _aware(r.expires_at) <= now:
            r.status = DailyTriviaRewardStatus.expired
            count += 1
    db.commit()
    return count


# ---------- Reminders ----------

def _send_reminders(db: Session, now: datetime) -> int:
    zones = [row[0] for row in db.query(User.timezone).distinct().all()]
    due = [tz for tz in zones if now.astimezone(_zone(tz)).hour == REMINDER_HOUR]
    if not due:
        return 0
    named = [tz for tz in due if tz is not None]
    tz_filter = User.timezone.in_(named) if named else None
    if None in due:
        tz_filter = User.timezone.is_(None) if tz_filter is None else (tz_filter | User.timezone.is_(None))

    has_device = exists().where(DeviceToken.user_id == User.id, DeviceToken.is_active == "true")
    users = db.query(User).filter(User.push_enabled == True, tz_filter, has_device).all()  # noqa: E712

    reminded = 0
    for user in users:
        today = local_today(user, now)
        q = get_or_create_question(db, today)
        if q is None:
            return reminded
        s = _get_streak(db, user.id, lock=True)
        if s is not None and today in (s.last_answered_date, s.last_reminded_date):
            db.commit()
            continue
        if s is None:
            s = DailyTriviaStreak(user_id=user.id, current_streak=0, longest_streak=0, freezes_available=0,
                                  perfect_run=True, freeze_dates=[], tiers_earned=[])
            db.add(s)
        s.last_reminded_date = today
        current, _, _ = _effective(s, today)
        db.commit()   # record first so a re-run in the same hour can't send twice
        try:
            notify_daily_trivia_reminder(
                db, user.id, current,
                CATEGORY_LABELS.get(q.category.value, q.category.value),
                DIFFICULTY_LABELS.get(q.difficulty.value, q.difficulty.value),
                today.isoformat(),
            )
            reminded += 1
        except Exception as e:
            logger.warning(f"[daily-trivia] Reminder push failed for user {user.id}: {e}")
    return reminded


def run_hourly(db: Session, now: Optional[datetime] = None) -> dict:
    now = now or _now()
    errors = []
    try:
        reminded = _send_reminders(db, now)
    except Exception as e:
        db.rollback()
        logger.error(f"[daily-trivia] Reminders failed: {e}", exc_info=True)
        reminded = 0
        errors.append({"step": "reminders", "error": str(e)})

    processed = 0
    for reward_id in _unfinished_reward_ids(db):
        try:
            process_reward(db, reward_id, now)
            processed += 1
        except Exception as e:
            db.rollback()
            logger.error(f"[daily-trivia] Reward {reward_id} incomplete: {e}", exc_info=True)
            errors.append({"reward_id": reward_id, "error": str(e)})

    expired = expire_rewards(db, now)
    logger.info(f"[daily-trivia] Hourly: reminded={reminded} processed={processed} "
                f"expired={expired} errors={len(errors)}")
    return {"reminded": reminded, "rewards_processed": processed, "rewards_expired": expired, "errors": errors}
