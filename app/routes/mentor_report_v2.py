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
    """Generate and return the mentor report v2 as a PDF file.
    
    Premium users get enhanced PDF with full report details.
    """
    user_id = decoded_token["uid"]
    a = db.query(assessment_model.Assessment).filter_by(id=assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    is_apprentice = (user_id == a.apprentice_id)
    mentor_rel = db.query(mentor_model.MentorApprentice).filter_by(mentor_id=user_id, apprentice_id=a.apprentice_id).first()
    if not (is_apprentice or mentor_rel):
        raise HTTPException(status_code=403, detail="Not allowed")

    # Get requesting user to check premium status
    requesting_user = db.query(user_model.User).filter_by(id=user_id).first()
    
    mentor_blob = a.mentor_report_v2 or {}
    scores = a.scores or {}
    apprentice = db.query(user_model.User).filter_by(id=a.apprentice_id).first()
    apprentice_name = getattr(apprentice, 'name', None) or getattr(apprentice, 'email', 'Apprentice')
    
    # Check if requesting user is premium
    from app.services.auth import is_premium_user
    import logging
    _logger = logging.getLogger(__name__)
    user_is_premium = is_premium_user(requesting_user) if requesting_user else False
    _logger.info(f"[export-pdf] user_id={user_id}, user_is_premium={user_is_premium}, subscription_tier={getattr(requesting_user, 'subscription_tier', None)}")
    
    # For premium users, ensure full_report is available
    if user_is_premium:
        cached_full_report = scores.get('full_report_v1')
        if not cached_full_report:
            try:
                from app.services.ai_scoring import generate_full_report_for_assessment
                cached_full_report = generate_full_report_for_assessment(a, apprentice_name, db)
                if cached_full_report:
                    updated_scores = dict(scores)
                    updated_scores['full_report_v1'] = cached_full_report
                    a.scores = updated_scores
                    scores = updated_scores
                    db.commit()
                    _logger.info("[export-pdf] on-demand full_report generated and cached")
            except Exception as e:
                _logger.warning(f"On-demand full report generation failed: {e}")
    
    assessment_ctx = {
        'apprentice': {'id': a.apprentice_id, 'name': apprentice_name},
        'template_id': a.template_id,
        'created_at': getattr(a, 'created_at', None),
    }
    context = build_report_context(assessment_ctx, scores, mentor_blob)
    
    # Ensure full_report is in context for premium PDF
    if user_is_premium and scores.get('full_report_v1'):
        context['full_report'] = scores.get('full_report_v1')
        _logger.info(f"[export-pdf] full_report added to context for premium PDF")
    
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
    
    Premium users receive an enhanced report with:
    - Deep dive analysis
    - Multi-session conversation guides  
    - Growth pathways
    """
    user_id = decoded_token["uid"]
    a = db.query(assessment_model.Assessment).filter_by(id=assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    is_apprentice = (user_id == a.apprentice_id)
    mentor_rel = db.query(mentor_model.MentorApprentice).filter_by(mentor_id=user_id, apprentice_id=a.apprentice_id).first()
    if not (is_apprentice or mentor_rel):
        raise HTTPException(status_code=403, detail="Not allowed")
    
    # Get requesting user to check premium status
    requesting_user = db.query(user_model.User).filter_by(id=user_id).first()
    
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
    
    # Check if requesting user is premium BEFORE building context
    from app.services.auth import is_premium_user
    user_is_premium = is_premium_user(requesting_user) if requesting_user else False
    
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info(f"[email-report] user_id={user_id}, user_is_premium={user_is_premium}, subscription_tier={getattr(requesting_user, 'subscription_tier', None)}")
    
    cached_full_report = None
    subject_prefix = ""
    
    if user_is_premium:
        # Check for cached full_report in scores (generated during assessment submission)
        cached_full_report = scores.get('full_report_v1')
        _logger.info(f"[email-report] cached_full_report exists: {cached_full_report is not None}")
        
        # If no cached report, generate on-demand for premium users
        if not cached_full_report:
            try:
                from app.services.ai_scoring import generate_full_report_for_assessment
                cached_full_report = generate_full_report_for_assessment(a, apprentice_name, db)
                _logger.info(f"[email-report] on-demand full_report generated: {cached_full_report is not None}")
                # Cache it for future use
                if cached_full_report:
                    updated_scores = dict(scores)
                    updated_scores['full_report_v1'] = cached_full_report
                    a.scores = updated_scores
                    scores = updated_scores  # Update local reference for context building
                    db.commit()
            except Exception as e:
                _logger.warning(f"On-demand full report generation failed: {e}")
    
    # Build context AFTER potentially updating scores with full_report
    context = build_report_context(assessment_ctx, scores, mentor_blob)
    
    # Ensure full_report is in context for PDF generation if available
    if cached_full_report and user_is_premium:
        context['full_report'] = cached_full_report
        _logger.info(f"[email-report] full_report added to context, keys: {list(cached_full_report.keys()) if isinstance(cached_full_report, dict) else 'not dict'}")
    
    if user_is_premium and cached_full_report:
        try:
            from app.services.email import render_premium_report_email
            html, plain = render_premium_report_email(context, cached_full_report)
            subject_prefix = "✦ PREMIUM "
            _logger.info("[email-report] using premium email template")
        except Exception as e:
            # Fallback to standard email if premium rendering fails
            _logger.warning(f"Premium email rendering failed, using standard: {e}")
            html = render_email_v2(context)
            plain = f"T[root]H Mentor Report\nApprentice: {apprentice_name}\nKnowledge: {context.get('overall_mc_percent')}% ({context.get('knowledge_band')})"
    else:
        html = render_email_v2(context)
        plain = f"T[root]H Mentor Report\nApprentice: {apprentice_name}\nKnowledge: {context.get('overall_mc_percent')}% ({context.get('knowledge_band')})"
        _logger.info(f"[email-report] using standard email template (premium={user_is_premium}, has_full_report={cached_full_report is not None})")
    
    attachments = None
    if include_pdf:
        pdf = render_pdf_v2(context)
        safe = apprentice_name.lower().replace(' ', '_')
        today = datetime.now(UTC).strftime('%Y%m%d')
        attachments = [{"filename": f"mentor_report_{safe}_{today}.pdf", "mime_type": "application/pdf", "data": pdf}]
        _logger.info(f"[email-report] PDF generated, full_report in context: {'full_report' in context}")
    sent = send_email(to_email, f"{subject_prefix}Mentor Assessment Report — {apprentice_name} — {datetime.now(UTC).date()}", html, plain, attachments=attachments)
    return {"sent": bool(sent), "assessment_id": a.id, "premium": user_is_premium}
