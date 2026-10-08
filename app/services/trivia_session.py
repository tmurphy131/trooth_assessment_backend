"""Server-run single-player trivia games.

The server picks the questions, sends one at a time without its answer,
grades each answer against the question it actually served, times answers
with its own clock, and runs sudden death and grace tokens. Only scores
written here are marked verified, so only they count toward competitions.

See specs/001-trivia-integrity/ (contract: contracts/trivia-api.md).
"""
import logging
import random
from datetime import datetime, UTC, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.trivia import (
    TriviaQuestion, TriviaSingleSession, TriviaSessionStatus,
    TriviaCategory, TriviaDifficulty,
)
from app.models.user import User
from app.schemas.trivia import (
    SingleSessionState, SessionQuestion, LastAnswer, SingleGameResult,
)
from app.services import trivia as trivia_svc

logger = logging.getLogger(__name__)

TIME_LIMIT_MS = 30_000
GRACE_WINDOW_MS = 10_000
ALLOWANCE_MS = 3_000          # network latency allowance on both limits
IDLE_LIMIT = timedelta(hours=1)
CORRECT_PER_GRACE_TOKEN = 10


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite hands back naive datetimes; treat them as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# ---------- Public API ----------

def start(db: Session, user: User, category: TriviaCategory, difficulty: TriviaDifficulty) -> SingleSessionState:
    now = _now()
    _finish_unfinished(db, user.id)

    query = db.query(TriviaQuestion.id).filter(
        TriviaQuestion.is_approved == True,
        TriviaQuestion.difficulty == difficulty,
    )
    if category != TriviaCategory.random:
        query = query.filter(TriviaQuestion.category == category)
    question_ids = [row[0] for row in query.all()]
    if not question_ids:
        db.commit()
        raise HTTPException(status_code=400, detail="No questions available")
    random.shuffle(question_ids)

    session = TriviaSingleSession(
        user_id=user.id,
        category=category,
        difficulty=difficulty,
        question_ids=question_ids,
        answers=[],
        created_at=now,
        last_activity_at=now,
    )
    db.add(session)
    db.flush()
    if not _serve(db, session):
        _finish(db, session)
    db.commit()
    logger.info("Trivia session %s started by user %s (%d questions)", session.id, user.id, len(question_ids))
    return to_state(session)


def answer(db: Session, user: User, session_id: str, question_id: int, selected: Optional[str]) -> SingleSessionState:
    session = _get_owned(db, user, session_id)
    answers = list(session.answers or [])

    # Network retry of the answer we just graded: replay, never grade twice
    if answers and answers[-1]["question_id"] == question_id:
        db.commit()
        return to_state(session, last_answer=_last_answer(answers[-1]))

    now = _now()
    _resolve_expired_grace(db, session, now)
    if session.status == TriviaSessionStatus.finished:
        db.commit()
        raise HTTPException(status_code=409, detail="Game is over")
    if session.status == TriviaSessionStatus.awaiting_grace:
        db.commit()
        raise HTTPException(status_code=409, detail="Grace decision pending")

    current = session.current_question
    if not current or question_id != current["id"]:
        db.commit()
        raise HTTPException(status_code=400, detail="Answer is not for the current question")

    served_at = _aware(session.current_served_at)
    question_expires = served_at + timedelta(milliseconds=TIME_LIMIT_MS)
    elapsed_ms = int((now - served_at).total_seconds() * 1000)
    timed_out = elapsed_ms > TIME_LIMIT_MS + ALLOWANCE_MS
    correct = not timed_out and selected is not None and selected == current["correct"]

    entry = {
        "index": session.current_index,
        "question_id": question_id,
        "selected": selected,
        "correct": correct,
        "correct_option": current["correct"],
        "timed_out": timed_out,
        "graced": False,
        "elapsed_ms": elapsed_ms,
    }
    session.answers = answers + [entry]
    session.last_activity_at = now

    if correct:
        session.streak += 1
        session.correct_count += 1
        if session.correct_count % CORRECT_PER_GRACE_TOKEN == 0:
            session.grace_tokens += 1
        _rescore(session)
        _advance(db, session)
    else:
        # The clock keeps running while the player is away: for a late answer the
        # grace window starts when the question expired, not when they came back.
        grace_deadline = min(now, question_expires) + timedelta(milliseconds=GRACE_WINDOW_MS + ALLOWANCE_MS)
        if session.grace_tokens > 0 and now <= grace_deadline:
            session.status = TriviaSessionStatus.awaiting_grace
            session.grace_deadline = grace_deadline
            _rescore(session)
        else:
            _finish(db, session)

    db.commit()
    return to_state(session, last_answer=_last_answer(entry))


