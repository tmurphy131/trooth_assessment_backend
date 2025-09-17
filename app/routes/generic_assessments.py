from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta, UTC
import base64, json, uuid

from app.db import get_db
from app.models.user import User, UserRole
from app.models.assessment import Assessment
from app.models.assessment_template import AssessmentTemplate
from app.models.mentor_apprentice import MentorApprentice
from app.services.auth import get_current_user
from app.services.ai_scoring_generic import score_generic_assessment
from app.services.generic_assessment_report import generate_html as gen_html, generate_pdf as gen_pdf
from app.services.email import send_email, render_generic_assessment_email
from app.services.audit import log_assessment_submit, log_assessment_view, log_email_send
from app.models.email_send_event import EmailSendEvent
from sqlalchemy import func
from app.core.settings import settings

router = APIRouter()


def _encode_cursor(created_at: datetime, assessment_id: str) -> str:
    payload = {"ts": created_at.isoformat(), "id": assessment_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    data = json.loads(raw)
    return datetime.fromisoformat(data["ts"]), data["id"]


def _apprentice_can_use_template(db: Session, apprentice_id: str, tpl: AssessmentTemplate) -> bool:
    if not tpl.is_published:
        return False
    if tpl.is_master_assessment:
        return False
    if not tpl.created_by:
        return True
    link = (
        db.query(MentorApprentice)
        .filter(MentorApprentice.mentor_id == tpl.created_by, MentorApprentice.apprentice_id == apprentice_id, MentorApprentice.active == True)
        .first()
    )
    return bool(link)


def _require_mentor_or_admin_for_apprentice(db: Session, current_user: User, apprentice_id: str) -> None:
    if current_user.role == UserRole.mentor:
        link = (
            db.query(MentorApprentice)
            .filter(
                MentorApprentice.mentor_id == current_user.id,
                MentorApprentice.apprentice_id == apprentice_id,
                MentorApprentice.active == True,
            )
            .first()
        )
        if not link:
            raise HTTPException(status_code=403, detail="Mentor is not assigned to this apprentice")
    elif current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only mentors or admins permitted")


# ---- Submit ----
@router.post("/templates/{template_id}/submit")
def submit_generic(template_id: str, body: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.apprentice:
        raise HTTPException(status_code=403, detail="Only apprentices can submit this assessment")
    tpl = db.query(AssessmentTemplate).filter(AssessmentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if not _apprentice_can_use_template(db, current_user.id, tpl):
        raise HTTPException(status_code=403, detail="Template not available for this apprentice")

    answers = body.get("answers") if isinstance(body, dict) else None
    if not isinstance(answers, dict) or not answers:
        raise HTTPException(status_code=400, detail="answers are required")

    strategy = (tpl.scoring_strategy or "ai_generic").lower()
    rubric = tpl.rubric_json if isinstance(tpl.rubric_json, dict) else None
    if strategy in ("ai_generic", "deterministic"):
        scores = score_generic_assessment(answers, rubric)
    elif strategy == "none":
        scores = {"overall_score": 0.0, "categories": [], "scoring_version": "none_v1", "model": "none"}
    else:
        # Unknown strategy; safe fallback
        scores = score_generic_assessment(answers, rubric)

    # annotate with template version
    scores["template_version"] = tpl.version or 1
    scores["template_id"] = tpl.id

    assessment = Assessment(
        id=str(uuid.uuid4()),
        apprentice_id=current_user.id,
        template_id=tpl.id,
        answers=answers,
        scores=scores,
        recommendation=None,
        category=f"template:{tpl.key or tpl.id}"
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    log_assessment_submit(current_user.id, assessment.id, "generic", tpl.id, scores.get("template_version"))
    return {
        "id": assessment.id,
        "apprentice_id": assessment.apprentice_id,
        "scores": assessment.scores,
        "created_at": assessment.created_at,
    }


# ---- Latest ----
@router.get("/templates/{template_id}/latest")
def latest_generic(template_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tpl = db.query(AssessmentTemplate).filter(AssessmentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if current_user.role == UserRole.apprentice and not _apprentice_can_use_template(db, current_user.id, tpl):
        raise HTTPException(status_code=403, detail="Template not available for this apprentice")
    a = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == current_user.id, Assessment.template_id == template_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="No assessment found for this template")
    log_assessment_view(current_user.id, a.id, "generic", current_user.role.value, current_user.id)
    return a.scores or {}


# ---- History ----
@router.get("/templates/{template_id}/history")
def history_generic(template_id: str, limit: int = 20, cursor: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if limit <= 0 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    base_query = db.query(Assessment).filter(Assessment.apprentice_id == current_user.id, Assessment.template_id == template_id)
    if cursor:
        try:
            ts, aid = _decode_cursor(cursor)
            base_query = base_query.filter((Assessment.created_at < ts) | ((Assessment.created_at == ts) & (Assessment.id < aid)))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cursor")
    rows = base_query.order_by(Assessment.created_at.desc(), Assessment.id.desc()).limit(limit + 1).all()
    if not rows:
        return {"results": [], "next_cursor": None}
    has_more = len(rows) > limit
    rows = rows[:limit]
    for a in rows:
        log_assessment_view(current_user.id, a.id, "generic", current_user.role.value, current_user.id)
    next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
    return {"results": [(r.scores or {}) for r in rows], "next_cursor": next_cursor}


# ---- Email report ----
EMAIL_MAX_PER_HOUR = 5
EMAIL_WINDOW_SECONDS = 3600


def _enforce_email_rate_limit(db: Session, user_id: str) -> None:
    window_start = datetime.now(UTC) - timedelta(seconds=EMAIL_WINDOW_SECONDS)
    count = (
        db.query(func.count(EmailSendEvent.id))
        .filter(
            EmailSendEvent.sender_user_id == user_id,
            EmailSendEvent.created_at >= window_start,
            EmailSendEvent.purpose == "report",
            EmailSendEvent.category == "generic",
        )
        .scalar()
    )
    if count and count >= EMAIL_MAX_PER_HOUR:
        raise HTTPException(status_code=429, detail={"error": "RATE_LIMIT", "retry_after_seconds": EMAIL_WINDOW_SECONDS})


@router.post("/templates/{template_id}/email-report")
def email_generic(template_id: str, body: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.apprentice:
        raise HTTPException(status_code=403, detail="Only apprentices can email their report")
    to_email = (body.get("to_email") or "").strip() if isinstance(body, dict) else ""
    include_pdf = bool(body.get("include_pdf")) if isinstance(body, dict) else True
    if not to_email:
        raise HTTPException(status_code=400, detail="to_email is required")

    tpl = db.query(AssessmentTemplate).filter(AssessmentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if not _apprentice_can_use_template(db, current_user.id, tpl):
        raise HTTPException(status_code=403, detail="Template not available for this apprentice")
    _enforce_email_rate_limit(db, current_user.id)

    a = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == current_user.id, Assessment.template_id == template_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")

    html, plain = render_generic_assessment_email(tpl.name or "Assessment Report", getattr(current_user, 'name', None), a.scores or {})
    attachments = None
    if include_pdf:
        pdf = gen_pdf(tpl.name or "Assessment Report", getattr(current_user, 'name', None), a.scores or {})
        safe_name = (getattr(current_user, 'name', 'Apprentice') or 'Apprentice').lower().replace(' ', '_')
        today = datetime.now(UTC).strftime('%Y%m%d')
        attachments = [{
            "filename": f"assessment_report_{safe_name}_{today}.pdf",
            "mime_type": "application/pdf",
            "data": pdf,
        }]
    subject = f"{tpl.name or 'Assessment Report'} — {getattr(current_user, 'name', 'Apprentice')} — {datetime.now(UTC).date()}"
    sent = send_email(to_email, subject, html, plain, attachments=attachments)
    event = EmailSendEvent(
        sender_user_id=current_user.id,
        target_user_id=current_user.id,
        assessment_id=a.id,
        category="generic",
        template_version=(a.scores or {}).get("template_version"),
        role_context=current_user.role.value,
        purpose="report",
    )
    db.add(event)
    try:
        db.commit()
    except Exception:
        db.rollback()
    log_email_send(current_user.id, a.id, "generic", (a.scores or {}).get("template_version"), current_user.id, "report", current_user.role.value, bool(sent))
    return {"sent": bool(sent), "assessment_id": a.id}


# ---- Mentor/admin views ----
@router.get("/templates/{template_id}/{apprentice_id}/latest")
def mentor_latest_generic(template_id: str, apprentice_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tpl = db.query(AssessmentTemplate).filter(AssessmentTemplate.id == template_id).first()
    if not tpl or not tpl.is_published or tpl.is_master_assessment:
        raise HTTPException(status_code=404, detail="Template not available")
    _require_mentor_or_admin_for_apprentice(db, current_user, apprentice_id)
    a = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == apprentice_id, Assessment.template_id == template_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="No assessment found for this template")
    log_assessment_view(current_user.id, a.id, "generic", current_user.role.value, apprentice_id)
    return a.scores or {}


@router.get("/templates/{template_id}/{apprentice_id}/history")
def mentor_history_generic(
    template_id: str,
    apprentice_id: str,
    limit: int = 20,
    cursor: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if limit <= 0 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    tpl = db.query(AssessmentTemplate).filter(AssessmentTemplate.id == template_id).first()
    if not tpl or not tpl.is_published or tpl.is_master_assessment:
        raise HTTPException(status_code=404, detail="Template not available")
    _require_mentor_or_admin_for_apprentice(db, current_user, apprentice_id)

    base_query = db.query(Assessment).filter(Assessment.apprentice_id == apprentice_id, Assessment.template_id == template_id)
    if cursor:
        try:
            ts, aid = _decode_cursor(cursor)
            base_query = base_query.filter((Assessment.created_at < ts) | ((Assessment.created_at == ts) & (Assessment.id < aid)))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cursor")
    rows = base_query.order_by(Assessment.created_at.desc(), Assessment.id.desc()).limit(limit + 1).all()
    if not rows:
        return {"results": [], "next_cursor": None}
    has_more = len(rows) > limit
    rows = rows[:limit]
    for a in rows:
        log_assessment_view(current_user.id, a.id, "generic", current_user.role.value, apprentice_id)
    next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
    return {"results": [(r.scores or {}) for r in rows], "next_cursor": next_cursor}


@router.post("/templates/{template_id}/{apprentice_id}/email-report")
def mentor_email_generic(
    template_id: str,
    apprentice_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tpl = db.query(AssessmentTemplate).filter(AssessmentTemplate.id == template_id).first()
    if not tpl or not tpl.is_published or tpl.is_master_assessment:
        raise HTTPException(status_code=404, detail="Template not available")
    _require_mentor_or_admin_for_apprentice(db, current_user, apprentice_id)

    to_email = (body.get("to_email") or "").strip() if isinstance(body, dict) else ""
    include_pdf = bool(body.get("include_pdf")) if isinstance(body, dict) else True
    if not to_email:
        raise HTTPException(status_code=400, detail="to_email is required")
    _enforce_email_rate_limit(db, current_user.id)

    a = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == apprentice_id, Assessment.template_id == template_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    # Render based on the apprentice context (no name known here unless we fetch user)
    html, plain = render_generic_assessment_email(tpl.name or "Assessment Report", None, a.scores or {})
    attachments = None
    if include_pdf:
        pdf = gen_pdf(tpl.name or "Assessment Report", None, a.scores or {})
        today = datetime.now(UTC).strftime('%Y%m%d')
        attachments = [{
            "filename": f"assessment_report_{apprentice_id}_{today}.pdf",
            "mime_type": "application/pdf",
            "data": pdf,
        }]
    subject = f"{tpl.name or 'Assessment Report'} — {datetime.now(UTC).date()}"
    sent = send_email(to_email, subject, html, plain, attachments=attachments)
    event = EmailSendEvent(
        sender_user_id=current_user.id,
        target_user_id=apprentice_id,
        assessment_id=a.id,
        category="generic",
        template_version=(a.scores or {}).get("template_version"),
        role_context=current_user.role.value,
        purpose="report",
    )
    db.add(event)
    try:
        db.commit()
    except Exception:
        db.rollback()
    log_email_send(current_user.id, a.id, "generic", (a.scores or {}).get("template_version"), apprentice_id, "report", current_user.role.value, bool(sent))
    return {"sent": bool(sent), "assessment_id": a.id}
