"""
Metrics API routes for T[root]H Discipleship.
Provides endpoints for dashboard data and report generation.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.metrics import get_all_metrics, get_dashboard_summary
from app.services.metrics_reports import send_report_now
from app.models.user import User, UserRole
from app.models.mentor_apprentice import MentorApprentice

logger = logging.getLogger("app.routes.metrics")

router = APIRouter()


@router.get("/dashboard")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """
    Get simplified metrics for the status dashboard.
    This endpoint is PUBLIC (no auth) for the hidden status page.
    Returns big numbers for quick health check.
    """
    logger.info("Dashboard metrics requested")
    try:
        summary = get_dashboard_summary(db)
        return {"status": "success", "data": summary}
    except Exception as e:
        logger.error(f"Failed to generate dashboard metrics: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/users")
def get_user_list(
    category: str = Query(..., description="Category: 'all', 'mentors', 'apprentices', or 'pairs'"),
    db: Session = Depends(get_db),
):
    """
    Get user names for a given category. PUBLIC (hidden status page).
    """
    logger.info(f"User list requested for category: {category}")
    try:
        if category == "all":
            users = db.query(User.name, User.role, User.created_at).order_by(User.created_at.desc()).all()
            return {"status": "success", "data": [
                {"name": u.name, "role": u.role.value, "joined": u.created_at.strftime("%b %d, %Y") if u.created_at else ""}
                for u in users
            ]}
        elif category == "mentors":
            users = db.query(User.name, User.created_at).filter(User.role == UserRole.mentor).order_by(User.created_at.desc()).all()
            return {"status": "success", "data": [
                {"name": u.name, "joined": u.created_at.strftime("%b %d, %Y") if u.created_at else ""}
                for u in users
            ]}
        elif category == "apprentices":
            users = db.query(User.name, User.created_at).filter(User.role == UserRole.apprentice).order_by(User.created_at.desc()).all()
            return {"status": "success", "data": [
                {"name": u.name, "joined": u.created_at.strftime("%b %d, %Y") if u.created_at else ""}
                for u in users
            ]}
        elif category == "pairs":
            pairs = (
                db.query(MentorApprentice, User)
                .join(User, MentorApprentice.mentor_id == User.id)
                .filter(MentorApprentice.active == True)
                .all()
            )
            result = []
            for pair, mentor in pairs:
                apprentice = db.query(User.name).filter(User.id == pair.apprentice_id).first()
                result.append({
                    "mentor": mentor.name,
                    "apprentice": apprentice.name if apprentice else "Unknown",
                })
            return {"status": "success", "data": result}
        else:
            return {"status": "error", "message": "Invalid category. Use 'all', 'mentors', 'apprentices', or 'pairs'."}
    except Exception as e:
        logger.error(f"Failed to fetch user list: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/full")
def get_full_metrics(
    period: str = "week",
    db: Session = Depends(get_db)
):
    """
    Get full metrics report for the specified period.
    This endpoint is PUBLIC (no auth) for the hidden status page.
    
    Args:
        period: "day", "week", "month", or "all"
    """
    logger.info(f"Full metrics requested for period: {period}")
    
    if period not in ["day", "week", "month", "all"]:
        period = "week"
    
    try:
        metrics = get_all_metrics(db, period)
        return {"status": "success", "data": metrics}
    except Exception as e:
        logger.error(f"Failed to generate full metrics: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/send-report")
def trigger_report_send(
    report_type: str = Query("weekly", description="Report type: 'weekly' or 'monthly'"),
    recipient: Optional[str] = Query(None, description="Override recipient email (optional)")
):
    """
    Manually trigger sending a metrics report email.
    This endpoint is PUBLIC (hidden page access) but requires knowing the URL.
    
    Args:
        report_type: "weekly" or "monthly"
        recipient: Optional override email address
    """
    logger.info(f"Manual report trigger: type={report_type}, recipient={recipient}")
    
    if report_type not in ["weekly", "monthly"]:
        return {"status": "error", "message": "Invalid report_type. Use 'weekly' or 'monthly'"}
    
    try:
        success = send_report_now(report_type, recipient)
        if success:
            return {"status": "success", "message": f"{report_type.capitalize()} report sent successfully"}
        else:
            return {"status": "error", "message": "Failed to send report. Check server logs."}
    except Exception as e:
        logger.error(f"Failed to trigger report: {e}")
        return {"status": "error", "message": str(e)}