def use_grace(db: Session, user: User, session_id: str, use: bool) -> SingleSessionState:
    session = _get_owned(db, user, session_id)
    if session.status != TriviaSessionStatus.awaiting_grace:
        db.commit()
        raise HTTPException(status_code=409, detail="No grace decision pending")

    now = _now()
    session.last_activity_at = now
    if not use or now > _aware(session.grace_deadline):
        _finish(db, session)
    else:
        answers = [dict(a) for a in session.answers]
        answers[-1]["graced"] = True
        session.answers = answers
        session.grace_tokens -= 1
        session.grace_tokens_used += 1
        session.grace_deadline = None
        session.status = TriviaSessionStatus.active
        _rescore(session)
        _advance(db, session)

    db.commit()
    return to_state(session)


def finish(db: Session, user: User, session_id: str) -> SingleGameResult:
    session = _get_owned(db, user, session_id)
    if session.status != TriviaSessionStatus.finished:
        session.last_activity_at = _now()
        _finish(db, session)
    db.commit()
    return SingleGameResult(**session.result)


def finish_stale(db: Session, now: Optional[datetime] = None) -> int:
    """Finish games whose question or grace window expired, or idle past IDLE_LIMIT. Returns how many."""
    now = now or _now()
    open_sessions = (
        db.query(TriviaSingleSession)
        .filter(TriviaSingleSession.status != TriviaSessionStatus.finished)
        .with_for_update()
        .all()
    )
    finished = 0
    for session in open_sessions:
        if _is_stale(session, now):
            _finish(db, session)
            finished += 1
    db.commit()
    if finished:
        logger.info("Trivia sessions: finished %d stale games", finished)
    return finished


def games_in_progress_before(db: Session, cutoff: datetime, now: Optional[datetime] = None) -> int:
    """Finish stale games, then count games started before cutoff that are still being played."""
    finish_stale(db, now)
    open_sessions = (
        db.query(TriviaSingleSession)
        .filter(TriviaSingleSession.status != TriviaSessionStatus.finished)
        .all()
    )
    return sum(1 for s in open_sessions if _aware(s.created_at) < _aware(cutoff))


# ---------- State ----------

def to_state(session: TriviaSingleSession, last_answer: Optional[LastAnswer] = None) -> SingleSessionState:
    total = len(session.question_ids or [])
    question = None
    current = session.current_question
    if session.status == TriviaSessionStatus.active and current:
        options = current["options"]
        question = SessionQuestion(
            index=session.current_index,
            id=current["id"],
            question_text=current["question_text"],
            question_type=current["question_type"],
            option_a=options["a"],
            option_b=options["b"],
            option_c=options.get("c"),
            option_d=options.get("d"),
        )

    grace_expires_in_ms = None
    if session.status == TriviaSessionStatus.awaiting_grace and session.grace_deadline:
        remaining = _aware(session.grace_deadline) - _now()
        grace_expires_in_ms = max(0, int(remaining.total_seconds() * 1000))

    return SingleSessionState(
        session_id=session.id,
        status=session.status.value,
        score=session.score,
        streak=session.streak,
        correct_count=session.correct_count,
        grace_tokens=session.grace_tokens,
        grace_tokens_used=session.grace_tokens_used,
        question_number=min(session.current_index + 1, total),
        total_questions=total,
        time_limit_ms=TIME_LIMIT_MS,
        question=question,
        last_answer=last_answer,
        grace_expires_in_ms=grace_expires_in_ms,
        result=SingleGameResult(**session.result) if session.result else None,
    )


def _last_answer(entry: dict) -> LastAnswer:
    return LastAnswer(
        question_id=entry["question_id"],
        selected=entry["selected"],
        correct=entry["correct"],
        correct_option=entry["correct_option"],
        timed_out=entry["timed_out"],
    )


