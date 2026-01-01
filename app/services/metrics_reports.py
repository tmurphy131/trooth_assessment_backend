"""
Metrics report scheduler and email sender for T[root]H Discipleship.
Handles sending weekly and monthly email reports.
"""

import logging
import os
from datetime import datetime
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.email import send_email
from app.services.metrics import get_all_metrics
from app.core.settings import settings
from app.db import SessionLocal

logger = logging.getLogger("app.metrics_reports")

# Admin email(s) to receive reports - comma-separated in env var
REPORT_RECIPIENTS = os.getenv("METRICS_REPORT_RECIPIENTS", "admin@trooth-app.com")


def get_report_recipients() -> list[str]:
    """Parse report recipients from environment variable."""
    recipients_str = os.getenv("METRICS_REPORT_RECIPIENTS", "")
    if not recipients_str:
        logger.warning("No METRICS_REPORT_RECIPIENTS configured")
        return []
    return [email.strip() for email in recipients_str.split(",") if email.strip()]


def render_metrics_email(metrics: dict, report_type: str) -> tuple[str, str]:
    """Render the metrics report email using Jinja2 template.
    
    Args:
        metrics: Full metrics dict from get_all_metrics()
        report_type: "Weekly" or "Monthly"
    
    Returns:
        (html_content, plain_text)
    """
    template_dir = os.path.join(os.path.dirname(__file__), '../templates/email')
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    period_label = "Week" if report_type == "Weekly" else "Month"
    report_date = datetime.utcnow().strftime("%B %d, %Y")
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    context = {
        "report_type": report_type,
        "report_date": report_date,
        "generated_at": generated_at,
        "period_label": period_label,
        **metrics  # Spread users, assessments, mentorship, etc.
    }
    
    try:
        template = env.get_template('metrics_report.html')
        html_content = template.render(**context)
    except Exception as e:
        logger.error(f"Failed to render metrics email template: {e}")
        html_content = _fallback_html(metrics, report_type, report_date)
    
    # Plain text version
    plain_text = _generate_plain_text(metrics, report_type, report_date)
    
    return html_content, plain_text


