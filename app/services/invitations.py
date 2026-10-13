"""Invitation acceptance and invite-code redemption (specs/006-invite-codes)."""
import logging
from datetime import datetime, timedelta, UTC

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.exceptions import NotFoundException, ValidationException
from app.models.apprentice_invitation import ApprenticeInvitation
from app.models.invite_code_attempt import InviteCodeAttempt
from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User
from app.services.invite_codes import generate_invite_code, normalize_invite_code

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 10
ATTEMPT_WINDOW = timedelta(hours=1)

EXPIRED_DETAIL = "This invitation has expired."
ALREADY_ACCEPTED_DETAIL = "Invitation has already been accepted"


def _now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def create_code_for(db: Session) -> str:
    """A code no existing invitation uses. Collisions are astronomically rare; retry a few times anyway."""
    for _ in range(5):
        code = generate_invite_code()
        if not db.query(ApprenticeInvitation.id).filter(ApprenticeInvitation.code == code).first():
            return code
    raise RuntimeError("Could not generate a unique invite code")


def accept_invitation(db: Session, invitation: ApprenticeInvitation, apprentice: User) -> str:
    """Accept an invitation for `apprentice`. Returns "created", "reactivated" or "already_active".

    The caller commits. Marking the invite accepted is a conditional update, so of two
    concurrent acceptances exactly one wins and the other gets "already accepted".
    """
    expires_at = invitation.expires_at.replace(tzinfo=None) if invitation.expires_at.tzinfo else invitation.expires_at
    if expires_at < _now_naive():
        raise ValidationException(EXPIRED_DETAIL)

    updated = (
        db.query(ApprenticeInvitation)
        .filter(ApprenticeInvitation.id == invitation.id, ApprenticeInvitation.accepted == False)  # noqa: E712
        .update({"accepted": True}, synchronize_session=False)
    )
    if updated == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail=ALREADY_ACCEPTED_DETAIL)

    # Pairing with this mentor never touches the apprentice's other mentor relationships.
    existing = db.query(MentorApprentice).filter_by(
        apprentice_id=apprentice.id,
        mentor_id=invitation.mentor_id,
    ).first()
    if existing:
        if existing.active:
            return "already_active"
        existing.active = True
        return "reactivated"

    db.add(MentorApprentice(mentor_id=invitation.mentor_id, apprentice_id=apprentice.id))
    return "created"


def _record_attempt(db: Session, user_id: str, invitation_id: str | None, succeeded: bool) -> None:
    db.add(InviteCodeAttempt(user_id=user_id, invitation_id=invitation_id, succeeded=succeeded))
    db.commit()


def _check_rate_limit(db: Session, user_id: str) -> None:
    window_start = _now_naive() - ATTEMPT_WINDOW
    failures = (
        db.query(InviteCodeAttempt.created_at)
        .filter(
            InviteCodeAttempt.user_id == user_id,
            InviteCodeAttempt.succeeded == False,  # noqa: E712
            InviteCodeAttempt.created_at > window_start,
        )
        .order_by(InviteCodeAttempt.created_at.asc())
        .all()
    )
    if len(failures) < MAX_FAILED_ATTEMPTS:
        return
    # The rolling window reopens when the oldest counted failure turns an hour old.
    oldest = failures[0][0]
    retry_after = max(1, int((oldest + ATTEMPT_WINDOW - _now_naive()).total_seconds()) + 1)
    logger.warning("invite.redeem user_id=%s outcome=rate_limited", user_id)
    raise HTTPException(
        status_code=429,
        detail="Too many invalid codes. Try again later.",
        headers={"Retry-After": str(retry_after)},
    )


def redeem_code(db: Session, raw_code: str, apprentice: User) -> tuple[ApprenticeInvitation, str]:
    """Redeem an invite code for the signed-in apprentice. Returns (invitation, relationship)."""
    _check_rate_limit(db, apprentice.id)

    code = normalize_invite_code(raw_code)
    invitation = None
    if code is not None:
        invitation = db.query(ApprenticeInvitation).filter(ApprenticeInvitation.code == code).first()
    if invitation is None:
        _record_attempt(db, apprentice.id, None, succeeded=False)
        logger.info("invite.redeem user_id=%s outcome=not_found", apprentice.id)
        raise NotFoundException("Invite code not found")

    invitation_id = invitation.id
    try:
        relationship = accept_invitation(db, invitation, apprentice)
    except HTTPException as exc:
        db.rollback()
        outcome = "expired" if exc.detail == EXPIRED_DETAIL else "used"
        _record_attempt(db, apprentice.id, invitation_id, succeeded=False)
        logger.info("invite.redeem user_id=%s invitation_id=%s outcome=%s", apprentice.id, invitation_id, outcome)
        raise

    db.add(InviteCodeAttempt(user_id=apprentice.id, invitation_id=invitation_id, succeeded=True))
    db.commit()
    logger.info(
        "invite.redeem user_id=%s invitation_id=%s outcome=ok relationship=%s",
        apprentice.id, invitation_id, relationship,
    )
    return invitation, relationship
