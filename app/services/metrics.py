"""
Metrics collection service for T[root]H Discipleship.
Collects various usage statistics for weekly/monthly reporting and real-time dashboard.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.user import User, UserRole
from app.models.assessment import Assessment
from app.models.assessment_draft import AssessmentDraft
from app.models.assessment_template import AssessmentTemplate
from app.models.agreement import Agreement
from app.models.apprentice_invitation import ApprenticeInvitation
from app.models.mentor_apprentice import MentorApprentice
from app.models.mentor_note import MentorNote

logger = logging.getLogger("app.metrics")


def get_date_range(period: str = "week") -> tuple[datetime, datetime]:
    """Get start and end date for the specified period."""
    now = datetime.now(UTC)
    if period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    elif period == "day":
        start = now - timedelta(days=1)
    else:
        start = now - timedelta(days=7)  # default to week
    return start, now


def get_user_metrics(db: Session, period: str = "all") -> Dict[str, Any]:
    """Get user registration and role distribution metrics."""
    start, end = get_date_range(period) if period != "all" else (None, None)
    
    # Total users by role
    total_users = db.query(User).count()
    mentors = db.query(User).filter(User.role == UserRole.mentor).count()
    apprentices = db.query(User).filter(User.role == UserRole.apprentice).count()
    admins = db.query(User).filter(User.role == UserRole.admin).count()
    
    # New users in period
    if start:
        new_users = db.query(User).filter(User.created_at >= start).count()
        new_mentors = db.query(User).filter(
            and_(User.created_at >= start, User.role == UserRole.mentor)
        ).count()
        new_apprentices = db.query(User).filter(
            and_(User.created_at >= start, User.role == UserRole.apprentice)
        ).count()
    else:
        new_users = total_users
        new_mentors = mentors
        new_apprentices = apprentices
    
    return {
        "total_users": total_users,
        "mentors": mentors,
        "apprentices": apprentices,
        "admins": admins,
        "new_users_in_period": new_users,
        "new_mentors_in_period": new_mentors,
        "new_apprentices_in_period": new_apprentices,
    }


def get_assessment_metrics(db: Session, period: str = "all") -> Dict[str, Any]:
    """Get assessment activity metrics."""
    start, end = get_date_range(period) if period != "all" else (None, None)
    
    # Total completed assessments
    total_completed = db.query(Assessment).filter(Assessment.status == "done").count()
    
    # In period
    if start:
        completed_in_period = db.query(Assessment).filter(
            and_(Assessment.created_at >= start, Assessment.status == "done")
        ).count()
        started_in_period = db.query(AssessmentDraft).filter(
            AssessmentDraft.created_at >= start
        ).count()
        submitted_in_period = db.query(AssessmentDraft).filter(
            and_(AssessmentDraft.created_at >= start, AssessmentDraft.is_submitted == True)
        ).count()
    else:
        completed_in_period = total_completed
        started_in_period = db.query(AssessmentDraft).count()
        submitted_in_period = db.query(AssessmentDraft).filter(
            AssessmentDraft.is_submitted == True
        ).count()
    
    # Active drafts (not submitted)
    active_drafts = db.query(AssessmentDraft).filter(
        AssessmentDraft.is_submitted == False
    ).count()
    
    # Processing/error assessments
    processing = db.query(Assessment).filter(Assessment.status == "processing").count()
    errors = db.query(Assessment).filter(Assessment.status == "error").count()
    
    # Completion rate
    total_drafts = db.query(AssessmentDraft).count()
    completion_rate = round((submitted_in_period / started_in_period * 100), 1) if started_in_period > 0 else 0
    
    return {
        "total_completed": total_completed,
        "completed_in_period": completed_in_period,
        "started_in_period": started_in_period,
        "submitted_in_period": submitted_in_period,
        "active_drafts": active_drafts,
        "processing": processing,
        "errors": errors,
        "completion_rate": completion_rate,
    }


def get_mentorship_metrics(db: Session, period: str = "all") -> Dict[str, Any]:
    """Get mentorship relationship metrics."""
    start, end = get_date_range(period) if period != "all" else (None, None)
    
    # Total active relationships
    active_relationships = db.query(MentorApprentice).filter(
        MentorApprentice.active == True
    ).count()
    
    # Mentors with at least one apprentice
    mentors_with_apprentices = db.query(
        func.count(func.distinct(MentorApprentice.mentor_id))
    ).filter(MentorApprentice.active == True).scalar() or 0
    
    # Average apprentices per mentor
    total_mentors = db.query(User).filter(User.role == UserRole.mentor).count()
    avg_apprentices = round(active_relationships / mentors_with_apprentices, 2) if mentors_with_apprentices > 0 else 0
    
    # Mentor utilization (mentors with apprentices / total mentors)
    mentor_utilization = round((mentors_with_apprentices / total_mentors * 100), 1) if total_mentors > 0 else 0
    
    return {
        "active_relationships": active_relationships,
        "mentors_with_apprentices": mentors_with_apprentices,
        "total_mentors": total_mentors,
        "avg_apprentices_per_mentor": avg_apprentices,
        "mentor_utilization_percent": mentor_utilization,
    }


def get_invitation_metrics(db: Session, period: str = "all") -> Dict[str, Any]:
    """Get invitation system metrics."""
    start, end = get_date_range(period) if period != "all" else (None, None)
    
    # Total invitations
    total_invitations = db.query(ApprenticeInvitation).count()
    
    # In period
    if start:
        sent_in_period = db.query(ApprenticeInvitation).filter(
            ApprenticeInvitation.expires_at >= start - timedelta(days=7)  # Adjust for 7-day expiry
        ).count()
    else:
        sent_in_period = total_invitations
    
    # Accepted invitations
    accepted = db.query(ApprenticeInvitation).filter(
        ApprenticeInvitation.accepted == True
    ).count()
    
    # Pending (not accepted, not expired)
    now = datetime.now(UTC)
    pending = db.query(ApprenticeInvitation).filter(
        and_(
            ApprenticeInvitation.accepted == False,
            ApprenticeInvitation.expires_at > now
        )
    ).count()
    
    # Expired
    expired = db.query(ApprenticeInvitation).filter(
        and_(
            ApprenticeInvitation.accepted == False,
            ApprenticeInvitation.expires_at <= now
        )
    ).count()
    
    # Acceptance rate
    acceptance_rate = round((accepted / total_invitations * 100), 1) if total_invitations > 0 else 0
    
    return {
        "total_invitations": total_invitations,
        "sent_in_period": sent_in_period,
        "accepted": accepted,
        "pending": pending,
        "expired": expired,
        "acceptance_rate": acceptance_rate,
    }


def get_agreement_metrics(db: Session, period: str = "all") -> Dict[str, Any]:
    """Get agreement signing metrics."""
    start, end = get_date_range(period) if period != "all" else (None, None)
    
    # Total agreements
    total_agreements = db.query(Agreement).count()
    
    # By status
    fully_signed = db.query(Agreement).filter(Agreement.status == "fully_signed").count()
    awaiting_apprentice = db.query(Agreement).filter(Agreement.status == "awaiting_apprentice").count()
    awaiting_parent = db.query(Agreement).filter(Agreement.status == "awaiting_parent").count()
    draft = db.query(Agreement).filter(Agreement.status == "draft").count()
    
    # In period
    if start:
        created_in_period = db.query(Agreement).filter(
            Agreement.created_at >= start
        ).count()
        signed_in_period = db.query(Agreement).filter(
            and_(Agreement.activated_at >= start, Agreement.status == "fully_signed")
        ).count()
    else:
        created_in_period = total_agreements
        signed_in_period = fully_signed
    
    # Completion rate
    completion_rate = round((fully_signed / total_agreements * 100), 1) if total_agreements > 0 else 0
    
    return {
        "total_agreements": total_agreements,
        "fully_signed": fully_signed,
        "awaiting_apprentice": awaiting_apprentice,
        "awaiting_parent": awaiting_parent,
        "draft": draft,
        "created_in_period": created_in_period,
        "signed_in_period": signed_in_period,
        "completion_rate": completion_rate,
    }


def get_template_metrics(db: Session) -> Dict[str, Any]:
    """Get assessment template metrics."""
    total_templates = db.query(AssessmentTemplate).count()
    published = db.query(AssessmentTemplate).filter(
        AssessmentTemplate.is_published == True
    ).count()
    
    # Most used templates (by assessment count)
    # This would require a join query - simplified for now
    return {
        "total_templates": total_templates,
        "published_templates": published,
        "unpublished_templates": total_templates - published,
    }


def get_mentor_activity_metrics(db: Session, period: str = "all") -> Dict[str, Any]:
    """Get mentor engagement metrics (notes added)."""
    start, end = get_date_range(period) if period != "all" else (None, None)
    
    # Total mentor notes
    total_notes = db.query(MentorNote).count()
    
    # In period
    if start:
        notes_in_period = db.query(MentorNote).filter(
            MentorNote.created_at >= start
        ).count()
    else:
        notes_in_period = total_notes
    
    # Active mentors (mentors who added notes in period)
    if start:
        active_mentors = db.query(
            func.count(func.distinct(MentorNote.mentor_id))
        ).filter(MentorNote.created_at >= start).scalar() or 0
    else:
        active_mentors = db.query(
            func.count(func.distinct(MentorNote.mentor_id))
        ).scalar() or 0
    
    return {
        "total_notes": total_notes,
        "notes_in_period": notes_in_period,
        "active_mentors": active_mentors,
    }


def get_all_metrics(db: Session, period: str = "week") -> Dict[str, Any]:
    """Get all metrics for reporting or dashboard."""
    logger.info(f"Collecting metrics for period: {period}")
    
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "period": period,
        "users": get_user_metrics(db, period),
        "assessments": get_assessment_metrics(db, period),
        "mentorship": get_mentorship_metrics(db, period),
        "invitations": get_invitation_metrics(db, period),
        "agreements": get_agreement_metrics(db, period),
        "templates": get_template_metrics(db),
        "mentor_activity": get_mentor_activity_metrics(db, period),
    }


def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    """Get simplified metrics for the status dashboard (big numbers)."""
    logger.info("Generating dashboard summary")
    
    # Current totals (all-time)
    total_users = db.query(User).count()
    total_mentors = db.query(User).filter(User.role == UserRole.mentor).count()
    total_apprentices = db.query(User).filter(User.role == UserRole.apprentice).count()
    
    # Active mentorship pairs
    active_pairs = db.query(MentorApprentice).filter(
        MentorApprentice.active == True
    ).count()
    
    # Assessments
    total_assessments = db.query(Assessment).filter(Assessment.status == "done").count()
    active_drafts = db.query(AssessmentDraft).filter(
        AssessmentDraft.is_submitted == False
    ).count()
    
    # This week's activity
    week_start = datetime.now(UTC) - timedelta(days=7)
    assessments_this_week = db.query(Assessment).filter(
        and_(Assessment.created_at >= week_start, Assessment.status == "done")
    ).count()
    new_users_this_week = db.query(User).filter(User.created_at >= week_start).count()
    
    # Agreements
    fully_signed_agreements = db.query(Agreement).filter(
        Agreement.status == "fully_signed"
    ).count()
    pending_agreements = db.query(Agreement).filter(
        Agreement.status.in_(["awaiting_apprentice", "awaiting_parent"])
    ).count()
    
    # Pending invitations
    now = datetime.now(UTC)
    pending_invitations = db.query(ApprenticeInvitation).filter(
        and_(
            ApprenticeInvitation.accepted == False,
            ApprenticeInvitation.expires_at > now
        )
    ).count()
    
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "totals": {
            "users": total_users,
            "mentors": total_mentors,
            "apprentices": total_apprentices,
            "active_pairs": active_pairs,
            "assessments_completed": total_assessments,
            "agreements_signed": fully_signed_agreements,
        },
        "activity": {
            "assessments_this_week": assessments_this_week,
            "new_users_this_week": new_users_this_week,
        },
        "pending": {
            "drafts_in_progress": active_drafts,
            "agreements_awaiting": pending_agreements,
            "invitations_pending": pending_invitations,
        },
    }