def _fallback_html(metrics: dict, report_type: str, report_date: str) -> str:
    """Fallback HTML if template rendering fails."""
    users = metrics.get("users", {})
    assessments = metrics.get("assessments", {})
    mentorship = metrics.get("mentorship", {})
    
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #1a1a1a; color: #f5f5f5; padding: 20px;">
        <h1 style="color: #d4af37;">T[root]H Discipleship - {report_type} Report</h1>
        <p style="color: #888;">{report_date}</p>
        <h2>Users</h2>
        <p>Total: {users.get('total_users', 0)} | Mentors: {users.get('mentors', 0)} | Apprentices: {users.get('apprentices', 0)}</p>
        <h2>Assessments</h2>
        <p>Completed: {assessments.get('total_completed', 0)} | This Period: {assessments.get('completed_in_period', 0)}</p>
        <h2>Mentorship</h2>
        <p>Active Pairs: {mentorship.get('active_relationships', 0)}</p>
        <hr>
        <p style="color: #d4af37;">#getrooted #LUKE850</p>
    </body>
    </html>
    """


def _generate_plain_text(metrics: dict, report_type: str, report_date: str) -> str:
    """Generate plain text version of the report."""
    users = metrics.get("users", {})
    assessments = metrics.get("assessments", {})
    mentorship = metrics.get("mentorship", {})
    invitations = metrics.get("invitations", {})
    agreements = metrics.get("agreements", {})
    mentor_activity = metrics.get("mentor_activity", {})
    
    lines = [
        f"T[root]H Discipleship - {report_type} Metrics Report",
        f"Generated: {report_date}",
        "",
        "=" * 40,
        "KEY METRICS",
        "=" * 40,
        f"Total Users: {users.get('total_users', 0)}",
        f"  - Mentors: {users.get('mentors', 0)}",
        f"  - Apprentices: {users.get('apprentices', 0)}",
        f"  - New this period: +{users.get('new_users_in_period', 0)}",
        "",
        "ASSESSMENTS",
        "-" * 20,
        f"Total Completed: {assessments.get('total_completed', 0)}",
        f"Completed this period: {assessments.get('completed_in_period', 0)}",
        f"Drafts in progress: {assessments.get('active_drafts', 0)}",
        f"Completion Rate: {assessments.get('completion_rate', 0)}%",
        "",
        "MENTORSHIP",
        "-" * 20,
        f"Active Pairs: {mentorship.get('active_relationships', 0)}",
        f"Mentor Utilization: {mentorship.get('mentor_utilization_percent', 0)}%",
        "",
        "INVITATIONS",
        "-" * 20,
        f"Sent: {invitations.get('total_invitations', 0)}",
        f"Accepted: {invitations.get('accepted', 0)} ({invitations.get('acceptance_rate', 0)}%)",
        f"Pending: {invitations.get('pending', 0)}",
        "",
        "AGREEMENTS",
        "-" * 20,
        f"Fully Signed: {agreements.get('fully_signed', 0)}",
        f"Awaiting Action: {agreements.get('awaiting_apprentice', 0) + agreements.get('awaiting_parent', 0)}",
        "",
        "MENTOR ACTIVITY",
        "-" * 20,
        f"Notes Added: {mentor_activity.get('notes_in_period', 0)}",
        f"Active Mentors: {mentor_activity.get('active_mentors', 0)}",
        "",
        "=" * 40,
        "#getrooted #LUKE850",
        "ONLY BLV - T[root]H Discipleship",
    ]
    
    return "\n".join(lines)


def send_weekly_report() -> bool:
    """Generate and send weekly metrics report."""
    logger.info("Generating weekly metrics report")
    
    recipients = get_report_recipients()
    if not recipients:
        logger.warning("No recipients configured for weekly report")
        return False
    
    try:
        db = SessionLocal()
        metrics = get_all_metrics(db, period="week")
        db.close()
        
        html_content, plain_text = render_metrics_email(metrics, "Weekly")
        subject = f"T[root]H Weekly Report - {datetime.utcnow().strftime('%b %d, %Y')}"
        
        success_count = 0
        for recipient in recipients:
            try:
                if send_email(recipient, subject, html_content, plain_text):
                    success_count += 1
                    logger.info(f"Weekly report sent to {recipient}")
                else:
                    logger.error(f"Failed to send weekly report to {recipient}")
            except Exception as e:
                logger.error(f"Error sending to {recipient}: {e}")
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")
        return False


def send_monthly_report() -> bool:
    """Generate and send monthly metrics report."""
    logger.info("Generating monthly metrics report")
    
    recipients = get_report_recipients()
    if not recipients:
        logger.warning("No recipients configured for monthly report")
        return False
    
    try:
        db = SessionLocal()
        metrics = get_all_metrics(db, period="month")
        db.close()
        
        html_content, plain_text = render_metrics_email(metrics, "Monthly")
        subject = f"T[root]H Monthly Report - {datetime.utcnow().strftime('%B %Y')}"
        
        success_count = 0
        for recipient in recipients:
            try:
                if send_email(recipient, subject, html_content, plain_text):
                    success_count += 1
                    logger.info(f"Monthly report sent to {recipient}")
                else:
                    logger.error(f"Failed to send monthly report to {recipient}")
            except Exception as e:
                logger.error(f"Error sending to {recipient}: {e}")
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Failed to generate monthly report: {e}")
        return False


def send_report_now(report_type: str = "weekly", recipient_override: Optional[str] = None) -> bool:
    """
    Send a report immediately (for testing or manual trigger).
    
    Args:
        report_type: "weekly" or "monthly"
        recipient_override: If provided, send only to this email instead of configured recipients
    """
    logger.info(f"Sending {report_type} report now (manual trigger)")
    
    period = "week" if report_type == "weekly" else "month"
    report_label = "Weekly" if report_type == "weekly" else "Monthly"
    
    recipients = [recipient_override] if recipient_override else get_report_recipients()
    if not recipients:
        logger.warning("No recipients for manual report send")
        return False
    
    try:
        db = SessionLocal()
        metrics = get_all_metrics(db, period=period)
        db.close()
        
        html_content, plain_text = render_metrics_email(metrics, report_label)
        subject = f"T[root]H {report_label} Report - {datetime.utcnow().strftime('%b %d, %Y')}"
        
        success = False
        for recipient in recipients:
            try:
                if send_email(recipient, subject, html_content, plain_text):
                    logger.info(f"Report sent to {recipient}")
                    success = True
            except Exception as e:
                logger.error(f"Error sending to {recipient}: {e}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send manual report: {e}")
        return False