# ---------- Internals ----------

def _get_owned(db: Session, user: User, session_id: str) -> TriviaSingleSession:
    session = (
        db.query(TriviaSingleSession)
        .filter(TriviaSingleSession.id == session_id)
        .with_for_update()
        .first()
    )
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Game not found")
    return session


def _serve(db: Session, session: TriviaSingleSession) -> bool:
    """Snapshot the question at current_index (options shuffled). False when the pool is used up."""
    ids = session.question_ids or []
    while session.current_index < len(ids):
        q = db.query(TriviaQuestion).filter(TriviaQuestion.id == ids[session.current_index]).first()
        if q is not None and q.is_approved:
            shuffled = trivia_svc._shuffle_options(q)
            session.current_question = {
                "id": q.id,
                "question_text": shuffled.question_text,
                "question_type": shuffled.question_type.value,
                "options": {
                    letter: getattr(shuffled, f"option_{letter}")
                    for letter in ("a", "b", "c", "d")
                    if getattr(shuffled, f"option_{letter}")
                },
                "correct": shuffled.correct_option.value,
            }
            session.current_served_at = _now()
            return True
        # Deleted or unapproved since the game started: skip it
        session.current_index += 1
    session.current_question = None
    return False


def _advance(db: Session, session: TriviaSingleSession) -> None:
    session.current_index += 1
    if not _serve(db, session):
        _finish(db, session)


def _rescore(session: TriviaSingleSession) -> None:
    # Graced answers are dropped, as the app did before submitting: the streak carries on
    scored = [a for a in (session.answers or []) if not a.get("graced")]
    session.score, session.max_streak = trivia_svc.compute_score_for_answers(scored)


def _resolve_expired_grace(db: Session, session: TriviaSingleSession, now: datetime) -> None:
    if (
        session.status == TriviaSessionStatus.awaiting_grace
        and session.grace_deadline
        and now > _aware(session.grace_deadline)
    ):
        _finish(db, session)


def _is_stale(session: TriviaSingleSession, now: datetime) -> bool:
    if (
        session.status == TriviaSessionStatus.awaiting_grace
        and session.grace_deadline
        and now > _aware(session.grace_deadline)
    ):
        return True
    if session.status == TriviaSessionStatus.active and session.current_served_at:
        # Current question expired unanswered (plus the grace window a token holder
        # would get): the game is over whether or not the player is still in the app
        limit_ms = TIME_LIMIT_MS + ALLOWANCE_MS
        if session.grace_tokens > 0:
            limit_ms += GRACE_WINDOW_MS + ALLOWANCE_MS
        if now > _aware(session.current_served_at) + timedelta(milliseconds=limit_ms):
            return True
    last = _aware(session.last_activity_at) or _aware(session.created_at)
    return last is None or now - last > IDLE_LIMIT


def _finish_unfinished(db: Session, user_id: str) -> None:
    open_sessions = (
        db.query(TriviaSingleSession)
        .filter(
            TriviaSingleSession.user_id == user_id,
            TriviaSingleSession.status != TriviaSessionStatus.finished,
        )
        .with_for_update()
        .all()
    )
    for session in open_sessions:
        _finish(db, session)


def _finish(db: Session, session: TriviaSingleSession) -> None:
    """Record the score exactly once. A pending (unused) grace answer stays wrong."""
    if session.status == TriviaSessionStatus.finished:
        return
    _rescore(session)
    session.status = TriviaSessionStatus.finished
    session.grace_deadline = None
    session.current_question = None
    session.finished_at = _now()
    result = trivia_svc.record_single_score(
        db,
        user_id=session.user_id,
        category=session.category.value,
        difficulty=session.difficulty.value,
        score=session.score,
        streak_length=session.max_streak,
        correct_count=session.correct_count,
        grace_tokens_used=session.grace_tokens_used,
        verified=True,
        session_id=session.id,
        created_at=_aware(session.created_at),   # dated by game start (research R10)
        commit=False,
    )
    session.result = result.model_dump(mode="json")
    logger.info("Trivia session %s finished: score %d", session.id, session.score)
