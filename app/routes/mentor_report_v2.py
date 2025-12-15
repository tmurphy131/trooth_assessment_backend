from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.auth import verify_token
from app.models import assessment as assessment_model, user as user_model, mentor_apprentice as mentor_model
from app.services.master_trooth_report import build_report_context, render_email_v2, render_pdf_v2
from app.services.email import send_email
from datetime import datetime, UTC
import json

router = APIRouter()


@router.get("/assessments/{assessment_id}/mentor-report-v2", response_class=Response)
def get_mentor_report_v2(
    assessment_id: str,
    db: Session = Depends(get_db),
    decoded_token=Depends(verify_token)
):
    """Render the mentor report v2 as HTML for preview. Returns HTML.

    Authorization: apprentice who owns the assessment or their mentor.
    """
    user_id = decoded_token["uid"]
    a = db.query(assessment_model.Assessment).filter_by(id=assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Check permissions
    is_apprentice = (user_id == a.apprentice_id)
    mentor_rel = db.query(mentor_model.MentorApprentice).filter_by(mentor_id=user_id, apprentice_id=a.apprentice_id).first()
    if not (is_apprentice or mentor_rel):
        raise HTTPException(status_code=403, detail="Not allowed")

    mentor_blob = a.mentor_report_v2 or {}
    scores = a.scores or {}
    # Build minimal assessment dict for context
    apprentice = db.query(user_model.User).filter_by(id=a.apprentice_id).first()
    assessment_ctx = {
        'apprentice': {'id': a.apprentice_id, 'name': getattr(apprentice, 'name', None) or getattr(apprentice, 'email', 'Apprentice')},
        'template_id': a.template_id,
        'created_at': getattr(a, 'created_at', None),
    }
    context = build_report_context(assessment_ctx, scores, mentor_blob)
    html = render_email_v2(context)
    return Response(content=html, media_type="text/html")


@router.get("/assessments/{assessment_id}/mentor-report-v2.pdf")
def get_mentor_report_v2_pdf(
    assessment_id: str,
    db: Session = Depends(get_db),
    decoded_token=Depends(verify_token)
):
    """Generate and return the mentor report v2 as a PDF file."""
    user_id = decoded_token["uid"]
    a = db.query(assessment_model.Assessment).filter_by(id=assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    is_apprentice = (user_id == a.apprentice_id)
    mentor_rel = db.query(mentor_model.MentorApprentice).filter_by(mentor_id=user_id, apprentice_id=a.apprentice_id).first()
    if not (is_apprentice or mentor_rel):
        raise HTTPException(status_code=403, detail="Not allowed")

    mentor_blob = a.mentor_report_v2 or {}
    scores = a.scores or {}
    apprentice = db.query(user_model.User).filter_by(id=a.apprentice_id).first()
    apprentice_name = getattr(apprentice, 'name', None) or getattr(apprentice, 'email', 'Apprentice')
    assessment_ctx = {
        'apprentice': {'id': a.apprentice_id, 'name': apprentice_name},
        'template_id': a.template_id,
        'created_at': getattr(a, 'created_at', None),
    }
    context = build_report_context(assessment_ctx, scores, mentor_blob)
    pdf_bytes = render_pdf_v2(context)
    
    # Add content-disposition header for better download handling
    safe_name = apprentice_name.lower().replace(' ', '_')
    filename = f"mentor_report_{safe_name}_{assessment_id[:8]}.pdf"
    
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(pdf_bytes))
        }
    )


@router.post("/assessments/{assessment_id}/email-report")
def email_report_by_assessment(
    assessment_id: str,
    body: dict,
    db: Session = Depends(get_db),
    decoded_token=Depends(verify_token)
):
    """Email the mentor report (v2 if available) for a specific assessment ID.

    Authorization: apprentice owner or their mentor. Body: { to_email, include_pdf }
    """
    user_id = decoded_token["uid"]
    a = db.query(assessment_model.Assessment).filter_by(id=assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    is_apprentice = (user_id == a.apprentice_id)
    mentor_rel = db.query(mentor_model.MentorApprentice).filter_by(mentor_id=user_id, apprentice_id=a.apprentice_id).first()
    if not (is_apprentice or mentor_rel):
        raise HTTPException(status_code=403, detail="Not allowed")
    apprentice = db.query(user_model.User).filter_by(id=a.apprentice_id).first()
    apprentice_name = getattr(apprentice, 'name', None) or getattr(apprentice, 'email', 'Apprentice')
    to_email = (body.get("to_email") or "").strip()
    include_pdf = bool(body.get("include_pdf"))
    if not to_email:
        raise HTTPException(status_code=400, detail="to_email is required")
    mentor_blob = a.mentor_report_v2 or {}
    scores = a.scores or {}
    assessment_ctx = {
        'apprentice': {'id': a.apprentice_id, 'name': apprentice_name},
        'template_id': a.template_id,
        'created_at': getattr(a, 'created_at', None),
    }
    context = build_report_context(assessment_ctx, scores, mentor_blob)
    html = render_email_v2(context)
    plain = f"T[root]H Mentor Report\nApprentice: {apprentice_name}\nKnowledge: {context.get('overall_mc_percent')}% ({context.get('knowledge_band')})"
    attachments = None
    if include_pdf:
        pdf = render_pdf_v2(context)
        safe = apprentice_name.lower().replace(' ', '_')
        today = datetime.now(UTC).strftime('%Y%m%d')
        attachments = [{"filename": f"mentor_report_{safe}_{today}.pdf", "mime_type": "application/pdf", "data": pdf}]
    sent = send_email(to_email, f"Mentor Assessment Report — {apprentice_name} — {datetime.now(UTC).date()}", html, plain, attachments=attachments)
    return {"sent": bool(sent), "assessment_id": a.id}
