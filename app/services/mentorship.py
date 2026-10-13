"""Mentor–apprentice connection checks and agreement linking (specs/007-connected-apprentice-linking)."""
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.agreement import Agreement
from app.models.mentor_apprentice import MentorApprentice

logger = logging.getLogger(__name__)


def has_active_connection(db: Session, mentor_id: str, apprentice_id: str) -> bool:
    """True only while the mentorship is active; an ended one doesn't count."""
    return db.query(MentorApprentice.mentor_id).filter(
        MentorApprentice.mentor_id == mentor_id,
        MentorApprentice.apprentice_id == apprentice_id,
        MentorApprentice.active == True,  # noqa: E712
    ).first() is not None


def attach_pending_agreements(db: Session, mentor_id: str, email: str, apprentice_id: str) -> int:
    """Tie this mentor's not-yet-tied agreements for `email` to the apprentice. Returns the count.

    Called when an apprentice accepts that mentor's invitation to `email`, so a hidden or
    different account email still finds them. Already-tied agreements never move. The caller commits.
    """
    if not email:
        return 0
    count = (
        db.query(Agreement)
        .filter(
            Agreement.mentor_id == mentor_id,
            Agreement.apprentice_id.is_(None),
            func.lower(Agreement.apprentice_email) == email.strip().lower(),
        )
        .update({"apprentice_id": apprentice_id}, synchronize_session=False)
    )
    if count:
        logger.info("Attached %d agreement(s) mentor_id=%s apprentice_id=%s", count, mentor_id, apprentice_id)
    return count
