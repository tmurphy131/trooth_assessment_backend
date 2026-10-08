"""Trivia leaderboard competitions: windowed standings and prize finalization.

Standings count each eligible player's best single-player score at the
competition's difficulty, made inside [starts_at, ends_at). Ranking is
standard competition ranking (1, 1, 3): everyone tied for a place shares it,
and every player ranked within the prize places wins that place's prize.

finalize_competition() is idempotent and safe to call hourly from Cloud
Scheduler — each step (code, email, push) is recorded per winner and only
the missing steps run, so partial failures are retried on the next call.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, UTC, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.services import trivia_session
from app.models.trivia import (
    TriviaCompetition, TriviaCompetitionWinner, TriviaSingleScore, TriviaDifficulty,
)
from app.models.user import User, UserRole
from app.schemas.trivia import (
    CompetitionOut, CompetitionPrize, CompetitionStanding,
    CompetitionWinnerOut, CompetitionMyPrize,
)
from app.services import shopify_admin
from app.services import email as email_svc
from app.services.push_notification import notify_trivia_competition_won

logger = logging.getLogger(__name__)

STANDINGS_LIMIT = 10


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    # SQLite (tests) hands back naive datetimes; everything is stored in UTC
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def competition_status(comp: TriviaCompetition, now: datetime) -> str:
    if now < _aware(comp.starts_at):
        return "upcoming"
    if now < _aware(comp.ends_at):
        return "active"
    return "ended"


def get_current_competition(db: Session, now: Optional[datetime] = None) -> Optional[TriviaCompetition]:
    """The active competition, else the next upcoming one, else the latest ended one."""
    now = now or _now()
    comps = db.query(TriviaCompetition).order_by(TriviaCompetition.starts_at).all()
    by_status = {"active": [], "upcoming": [], "ended": []}
    for c in comps:
        by_status[competition_status(c, now)].append(c)
    if by_status["active"]:
        return by_status["active"][0]
    if by_status["upcoming"]:
        return by_status["upcoming"][0]
    if by_status["ended"]:
        return max(by_status["ended"], key=lambda c: _aware(c.ends_at))
    return None


def is_eligible(user: User) -> bool:
    if user.role == UserRole.admin:
        return False
    email = (user.email or "").lower()
    for entry in settings.trivia_competition_excluded_emails:
        if entry.startswith("@"):
            if email.endswith(entry):
                return False
        elif email == entry:
            return False
    return True


def prize_for_place(comp: TriviaCompetition, place: int) -> Optional[dict]:
    return next((p for p in (comp.prizes or []) if p["place"] == place), None)


def _max_prize_place(comp: TriviaCompetition) -> int:
    return max((p["place"] for p in (comp.prizes or [])), default=0)


@dataclass
class Standing:
    rank: int
    user: User
    score: int
    streak_length: int


def compute_standings(db: Session, comp: TriviaCompetition) -> list[Standing]:
    rows = (
        db.query(
            TriviaSingleScore.user_id,
            func.max(TriviaSingleScore.score).label("best_score"),
            func.max(TriviaSingleScore.streak_length).label("best_streak"),
        )
        .filter(
            TriviaSingleScore.difficulty == TriviaDifficulty(comp.difficulty),
            TriviaSingleScore.created_at >= _aware(comp.starts_at),
            TriviaSingleScore.created_at < _aware(comp.ends_at),
            TriviaSingleScore.score > 0,
            # Only server-run games count; client-graded legacy scores never win prizes
            TriviaSingleScore.verified == True,
        )
        .group_by(TriviaSingleScore.user_id)
        .all()
    )
    if not rows:
        return []

    users = {u.id: u for u in db.query(User).filter(User.id.in_([r.user_id for r in rows])).all()}
    eligible = [r for r in rows if r.user_id in users and is_eligible(users[r.user_id])]
    eligible.sort(key=lambda r: (-r.best_score, (users[r.user_id].name or "").lower()))

    standings: list[Standing] = []
    for i, r in enumerate(eligible):
        if standings and standings[-1].score == r.best_score:
            rank = standings[-1].rank
        else:
            rank = i + 1
        standings.append(Standing(rank=rank, user=users[r.user_id], score=r.best_score,
                                  streak_length=r.best_streak))
    return standings


def build_competition_out(db: Session, comp: TriviaCompetition, viewer: User,
                          now: Optional[datetime] = None) -> CompetitionOut:
    now = now or _now()
    status = competition_status(comp, now)
    out = CompetitionOut(
        slug=comp.slug,
        name=comp.name,
        status=status,
        difficulty=comp.difficulty,
        starts_at=_aware(comp.starts_at),
        ends_at=_aware(comp.ends_at),
        server_now=now,
        prizes=[CompetitionPrize(**p) for p in comp.prizes or []],
        is_eligible=is_eligible(viewer),
        finalized=comp.finalized_at is not None,
    )

    if status == "active":
        standings = compute_standings(db, comp)
        out.standings = [
            CompetitionStanding(rank=s.rank, user_id=s.user.id, display_name=s.user.name or "Player",
                                score=s.score, streak_length=s.streak_length)
            for s in standings[:STANDINGS_LIMIT]
        ]
        mine = next((s for s in standings if s.user.id == viewer.id), None)
        if mine:
            out.my_rank, out.my_score = mine.rank, mine.score

    elif status == "ended":
        # Winners are shown once they've been recorded; codes only to their owner
        for w in comp.winners:
            out.winners.append(CompetitionWinnerOut(
                place=w.place, display_name=w.display_name, score=w.score,
                is_me=w.user_id == viewer.id,
            ))
            if w.user_id == viewer.id and w.discount_code:
                prize = prize_for_place(comp, w.place) or {}
                out.my_prize = CompetitionMyPrize(
                    place=w.place,
                    label=prize.get("label", ""),
                    discount_code=w.discount_code,
                    code_expires_at=_aware(w.code_expires_at),
                    shop_url=settings.shop_url,
                )
    return out


# ---------- Finalization ----------

def _record_winners(db: Session, comp: TriviaCompetition) -> None:
    max_place = _max_prize_place(comp)
    for s in compute_standings(db, comp):
        if s.rank > max_place:
            break
        db.add(TriviaCompetitionWinner(
            competition_id=comp.id,
            user_id=s.user.id,
            display_name=s.user.name or "Player",
            place=s.rank,
            score=s.score,
        ))
    db.commit()


def _lock_winner(db: Session, winner_id: int) -> TriviaCompetitionWinner:
    # Row lock so overlapping scheduler runs can't double-create a code or double-send
    return (
        db.query(TriviaCompetitionWinner)
        .filter(TriviaCompetitionWinner.id == winner_id)
        .with_for_update()
        .one()
    )


def _ensure_code(db: Session, comp: TriviaCompetition, winner_id: int) -> None:
    w = _lock_winner(db, winner_id)
    if w.discount_code:
        db.commit()
        return
    prize = prize_for_place(comp, w.place)
    expires = _aware(comp.ends_at) + timedelta(days=comp.code_valid_days)
    code = shopify_admin.create_prize_code(
        place=w.place,
        amount=prize["amount"],
        title=f"Trivia {comp.name} – place {w.place} ({w.display_name})",
        starts_at=_now(),
        ends_at=expires,
    )
    w.discount_code = code.code
    w.shopify_discount_id = code.discount_id
    w.code_expires_at = expires
    db.commit()


def _ensure_notified(db: Session, comp: TriviaCompetition, winner_id: int) -> None:
    w = _lock_winner(db, winner_id)
    user = db.query(User).filter(User.id == w.user_id).first() if w.user_id else None
    if user is None:
        # Account deleted before we could notify — nothing to send
        w.emailed_at = w.emailed_at or _now()
        w.pushed_at = w.pushed_at or _now()
        db.commit()
        return

    if not w.emailed_at:
        prize = prize_for_place(comp, w.place) or {}
        if not email_svc.send_trivia_prize_email(db, user, w, comp, prize.get("label", "")):
            db.commit()
            raise RuntimeError(f"Prize email failed for winner {w.id}")
        w.emailed_at = _now()
        db.commit()
        w = _lock_winner(db, winner_id)

    if not w.pushed_at:
        try:
            notify_trivia_competition_won(db, user.id, w.place, comp.name)
        except Exception as e:  # push is best-effort; email is the delivery of record
            logger.warning(f"[trivia-competition] Push failed for winner {w.id}: {e}")
        w.pushed_at = _now()
    db.commit()


def finalize_competition(db: Session, comp_id: int, now: Optional[datetime] = None) -> dict:
    now = now or _now()
    comp = (
        db.query(TriviaCompetition)
        .filter(TriviaCompetition.id == comp_id)
        .with_for_update()
        .one()
    )
    if comp.finalized_at is not None:
        db.commit()
        return {"slug": comp.slug, "status": "already_finalized"}
    if now < _aware(comp.ends_at):
        db.commit()
        return {"slug": comp.slug, "status": "not_ended"}

    if not comp.winners:
        # A game started before the end counts (dated by its start). Close abandoned
        # ones; if someone is still mid-game, try again next hour.
        db.commit()
        if trivia_session.games_in_progress_before(db, comp.ends_at, now):
            return {"slug": comp.slug, "status": "waiting_for_games"}
        comp = (
            db.query(TriviaCompetition)
            .filter(TriviaCompetition.id == comp_id)
            .with_for_update()
            .one()
        )
        if not comp.winners:   # re-check: another run may have recorded them meanwhile
            _record_winners(db, comp)
        else:
            db.commit()
        db.refresh(comp)
    else:
        db.commit()

    errors = []
    for w in list(comp.winners):
        try:
            _ensure_code(db, comp, w.id)
            _ensure_notified(db, comp, w.id)
        except Exception as e:
            db.rollback()
            logger.error(f"[trivia-competition] Winner {w.id} ({comp.slug}) incomplete: {e}", exc_info=True)
            errors.append({"winner_id": w.id, "error": str(e)})

    db.refresh(comp)
    done = all(w.discount_code and w.emailed_at for w in comp.winners)
    if done:
        comp.finalized_at = now
        db.commit()
        try:
            email_svc.send_trivia_competition_admin_summary(comp)
        except Exception as e:
            logger.error(f"[trivia-competition] Admin summary failed for {comp.slug}: {e}")

    logger.info(f"[trivia-competition] {comp.slug}: {len(comp.winners)} winners, finalized={done}, errors={len(errors)}")
    return {
        "slug": comp.slug,
        "status": "finalized" if done else "incomplete",
        "winners": [
            {"place": w.place, "display_name": w.display_name, "score": w.score,
             "has_code": bool(w.discount_code), "emailed": bool(w.emailed_at)}
            for w in comp.winners
        ],
        "errors": errors,
    }


def finalize_due_competitions(db: Session, now: Optional[datetime] = None) -> list[dict]:
    now = now or _now()
    due = (
        db.query(TriviaCompetition.id)
        .filter(TriviaCompetition.finalized_at.is_(None), TriviaCompetition.ends_at <= now)
        .all()
    )
    return [finalize_competition(db, row.id, now) for row in due]
