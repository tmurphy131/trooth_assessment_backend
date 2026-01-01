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
