from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
from typing import List
import base64
import json

from app.db import get_db
from app.models.assessment import Assessment
from app.models.user import User, UserRole
from app.schemas.spiritual_gifts import (
    SpiritualGiftsSubmission,
    SpiritualGiftsResult,
    GiftScore
)
from app.services.spiritual_gifts_scoring import score_spiritual_gifts
from app.core.spiritual_gifts_map import QUESTION_ITEMS
from app.services.auth import get_current_user, require_mentor, require_admin
from app.models.mentor_apprentice import MentorApprentice
from app.models.assessment_template import AssessmentTemplate
from app.models.spiritual_gift_definition import SpiritualGiftDefinition
from app.services.audit import (
    log_assessment_submit,
    log_assessment_view,
    log_template_publish,
    log_email_send,
)
from app.services.spiritual_gifts_report import generate_pdf, generate_html
from app.services.email import send_email
from app.models.email_send_event import EmailSendEvent
import os
import time  # retained for backward compatibility if needed elsewhere
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/assessments/spiritual-gifts", tags=["spiritual-gifts"])

TEMPLATE_KEY = "spiritual_gifts_v1"

def _serialize_scores(assessment: Assessment) -> SpiritualGiftsResult:
    scores = assessment.scores or {}
    return SpiritualGiftsResult(
        id=assessment.id,
        apprentice_id=assessment.apprentice_id,
        template_key=TEMPLATE_KEY,
        version=scores.get("template_version") or scores.get("version", 1),
        created_at=assessment.created_at,
        top_gifts_truncated=[GiftScore(**g) for g in scores.get("top_gifts_truncated", [])],
        top_gifts_expanded=[GiftScore(**g) for g in scores.get("top_gifts_expanded", [])],
        all_scores=[GiftScore(**g) for g in scores.get("all_scores", [])],
        rank_meta=scores.get("rank_meta", {})
    )


# ---------------- Admin governance schemas & helpers -----------------
class GiftDefinitionIn(BaseModel):
    gift_slug: str
    display_name: str
    short_summary: Optional[str] = None
    full_definition: str

class SpiritualGiftsTemplateDraft(BaseModel):
    version: int = Field(..., description="Incrementing version integer")
    gift_definitions: list[GiftDefinitionIn]

class PublishTemplateRequest(BaseModel):
    version: int

def _get_active_template(db: Session) -> AssessmentTemplate | None:
    # Prefer highest version; fallback to most recent created_at if version null
    return (
        db.query(AssessmentTemplate)
        .filter(AssessmentTemplate.name == "Spiritual Gifts Assessment", AssessmentTemplate.is_published == True)  # noqa: E712
        .order_by(AssessmentTemplate.version.desc().nullslast(), AssessmentTemplate.created_at.desc())
        .first()
    )

def _validate_unique_slugs(defs: list[GiftDefinitionIn]):
    slugs = [d.gift_slug for d in defs]
    if len(set(slugs)) != len(slugs):
        raise HTTPException(status_code=400, detail="Duplicate gift_slug in definitions payload")

