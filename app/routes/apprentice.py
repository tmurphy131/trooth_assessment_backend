from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.report_summary import public_full_report
from app.db import get_db
from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User
from app.models.assessment_draft import AssessmentDraft
from app.services.auth import require_apprentice
from app.models.notification import Notification
from app.models.agreement import Agreement
from pydantic import BaseModel
from app.services.email import send_notification_email
from app.services.push_notification import notify_mentorship_revoked
import logging

logger = logging.getLogger(__name__)

class RevokeMentorBody(BaseModel):
    mentor_id: str
    reason: str | None = None

router = APIRouter(prefix="/apprentice", tags=["apprentice"])

@router.post("/mentor/revoke", response_model=dict)
def revoke_current_mentor(
    body: RevokeMentorBody,
    db: Session = Depends(get_db),
    apprentice: User = Depends(require_apprentice)
):
    """Allow an apprentice to revoke (deactivate) a specific active mentor relationship.

    Behavior:
    - Requires mentor_id in request body to identify which mentor to revoke.
    - Sets active = False (soft revoke) rather than delete for audit trail.
    - Creates a notification for former mentor so they are aware.
    - Returns status with previous mentor_id.
    """
    mapping = db.query(MentorApprentice).filter_by(
        apprentice_id=apprentice.id, mentor_id=body.mentor_id, active=True
    ).first()
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
        # Push notification to mentor
        try:
            notify_mentorship_revoked(
                db=db,
                mentor_id=mapping.mentor_id,
                apprentice_name=apprentice.name or apprentice.email
            )
        except Exception:
            pass
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
    """Return all active mentor relationships for the apprentice.

    Response shape:
    { "has_active": bool, "mentors": [{ "id": str, "name": str, "email": str }, ...] }
    """
    mappings = db.query(MentorApprentice).filter_by(apprentice_id=apprentice.id, active=True).all()
    if not mappings:
        return {"has_active": False, "mentors": []}
    mentor_ids = [m.mentor_id for m in mappings]
    mentor_users = db.query(User).filter(User.id.in_(mentor_ids)).all()
    mentor_map = {u.id: u for u in mentor_users}
    mentors = [
        {"id": u.id, "name": u.name, "email": u.email}
        for mid in mentor_ids
        if (u := mentor_map.get(mid))
    ]
    return {"has_active": bool(mentors), "mentors": mentors}


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


@router.get("/my-assessments/{id}/full-report", response_model=dict)
def get_my_full_report(
    id: str,
    db: Session = Depends(get_db),
    apprentice: User = Depends(require_apprentice),
):
    """Get full AI report for apprentice's own assessment (premium feature).
    
    Premium apprentices can view the full AI-generated report for their own
    completed assessments. This provides deeper insights into strengths, 
    growth areas, and personalized recommendations.
    
    The 'id' parameter can be either:
    - An Assessment.id (from /progress/reports endpoint)
    - An AssessmentDraft.id (from older API calls)
    
    Returns 403 if user is not premium.
    Returns 404 if not found or not owned by this apprentice.
    Returns 400 if assessment not yet completed/scored.
    """
    from app.services.full_report import get_or_generate_full_report
    from app.services.auth import is_premium_user
    from app.models.assessment import Assessment
    
    # Check premium status using proper function (handles enum, env var, admin, etc.)
    if not is_premium_user(apprentice):
        raise HTTPException(
            status_code=403,
            detail="Premium subscription required for full reports"
        )
    
    # Try to find by Assessment.id first (from /progress/reports endpoint)
    assessment = db.query(Assessment).filter(
        Assessment.id == id,
        Assessment.apprentice_id == apprentice.id
    ).first()
    
    draft = None
    if assessment:
        # Found as Assessment - look up corresponding draft by template_id
        logger.info(f"Found Assessment {id}, looking up corresponding draft")
        draft = db.query(AssessmentDraft).filter(
            AssessmentDraft.template_id == assessment.template_id,
            AssessmentDraft.apprentice_id == apprentice.id,
            AssessmentDraft.is_submitted == True
        ).order_by(AssessmentDraft.updated_at.desc()).first()
    else:
        # Try as draft_id (legacy API calls)
        draft = db.query(AssessmentDraft).filter(
            AssessmentDraft.id == id,
            AssessmentDraft.apprentice_id == apprentice.id
        ).first()
        if draft:
            # Also get the Assessment for caching
            assessment = db.query(Assessment).filter_by(
                apprentice_id=apprentice.id,
                template_id=draft.template_id
            ).order_by(Assessment.created_at.desc()).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    if not draft.is_submitted:
        raise HTTPException(status_code=400, detail="Assessment not yet completed")
    
    if assessment is None:  # legacy draft-only submission: serve its stored copy, never generate
        cached = (draft.score or {}).get("full_report_v1")
        if not cached:
            raise HTTPException(status_code=404, detail="Assessment not found")
        return {"report": public_full_report(cached, None), "cached": True, "draft_id": draft.id,
                "generated_at": (draft.score or {}).get("full_report_generated_at")}
    # Stored copy, or generate once (concurrent callers wait); 503 instead of 500 on failure
    result = get_or_generate_full_report(db, assessment)
    result["draft_id"] = draft.id
    return result


