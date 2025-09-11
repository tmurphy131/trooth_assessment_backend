from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User
from app.services.auth import require_apprentice
from app.models.notification import Notification
from app.models.agreement import Agreement
from pydantic import BaseModel
from app.services.email import send_notification_email

class RevokeMentorBody(BaseModel):
    reason: str | None = None

router = APIRouter(prefix="/apprentice", tags=["apprentice"])

@router.post("/mentor/revoke", response_model=dict)
def revoke_current_mentor(
    body: RevokeMentorBody | None = None,
    db: Session = Depends(get_db),
    apprentice: User = Depends(require_apprentice)
):
    """Allow an apprentice to revoke (deactivate) their active mentor relationship.

    Behavior:
    - Finds active MentorApprentice row for apprentice.
    - Sets active = False (soft revoke) rather than delete for audit trail.
    - Creates a notification for former mentor (optional) so they are aware.
    - Returns status with previous mentor_id if existed.
    """
    mapping = db.query(MentorApprentice).filter_by(apprentice_id=apprentice.id, active=True).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="No active mentor relationship to revoke")
    # Prevent revoke if there is a pending (awaiting signatures) agreement with this mentor
    pending = (
        db.query(Agreement)
        .filter(
            Agreement.mentor_id == mapping.mentor_id,
            (Agreement.apprentice_id == apprentice.id) | (Agreement.apprentice_email == apprentice.email),
            Agreement.status.in_(["draft", "awaiting_apprentice", "awaiting_parent"])
        )
        .first()
    )
    if pending:
        raise HTTPException(status_code=409, detail="Cannot revoke while an agreement is pending signatures")
    mapping.active = False
    db.add(mapping)
    # Notify mentor
    try:
        reason = (body.reason.strip() if body and body.reason else None)
        base_msg = f"Apprentice {apprentice.name or apprentice.email} revoked the mentorship"
        full_msg = base_msg + (f" – Reason: {reason}" if reason else "")
        db.add(Notification(user_id=mapping.mentor_id, message=full_msg, link=None))
        # Email mentor (best-effort)
        mentor_user = db.query(User).filter_by(id=mapping.mentor_id).first()
        if mentor_user and mentor_user.email:
            subj = "Mentorship Revoked"
            email_body = full_msg
            try:
                send_notification_email(mentor_user.email, subj, email_body)
            except Exception:
                pass
    except Exception:
        pass
    db.commit()
    return {"revoked": True, "mentor_id": mapping.mentor_id, "reason": body.reason if body else None}


@router.get("/mentor/status", response_model=dict)
def get_mentor_status(
    db: Session = Depends(get_db),
    apprentice: User = Depends(require_apprentice)
):
    """Return the apprentice's current mentor relationship status.

    Response shape:
    { "has_active": bool, "mentor": { "id": str, "name": str, "email": str } | None }
    """
    mapping = db.query(MentorApprentice).filter_by(apprentice_id=apprentice.id, active=True).first()
    if not mapping:
        return {"has_active": False, "mentor": None}
    mentor_user = db.query(User).filter_by(id=mapping.mentor_id).first()
    mentor_info = None
    if mentor_user:
        mentor_info = {"id": mentor_user.id, "name": mentor_user.name, "email": mentor_user.email}
    return {"has_active": True, "mentor": mentor_info}


@router.get("/agreements/pending", response_model=list[dict])
def list_pending_agreements(
    db: Session = Depends(get_db),
    apprentice: User = Depends(require_apprentice)
):
    """List agreements for this apprentice that are pending (not fully signed / completed).

    Pending statuses: draft, awaiting_apprentice, awaiting_parent.
    Returns list of objects: id, status, mentor_id, mentor_name, created_at, template_version.
    """
    pending_statuses = ["draft", "awaiting_apprentice", "awaiting_parent"]
    q = (
        db.query(Agreement)
        .filter(
            (Agreement.apprentice_id == apprentice.id) | (Agreement.apprentice_email == apprentice.email),
            Agreement.status.in_(pending_statuses)
        )
        .order_by(Agreement.created_at.desc())
    )
    rows = q.all()
    # Collect mentor ids for batch fetch
    mentor_ids = {r.mentor_id for r in rows}
    mentor_map = {}
    if mentor_ids:
        mentors = db.query(User).filter(User.id.in_(mentor_ids)).all()
        mentor_map = {m.id: m for m in mentors}
    out = []
    for r in rows:
        mu = mentor_map.get(r.mentor_id)
        out.append({
            "id": r.id,
            "status": r.status,
            "mentor_id": r.mentor_id,
            "mentor_name": mu.name if mu else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "template_version": r.template_version,
        })
    return out