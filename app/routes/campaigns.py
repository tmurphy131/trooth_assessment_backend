"""Campaign endpoints for Cloud Scheduler.

Secured with X-Cron-Secret header (same pattern as scheduled_tasks.py).
Schedule these in Google Cloud Scheduler pointing at:
  POST /campaigns/run-draft-reminders   — daily at 7 PM UTC
  POST /campaigns/run-inactive-reminders — daily at 8 AM UTC
  GET  /campaigns/stats                 — for manual analytics review
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.assessment_draft import AssessmentDraft
from app.models.assessment_template import AssessmentTemplate
from app.models.email_send_event import EmailSendEvent
from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User, UserRole
from app.services.email import (
    _already_sent_campaign,
    send_draft_reminder_email,
    send_inactive_reengagement_email,
    send_new_template_email,
)
from app.services.push_notification import (
    notify_draft_reminder_push,
    notify_new_template_push,
)

logger = logging.getLogger(__name__)
router = APIRouter()

CRON_SECRET = os.getenv("CRON_SECRET", "dev-cron-secret-change-in-prod")


def verify_cron_secret(x_cron_secret: Optional[str] = Header(None)):
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")
    return True


# ---------------------------------------------------------------------------
# Draft reminder campaign
# ---------------------------------------------------------------------------

@router.post("/run-draft-reminders")
def run_draft_reminders(
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_cron_secret),
):
    """Send email + push reminders for stale assessment drafts (5/10/14 days).

    Safe to run daily — dedup logic prevents duplicate sends within 3 days
    per draft.
    """
    now = datetime.utcnow()
    reminder_days = [5, 10, 14]
    results = {"reminder_days": {}}

    for days in reminder_days:
        window_start = now - timedelta(days=days + 1)
        window_end = now - timedelta(days=days - 1)

        drafts = (
            db.query(AssessmentDraft)
            .filter(
                AssessmentDraft.is_submitted == False,  # noqa: E712
                AssessmentDraft.updated_at >= window_start,
                AssessmentDraft.updated_at < window_end,
            )
            .all()
        )

        sent_email = 0
        sent_push = 0
        skipped = 0

        for draft in drafts:
            user = db.query(User).filter(User.id == draft.apprentice_id).first()
            if not user:
                continue

            # Skip if we already sent a reminder for this draft recently
            if _already_sent_campaign(db, user.id, "draft_reminder", "draft_id", draft.id, within_days=4):
                skipped += 1
                continue

            # Resolve mentor name
            mentor_name = "your mentor"
            ma = db.query(MentorApprentice).filter(
                MentorApprentice.apprentice_id == user.id,
                MentorApprentice.active == True,  # noqa: E712
            ).first()
            if ma:
                mentor = db.query(User).filter(User.id == ma.mentor_id).first()
                if mentor:
                    mentor_name = mentor.name

            if send_draft_reminder_email(db, user, draft, mentor_name, days):
                sent_email += 1

            if user.push_enabled:
                answers = draft.answers or {}
                answered = len(answers) if isinstance(answers, dict) else 0
                total = len(draft.template.questions) if hasattr(draft, 'template') and draft.template else 0
                pct = int((answered / total) * 100) if total else 0
                result = notify_draft_reminder_push(db, user.id, draft.id, pct, days)
                if result.get("success_count", 0) > 0:
                    sent_push += 1

        results["reminder_days"][days] = {
            "drafts_found": len(drafts),
            "emails_sent": sent_email,
            "pushes_sent": sent_push,
            "skipped_dedup": skipped,
        }
        logger.info(f"[campaigns] Draft reminders day={days}: {sent_email} emails, {sent_push} pushes, {skipped} skipped")

    return {"status": "ok", "results": results}


# ---------------------------------------------------------------------------
# Inactive user re-engagement campaign
# ---------------------------------------------------------------------------

@router.post("/run-inactive-reminders")
def run_inactive_reminders(
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_cron_secret),
):
    """Send re-engagement emails to inactive users (14/30/60 day windows).

    Skips users who already received an inactive email within 20 days.
    """
    now = datetime.utcnow()
    windows = [
        {"days": 14, "role": UserRole.apprentice},
        {"days": 30, "role": UserRole.apprentice},
        {"days": 30, "role": UserRole.mentor},
        {"days": 60, "role": UserRole.apprentice},
        {"days": 60, "role": UserRole.mentor},
    ]

    results = []

    for window in windows:
        days = window["days"]
        role = window["role"]
        cutoff_start = now - timedelta(days=days + 5)
        cutoff_end = now - timedelta(days=days - 1)

        users = (
            db.query(User)
            .filter(
                User.role == role,
                User.last_activity_at >= cutoff_start,
                User.last_activity_at < cutoff_end,
            )
            .all()
        )

        sent = 0
        skipped = 0

        for user in users:
            if _already_sent_campaign(db, user.id, "inactive_reengagement", "is_mentor",
                                       str(role == UserRole.mentor), within_days=20):
                skipped += 1
                continue

            last_activity = user.last_activity_at or user.created_at
            days_inactive = (now - last_activity).days if last_activity else days

            assessment_count = user.assessment_count or 0
            apprentice_names = None

            if role == UserRole.mentor:
                rels = db.query(MentorApprentice).filter(
                    MentorApprentice.mentor_id == user.id,
                    MentorApprentice.active == True,  # noqa: E712
                ).all()
                if rels:
                    apprentice_users = db.query(User).filter(
                        User.id.in_([r.apprentice_id for r in rels])
                    ).all()
                    apprentice_names = [u.name for u in apprentice_users]

            if send_inactive_reengagement_email(
                db, user, days_inactive,
                assessment_count=assessment_count,
                apprentice_names=apprentice_names,
            ):
                sent += 1

        results.append({
            "days": days,
            "role": role.value,
            "users_found": len(users),
            "emails_sent": sent,
            "skipped_dedup": skipped,
        })
        logger.info(f"[campaigns] Inactive reminders day={days} role={role.value}: {sent} sent, {skipped} skipped")

    return {"status": "ok", "results": results}


# ---------------------------------------------------------------------------
# New template notification (called from admin template creation endpoint)
# ---------------------------------------------------------------------------

def notify_new_template_to_all_apprentices(db: Session, template: AssessmentTemplate) -> dict:
    """Send email + push to all apprentices for a newly published template.

    Called as a background task from the admin template creation route.
    """
    apprentices = db.query(User).filter(User.role == UserRole.apprentice).all()

    sent_email = 0
    sent_push = 0

    for user in apprentices:
        if _already_sent_campaign(db, user.id, "new_template", "template_id", template.id, within_days=365):
            continue

        if send_new_template_email(db, user, template):
            sent_email += 1

        if user.push_enabled:
            result = notify_new_template_push(db, user.id, template.name, template.id)
            if result.get("success_count", 0) > 0:
                sent_push += 1

    logger.info(f"[campaigns] New template '{template.name}': {sent_email} emails, {sent_push} pushes to {len(apprentices)} apprentices")
    return {"emails_sent": sent_email, "pushes_sent": sent_push, "total_apprentices": len(apprentices)}


# ---------------------------------------------------------------------------
# Campaign analytics
# ---------------------------------------------------------------------------

@router.get("/stats")
def campaign_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_cron_secret),
):
    """Return campaign send counts grouped by type for the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            EmailSendEvent.campaign_type,
            func.count(EmailSendEvent.id).label("count"),
        )
        .filter(
            EmailSendEvent.campaign_type.isnot(None),
            EmailSendEvent.created_at >= cutoff,
        )
        .group_by(EmailSendEvent.campaign_type)
        .all()
    )

    stats = {row.campaign_type: row.count for row in rows}
    return {"period_days": days, "campaigns": stats}
