from __future__ import annotations
import logging
from enum import Enum
from typing import Any, Dict, Tuple
from datetime import datetime, UTC
from app.utils.datetime import utc_now

from app.core.settings import settings
from app.services.email import get_email_template_env, send_email

logger = logging.getLogger("app.agreement_email")

class AgreementEmailEvent(str, Enum):
    APPRENTICE_INVITE = "apprentice_invite"
    PARENT_INVITE = "parent_invite"
    PARENT_RESEND = "parent_resend"
    PARENT_RESEND_REQUEST = "parent_resend_request"
    RESCHEDULE_REQUEST = "reschedule_request"
    RESCHEDULE_RESPONSE = "reschedule_response"
    FULLY_SIGNED = "fully_signed"
    REVOKED = "revoked"

SUBJECTS: Dict[AgreementEmailEvent, str] = {
    AgreementEmailEvent.APPRENTICE_INVITE: "Mentorship Agreement: Please Review and Sign",
    AgreementEmailEvent.PARENT_INVITE: "Parent Signature Requested: Mentorship Agreement",
    AgreementEmailEvent.PARENT_RESEND: "Reminder: Parent Signature Needed",
    AgreementEmailEvent.PARENT_RESEND_REQUEST: "Apprentice requested parent signature resend",
    AgreementEmailEvent.RESCHEDULE_REQUEST: "Meeting reschedule requested",
    AgreementEmailEvent.RESCHEDULE_RESPONSE: "Mentor responded to reschedule request",
    AgreementEmailEvent.FULLY_SIGNED: "Mentorship Agreement Fully Signed",
    AgreementEmailEvent.REVOKED: "Mentorship Agreement Revoked",
}

TEMPLATE_MAP: Dict[AgreementEmailEvent, str] = {
    AgreementEmailEvent.APPRENTICE_INVITE: "agreements/apprentice_invite.html",
    AgreementEmailEvent.PARENT_INVITE: "agreements/parent_invite.html",
    AgreementEmailEvent.PARENT_RESEND: "agreements/parent_resend.html",
    AgreementEmailEvent.PARENT_RESEND_REQUEST: "agreements/parent_resend_request.html",
    AgreementEmailEvent.RESCHEDULE_REQUEST: "agreements/reschedule_request.html",
    AgreementEmailEvent.RESCHEDULE_RESPONSE: "agreements/reschedule_response.html",
    AgreementEmailEvent.FULLY_SIGNED: "agreements/fully_signed.html",
    AgreementEmailEvent.REVOKED: "agreements/revoked.html",
}

def _logo_url(context: Dict[str, Any]) -> str:
    return settings.logo_url

def render_agreement_email(event: AgreementEmailEvent, context: Dict[str, Any]) -> Tuple[str, str, str]:
    """Render HTML & plain text plus subject for an agreement lifecycle event."""
    subject = SUBJECTS[event]
    env = get_email_template_env()
    # Use backend_api_url for agreement signing pages (these are backend HTML pages, not mobile app links)
    ctx = {**context, 'event': event.value, 'subject': subject, 'app_url': settings.backend_api_url, 'logo_url': _logo_url(context)}

    html = None
    if env:
        template_name = TEMPLATE_MAP.get(event)
        try:
            template = env.get_template(template_name)
            html = template.render(**ctx)
        except Exception as e:
            logger.error(f"[agreement_email] Failed to render template {template_name}: {e}")

    if not html:
        # Fallback minimal HTML
        html_lines = [f"<h3>{subject}</h3>", f"<p>Agreement ID: {context.get('agreement_id')}</p>"]
        if event == AgreementEmailEvent.APPRENTICE_INVITE:
            html_lines.append("<p>You have been invited to review and sign a mentorship agreement.</p>")
        elif event == AgreementEmailEvent.PARENT_INVITE:
            html_lines.append("<p>A parent/guardian signature is requested for a mentorship agreement.</p>")
        elif event == AgreementEmailEvent.PARENT_RESEND:
            html_lines.append("<p>This is a reminder to review and sign the mentorship agreement.</p>")
        elif event == AgreementEmailEvent.PARENT_RESEND_REQUEST:
            html_lines.append("<p>The apprentice has requested that you resend the parent/guardian signature link.</p>")
            if context.get('parent_email'):
                html_lines.append(f"<p>Parent Email on file: {context.get('parent_email')}</p>")
        elif event == AgreementEmailEvent.FULLY_SIGNED:
            html_lines.append("<p>The mentorship agreement is now fully signed and active.</p>")
        elif event == AgreementEmailEvent.REVOKED:
            html_lines.append("<p>The mentorship agreement has been revoked.</p>")
        elif event == AgreementEmailEvent.RESCHEDULE_REQUEST:
            html_lines.append("<p>The apprentice has requested to reschedule the meeting.</p>")
            reason = context.get('reason')
            if reason:
                html_lines.append(f"<p><strong>Reason:</strong> {reason}</p>")
            proposals = context.get('proposals') or []
            if proposals:
                items = ''.join(f"<li>{p}</li>" for p in proposals)
                html_lines.append(f"<p><strong>Proposed Times:</strong><ul>{items}</ul></p>")
        elif event == AgreementEmailEvent.RESCHEDULE_RESPONSE:
            html_lines.append("<p>The mentor responded to your reschedule request.</p>")
            decision = context.get('decision')
            if decision:
                html_lines.append(f"<p><strong>Decision:</strong> {decision}</p>")
            selected_time = context.get('selected_time')
            if selected_time:
                html_lines.append(f"<p><strong>Selected time:</strong> {selected_time}</p>")
            note = context.get('note')
            if note:
                html_lines.append(f"<p><strong>Note:</strong> {note}</p>")
        action_url = context.get('action_url')
        if action_url:
            html_lines.append(f"<p><a href='{action_url}'>Open Agreement</a></p>")
        html = "\n".join(html_lines)

    # Plain text
    plain_lines = [subject, f"Agreement ID: {context.get('agreement_id')}"]
    action_url = context.get('action_url')
    if action_url:
        plain_lines.append(f"Link: {action_url}")
    plain = "\n".join(plain_lines)
    return html, plain, subject

def send_agreement_email(event: AgreementEmailEvent, to_email: str, context: Dict[str, Any]) -> bool:
    html, plain, subject = render_agreement_email(event, context)
    start = utc_now()
    success = False
    try:
        success = send_email(to_email, subject, html, plain)
        return success
    finally:
        duration_ms = int((utc_now() - start).total_seconds() * 1000)
        log_record = {
            'component': 'agreement_email',
            'event': event.value,
            'to': to_email,
            'agreement_id': context.get('agreement_id'),
            'success': success,
            'duration_ms': duration_ms,
        }
        logger.info(f"AGREEMENT_EMAIL_METRIC {log_record}")