@router.get("/admin/template", summary="Admin: get current published spiritual gifts template")
def admin_get_spiritual_gifts_template(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    tpl = _get_active_template(db)
    if not tpl:
        raise HTTPException(status_code=404, detail="No published template")
    # Aggregate definitions (latest version per slug) for convenience
    defs = db.query(SpiritualGiftDefinition).filter(SpiritualGiftDefinition.version == tpl.description_version if hasattr(tpl, 'description_version') else 1).all()  # may not have description_version column
    return {
        "template_id": tpl.id,
        "name": tpl.name,
        "description": tpl.description,
        "version": 1,
        "definitions": [
            {
                "gift_slug": d.gift_slug,
                "display_name": d.display_name,
                "short_summary": d.short_summary,
                "full_definition": d.full_definition,
                "version": d.version,
                "locale": d.locale,
            } for d in defs
        ]
    }

@router.post("/admin/template/draft", summary="Admin: create or replace draft gift definitions (idempotent per version)")
def admin_create_draft_spiritual_gifts(body: SpiritualGiftsTemplateDraft, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    _validate_unique_slugs(body.gift_definitions)
    # Insert definitions for provided version (replace existing for same version)
    existing = db.query(SpiritualGiftDefinition).filter(SpiritualGiftDefinition.version == body.version).all()
    if existing:
        # simplistic replace: delete then insert
        for row in existing:
            db.delete(row)
        db.flush()
    for gd in body.gift_definitions:
        row = SpiritualGiftDefinition(
            gift_slug=gd.gift_slug.lower(),
            display_name=gd.display_name,
            short_summary=gd.short_summary,
            full_definition=gd.full_definition,
            version=body.version,
            locale="en"
        )
        db.add(row)
    db.commit()
    return {"message": "draft definitions stored", "version": body.version, "count": len(body.gift_definitions)}

@router.post("/admin/template/publish", summary="Admin: publish spiritual gifts template version")
def admin_publish_spiritual_gifts(body: PublishTemplateRequest, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    # Ensure definitions exist for version
    defs = db.query(SpiritualGiftDefinition).filter(SpiritualGiftDefinition.version == body.version).all()
    if not defs:
        raise HTTPException(status_code=400, detail="No draft definitions for requested version")
    # Mark previous template (if any) still present; we allow multiple published but always choose latest by created_at
    tpl = AssessmentTemplate(
        name="Spiritual Gifts Assessment",
        description="Spiritual gifts assessment (version {})".format(body.version),
        is_published=True,
        is_master_assessment=False,
        version=body.version
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    log_template_publish(current_user.id, tpl.id, tpl.name, body.version)
    return {"message": "published", "template_id": tpl.id, "version": body.version}

@router.post("/submit", response_model=SpiritualGiftsResult)
def submit_spiritual_gifts(payload: SpiritualGiftsSubmission, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.apprentice:
        raise HTTPException(status_code=403, detail="Only apprentices can submit spiritual gifts assessments")
    if payload.template_key != TEMPLATE_KEY:
        raise HTTPException(status_code=400, detail="Invalid template_key")
    try:
        scored = score_spiritual_gifts(payload.answers)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    active_template = _get_active_template(db)
    template_version = active_template.version if active_template and active_template.version is not None else 1
    # augment scores with template metadata
    scored["template_version"] = template_version
    scored["template_id"] = active_template.id if active_template else None
    assessment = Assessment(
        id=str(uuid.uuid4()),
        apprentice_id=current_user.id,
        template_id=active_template.id if active_template else None,
        answers=payload.answers,
        scores=scored,
        recommendation=None,
        category="spiritual_gifts"
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    log_assessment_submit(current_user.id, assessment.id, "spiritual_gifts", assessment.template_id, scored.get("template_version"))
    return _serialize_scores(assessment)

@router.get("/latest", response_model=SpiritualGiftsResult)
def latest_spiritual_gifts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assessment = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == current_user.id, Assessment.category == "spiritual_gifts")
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="No spiritual gifts assessment found")
    log_assessment_view(current_user.id, assessment.id, "spiritual_gifts", current_user.role.value, current_user.id)
    return _serialize_scores(assessment)

class QuestionItem(BaseModel):
    code: str
    text: str

class QuestionsResponse(BaseModel):
    version: int
    count: int
    items: list[QuestionItem]

@router.get("/questions", response_model=QuestionsResponse, summary="Fetch ordered spiritual gifts questions (code + text)")
def get_spiritual_gifts_questions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return all question items in canonical order.

    Uses QUESTION_ITEMS from the core map. Text already includes ordinal numbering.
    Version is derived from active template if available; otherwise 1.
    """
    active_template = _get_active_template(db)
    version = active_template.version if active_template and active_template.version is not None else 1
    items = [QuestionItem(code=c, text=t) for c, _gift, t in QUESTION_ITEMS]
    return QuestionsResponse(version=version, count=len(items), items=items)

class HistoryPage(BaseModel):
    results: List[SpiritualGiftsResult]
    next_cursor: Optional[str] = None

class EmailReportRequest(BaseModel):
    to_email: str
    assessment_id: Optional[str] = Field(None, description="If omitted, latest assessment is used")
    include_pdf: bool = True
    include_html: bool = False

class EmailReportResponse(BaseModel):
    sent: bool
    assessment_id: str
    template_version: int
    pdf_bytes: Optional[int] = None
    html_bytes: Optional[int] = None

EMAIL_MAX_PER_HOUR = 5
EMAIL_WINDOW_SECONDS = 3600

def _enforce_email_rate_limit(db: Session, user_id: str) -> int:
    """DB-backed rate limit: count events in window for this sender & purpose 'report'.
    Returns remaining allowance (may be negative if just exceeded)."""
    window_start = datetime.utcnow() - timedelta(seconds=EMAIL_WINDOW_SECONDS)
    count = (
        db.query(func.count(EmailSendEvent.id))
        .filter(
            EmailSendEvent.sender_user_id == user_id,
            EmailSendEvent.created_at >= window_start,
            EmailSendEvent.purpose == "report",
            EmailSendEvent.category == "spiritual_gifts",
        )
        .scalar()
    )
    remaining = EMAIL_MAX_PER_HOUR - (count or 0)
    if count is not None and count >= EMAIL_MAX_PER_HOUR:
        retry_after = int(EMAIL_WINDOW_SECONDS / 60) * 60  # coarse seconds
        raise HTTPException(status_code=429, detail={
            "error": "RATE_LIMIT",
            "message": "Email report rate limit exceeded (5/hour)",
            "retry_after_seconds": EMAIL_WINDOW_SECONDS,
            "remaining": 0
        })
    return remaining

def _encode_cursor(created_at: datetime, assessment_id: str) -> str:
    payload = {"ts": created_at.isoformat(), "id": assessment_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(raw)
        return datetime.fromisoformat(data["ts"]), data["id"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cursor")

@router.get("/history", response_model=HistoryPage)
def history_spiritual_gifts(limit: int = 20, cursor: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if limit <= 0 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    base_query = db.query(Assessment).filter(Assessment.apprentice_id == current_user.id, Assessment.category == "spiritual_gifts")
    if cursor:
        ts, aid = _decode_cursor(cursor)
        # created_at descending; fetch records strictly older than cursor tuple
        base_query = base_query.filter(
            (Assessment.created_at < ts) | ((Assessment.created_at == ts) & (Assessment.id < aid))
        )
    rows = (
        base_query.order_by(Assessment.created_at.desc(), Assessment.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    rows = rows[:limit]
    for a in rows:
        log_assessment_view(current_user.id, a.id, "spiritual_gifts", current_user.role.value, current_user.id)
    next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
    return HistoryPage(results=[_serialize_scores(a) for a in rows], next_cursor=next_cursor)


# ---- Mentor access endpoints ----
@router.get("/{apprentice_id}/latest", response_model=SpiritualGiftsResult, summary="Mentor: latest spiritual gifts for an assigned apprentice")
def mentor_latest_spiritual_gifts(apprentice_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Authorization: current_user must be mentor and linked to apprentice
    if current_user.role != UserRole.mentor:
        raise HTTPException(status_code=403, detail="Only mentors can access apprentice reports via this endpoint")
    link = (
        db.query(MentorApprentice)
        .filter(MentorApprentice.mentor_id == current_user.id, MentorApprentice.apprentice_id == apprentice_id, MentorApprentice.active == True)
        .first()
    )
    if not link:
        raise HTTPException(status_code=403, detail="Mentor is not assigned to this apprentice")
    assessment = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == apprentice_id, Assessment.category == "spiritual_gifts")
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="No spiritual gifts assessment found for apprentice")
    log_assessment_view(current_user.id, assessment.id, "spiritual_gifts", current_user.role.value, apprentice_id)
    return _serialize_scores(assessment)

@router.get("/{apprentice_id}/history", response_model=HistoryPage, summary="Mentor: history of spiritual gifts assessments for an assigned apprentice")
def mentor_history_spiritual_gifts(apprentice_id: str, limit: int = 20, cursor: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.mentor:
        raise HTTPException(status_code=403, detail="Only mentors can access apprentice reports via this endpoint")
    link = (
        db.query(MentorApprentice)
        .filter(MentorApprentice.mentor_id == current_user.id, MentorApprentice.apprentice_id == apprentice_id, MentorApprentice.active == True)
        .first()
    )
    if not link:
        raise HTTPException(status_code=403, detail="Mentor is not assigned to this apprentice")
    if limit <= 0 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    base_query = db.query(Assessment).filter(Assessment.apprentice_id == apprentice_id, Assessment.category == "spiritual_gifts")
    if cursor:
        ts, aid = _decode_cursor(cursor)
        base_query = base_query.filter(
            (Assessment.created_at < ts) | ((Assessment.created_at == ts) & (Assessment.id < aid))
        )
    rows = (
        base_query.order_by(Assessment.created_at.desc(), Assessment.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    rows = rows[:limit]
    for a in rows:
        log_assessment_view(current_user.id, a.id, "spiritual_gifts", current_user.role.value, apprentice_id)
    next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
    return HistoryPage(results=[_serialize_scores(a) for a in rows], next_cursor=next_cursor)


@router.post("/email-report", response_model=EmailReportResponse, summary="Email Spiritual Gifts report (apprentice self-service)")
def email_spiritual_gifts_report(body: EmailReportRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.apprentice:
        raise HTTPException(status_code=403, detail="Only apprentices can email their spiritual gifts report")
    # DB-backed rate limit
    remaining = _enforce_email_rate_limit(db, current_user.id)
    # Enforce self-email only
    if body.to_email.lower() != current_user.email.lower():
        raise HTTPException(status_code=400, detail="to_email must match authenticated user email")
    # Find assessment
    query = db.query(Assessment).filter(Assessment.apprentice_id == current_user.id, Assessment.category == "spiritual_gifts")
    if body.assessment_id:
        query = query.filter(Assessment.id == body.assessment_id)
    assessment = query.order_by(Assessment.created_at.desc()).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    scores = assessment.scores or {}
    template_version = scores.get("template_version") or scores.get("version", 1)
    # gather definitions (all for requested version)
    defs_rows = db.query(SpiritualGiftDefinition).filter(SpiritualGiftDefinition.version == template_version).all()
    defs_map = {r.gift_slug: {
        "display_name": r.display_name,
        "full_definition": r.full_definition,
        "short_summary": r.short_summary,
    } for r in defs_rows}
    pdf_data = b""
    html_report = ""
    if body.include_pdf:
        pdf_data = generate_pdf(getattr(current_user, 'name', None), template_version, scores, defs_map)
    if body.include_html:
        html_report = generate_html(getattr(current_user, 'name', None), template_version, scores, defs_map)
    # Build email content
    today = datetime.utcnow().strftime('%Y-%m-%d')
    subj_name = getattr(current_user, 'name', 'Apprentice')
    subject = f"Spiritual Gifts Report — {subj_name} — {today}"
    inline_html = html_report or generate_html(getattr(current_user, 'name', None), template_version, scores, defs_map)
    plain_fallback = "Spiritual Gifts Report\nTop Gifts:\n" + "\n".join([f"- {g['gift']}: {g['score']}" for g in scores.get('top_gifts_truncated', [])])
    attachments = None
    if body.include_pdf and pdf_data:
        safe_name = subj_name.lower().replace(' ', '_')
        attachments = [{
            "filename": f"spiritual_gifts_report_{safe_name}_{today.replace('-', '')}.pdf",
            "mime_type": "application/pdf",
            "data": pdf_data,
        }]
    sent = send_email(body.to_email, subject, inline_html, plain_fallback, attachments=attachments)
    # Persist email send event (attempt logged regardless of success to prevent brute-force retries bypass)
    event = EmailSendEvent(
        sender_user_id=current_user.id,
        target_user_id=current_user.id,
        assessment_id=assessment.id,
        category="spiritual_gifts",
        template_version=template_version,
        role_context=current_user.role.value,
        purpose="report",
    )
    db.add(event)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # We don't fail the endpoint if logging the event fails; continue.
    log_assessment_view(current_user.id, assessment.id, "spiritual_gifts", current_user.role.value, current_user.id)
    log_email_send(current_user.id, assessment.id, "spiritual_gifts", template_version, current_user.id, "report", current_user.role.value, bool(sent))
    return EmailReportResponse(
        sent=bool(sent),
        assessment_id=assessment.id,
        template_version=template_version,
        pdf_bytes=len(pdf_data) if pdf_data else None,
        html_bytes=len(inline_html.encode()) if inline_html else None,
    )


@router.post("/{apprentice_id}/email-report", response_model=EmailReportResponse, summary="Mentor/Admin: email an apprentice's Spiritual Gifts report")
def mentor_admin_email_spiritual_gifts_report(apprentice_id: str, body: EmailReportRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Authorization: mentor with relationship OR admin
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
        raise HTTPException(status_code=403, detail="Only mentors or admins can send an apprentice's report")

    # Rate limit per sender
    remaining = _enforce_email_rate_limit(db, current_user.id)

    query = db.query(Assessment).filter(Assessment.apprentice_id == apprentice_id, Assessment.category == "spiritual_gifts")
    if body.assessment_id:
        query = query.filter(Assessment.id == body.assessment_id)
    assessment = query.order_by(Assessment.created_at.desc()).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    scores = assessment.scores or {}
    template_version = scores.get("template_version") or scores.get("version", 1)
    defs_rows = db.query(SpiritualGiftDefinition).filter(SpiritualGiftDefinition.version == template_version).all()
    defs_map = {r.gift_slug: {
        "display_name": r.display_name,
        "full_definition": r.full_definition,
        "short_summary": r.short_summary,
    } for r in defs_rows}

    pdf_data = b""
    html_report = ""
    if body.include_pdf:
        pdf_data = generate_pdf(None, template_version, scores, defs_map)
    if body.include_html:
        html_report = generate_html(None, template_version, scores, defs_map)

    # Fetch apprentice user for display name
    apprentice_user = db.query(User).filter(User.id == apprentice_id).first()
    apprentice_name = apprentice_user.name if apprentice_user else 'Apprentice'
    today = datetime.utcnow().strftime('%Y-%m-%d')
    subject = f"Spiritual Gifts Report — {apprentice_name} — {today}"
    inline_html = html_report or generate_html(None, template_version, scores, defs_map)
    plain_fallback = "Spiritual Gifts Report\nTop Gifts:\n" + "\n".join([f"- {g['gift']}: {g['score']}" for g in scores.get('top_gifts_truncated', [])])
    attachments = None
    if body.include_pdf and pdf_data:
        safe_name = apprentice_name.lower().replace(' ', '_')
        attachments = [{
            "filename": f"spiritual_gifts_report_{safe_name}_{today.replace('-', '')}.pdf",
            "mime_type": "application/pdf",
            "data": pdf_data,
        }]
    sent = send_email(body.to_email, subject, inline_html, plain_fallback, attachments=attachments)

    event = EmailSendEvent(
        sender_user_id=current_user.id,
        target_user_id=apprentice_id,
        assessment_id=assessment.id,
        category="spiritual_gifts",
        template_version=template_version,
        role_context=current_user.role.value,
        purpose="report",
    )
    db.add(event)
    try:
        db.commit()
    except Exception:
        db.rollback()
    log_assessment_view(current_user.id, assessment.id, "spiritual_gifts", current_user.role.value, apprentice_id)
    log_email_send(current_user.id, assessment.id, "spiritual_gifts", template_version, apprentice_id, "report", current_user.role.value, bool(sent))
    return EmailReportResponse(
        sent=bool(sent),
        assessment_id=assessment.id,
        template_version=template_version,
        pdf_bytes=len(pdf_data) if pdf_data else None,
        html_bytes=len(inline_html.encode()) if inline_html else None,
    )


@router.get("/template/metadata", summary="Public: active spiritual gifts template metadata")
def public_spiritual_gifts_template_metadata(db: Session = Depends(get_db)):
    tpl = _get_active_template(db)
    if not tpl:
        raise HTTPException(status_code=404, detail="No published template")
    return {
        "template_id": tpl.id,
        "version": tpl.version,
        "published_at": tpl.created_at,
        "name": tpl.name,
    }
