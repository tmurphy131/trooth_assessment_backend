from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
from datetime import datetime, UTC
import logging

logger = logging.getLogger(__name__)

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
    from app.services.ai_scoring import generate_full_report, _build_v2_prompt_input
    from app.models.assessment_template import AssessmentTemplate
    from app.models.question import Question
    from app.models.category import Category
    from app.models.assessment_template_question import AssessmentTemplateQuestion
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
    
    # Check if full report is cached - check BOTH draft.score AND Assessment.scores
    scores = draft.score or {}
    cached_full_report = scores.get("full_report_v1")
    
    # If not in draft, check Assessment.scores (where email/PDF endpoints store it)
    if not cached_full_report:
        if assessment and assessment.scores:
            cached_full_report = assessment.scores.get("full_report_v1")
            if cached_full_report:
                logger.info(f"Found cached full report in Assessment.scores for id {id}")
    
    if cached_full_report:
        logger.info(f"Returning cached full report for id {id}")
        return {
            "report": cached_full_report,
            "cached": True,
            "draft_id": draft.id,
            "generated_at": scores.get("full_report_generated_at")
        }
    
    # Generate full report on demand
    logger.info(f"Generating full report on demand for id {id}")
    
    # Get questions for this template (with eager loading of question relationship)
    from sqlalchemy.orm import joinedload
    template_questions = db.query(AssessmentTemplateQuestion)\
        .options(joinedload(AssessmentTemplateQuestion.question))\
        .filter_by(template_id=draft.template_id)\
        .order_by(AssessmentTemplateQuestion.order)\
        .all()
    
    questions_list = []
    for tq in template_questions:
        q = tq.question
        if not q:
            continue
        category_name = 'General'
        if q.category_id:
            cat = db.query(Category).filter_by(id=q.category_id).first()
            if cat:
                category_name = cat.name
        q_dict = {
            'id': str(q.id),
            'text': q.text,
            'question_type': q.question_type.value if hasattr(q.question_type, 'value') else str(q.question_type),
            'category': category_name,
        }
        if q.options:
            q_dict['options'] = [
                {'id': str(opt.id), 'text': opt.option_text, 'is_correct': opt.is_correct}
                for opt in q.options
            ]
        questions_list.append(q_dict)
    
    # Get previous assessments for trend analysis
    previous_drafts = db.query(AssessmentDraft).filter(
        AssessmentDraft.apprentice_id == apprentice.id,
        AssessmentDraft.is_submitted == True,
        AssessmentDraft.id != draft.id
    ).order_by(AssessmentDraft.updated_at.desc()).limit(5).all()
    
    previous_assessments = []
    for pd in previous_drafts:
        if pd.score:
            previous_assessments.append({
                'date': pd.updated_at.isoformat() if pd.updated_at else None,
                'health_score': pd.score.get('mentor_blob_v2', {}).get('health_score'),
                'strengths': pd.score.get('mentor_blob_v2', {}).get('strengths', []),
                'gaps': pd.score.get('mentor_blob_v2', {}).get('gaps', [])
            })
    
    # Build the payload for the full report
    apprentice_info = {
        'id': str(apprentice.id),
        'name': apprentice.name if apprentice.name else 'Apprentice',
        'age': None,
        'church': None
    }
    
    payload, _ = _build_v2_prompt_input(
        apprentice=apprentice_info,
        assessment_id=draft.id,
        template_id=str(draft.template_id),
        submitted_at=draft.updated_at.isoformat() if draft.updated_at else None,
        answers=draft.answers or {},
        questions=questions_list,
        previous_assessments=previous_assessments
    )
    
    try:
        # Generate the full report
        full_report = generate_full_report(payload, previous_assessments)
        
        # Cache the report in BOTH draft.score AND Assessment.scores
        if not scores:
            scores = {}
        scores['full_report_v1'] = full_report
        scores['full_report_generated_at'] = datetime.now(UTC).isoformat()
        draft.score = scores
        
        # Also save to Assessment.scores for email/PDF endpoints
        # (assessment already loaded above if it existed)
        if assessment:
            assess_scores = dict(assessment.scores or {})
            assess_scores['full_report_v1'] = full_report
            assess_scores['full_report_generated_at'] = datetime.now(UTC).isoformat()
            assessment.scores = assess_scores
        
        db.commit()
        
        return {
            "report": full_report,
            "cached": False,
            "draft_id": draft.id,
            "generated_at": full_report.get("_meta", {}).get("generated_at")
        }
        
    except Exception as e:
        logger.error(f"Failed to generate full report for id {id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate full report: {str(e)}"
        )