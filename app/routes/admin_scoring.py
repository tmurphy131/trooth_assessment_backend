"""Recover failed, stuck or outage-emptied assessments (specs/004-reliable-ai-reports).

- POST /admin/assessments/requeue — admin user or X-Cron-Secret.
- POST /scheduled/scoring-sweep   — X-Cron-Secret; Cloud Scheduler every 15 minutes.
"""
import hmac
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.assessment import Assessment
from app.models.user import UserRole
from app.services import scoring_queue
from app.services.auth import get_current_user_optional, require_cron_secret

logger = logging.getLogger(__name__)
router = APIRouter()

STUCK_AFTER = timedelta(minutes=75)
FAILED_RETRY_AFTER = timedelta(hours=6)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def require_admin_or_cron(
    x_cron_secret: Optional[str] = Header(None),
    user=Depends(get_current_user_optional),
) -> str:
    """Accept the scheduler secret, else an authenticated admin user."""
    expected = os.getenv("CRON_SECRET", "")
    if x_cron_secret and expected and hmac.compare_digest(x_cron_secret, expected):
        return "cron"
    role = (user.role.value if hasattr(user.role, "value") else str(user.role)) if user else None
    if role != UserRole.admin.value:
        raise HTTPException(status_code=403, detail="Admin or scheduler access required")
    return "admin"


def _is_fallback_report(blob: Optional[dict]) -> bool:
    blob = blob or {}
    return not blob.get("insights") and not blob.get("strengths")


def _requeue(db: Session, ids: List[str], reason: str) -> tuple[list, list]:
    requeued, skipped = [], []
    now = _now()
    for a in db.query(Assessment).filter(Assessment.id.in_(ids)).all():
        if a.scoring_lease_until and a.scoring_lease_until > now:
            skipped.append({"id": a.id, "why": "already processing"})
            continue
        a.status = "processing"
        a.failure_reason = None
        a.scoring_queued_at = now
        db.commit()
        try:
            scoring_queue.enqueue(a.id, reason, unique=True)
            requeued.append(a.id)
        except Exception as e:
            logger.error("requeue failed for %s: %s", a.id, e)
            skipped.append({"id": a.id, "why": "enqueue failed"})
    return requeued, skipped


class RequeueRequest(BaseModel):
    ids: Optional[List[str]] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    include_done_fallback: bool = False


@router.post("/admin/assessments/requeue")
def requeue_assessments(body: RequeueRequest, db: Session = Depends(get_db),
                        _who: str = Depends(require_admin_or_cron)):
    if not (body.ids or body.since or body.until):
        raise HTTPException(status_code=422, detail="Provide ids, since or until")
    q = db.query(Assessment)
    if body.ids:
        q = q.filter(Assessment.id.in_(body.ids))
    if body.since:
        q = q.filter(Assessment.created_at >= body.since.replace(tzinfo=None))
    if body.until:
        q = q.filter(Assessment.created_at < body.until.replace(tzinfo=None))
    candidates = []
    for a in q.all():
        if a.status in ("failed", "processing") or body.ids:
            candidates.append(a.id)
        elif body.include_done_fallback and a.status == "done" and _is_fallback_report(a.mentor_report_v2):
            candidates.append(a.id)
    requeued, skipped = _requeue(db, candidates, "admin")
    return {"requeued": len(requeued), "ids": requeued, "skipped": skipped}


@router.post("/scheduled/scoring-sweep")
def scoring_sweep(db: Session = Depends(get_db), _auth: bool = Depends(require_cron_secret)):
    now = _now()
    stuck_before = now - STUCK_AFTER
    lease_free = or_(Assessment.scoring_lease_until.is_(None), Assessment.scoring_lease_until < now)
    stuck = db.query(Assessment).filter(
        Assessment.status == "processing", Assessment.scoring_queued_at < stuck_before, lease_free).all()

    never_ran, gave_up = [], []
    for a in stuck:
        (never_ran if not a.scoring_attempts else gave_up).append(a)
    # Ran and the queue stopped retrying without a final answer: that's a failure, not a re-queue loop
    for a in gave_up:
        a.status = "failed"
        a.failure_reason = "AI provider unavailable"
        logger.error("scoring_failed assessment=%s reason=retry_window_exhausted detail=sweep", a.id)
        logger.error("Failed to build mentor_blob (final) for assessment %s", a.id)
    db.commit()

    retry_failed = db.query(Assessment).filter(
        Assessment.status == "failed", Assessment.scoring_queued_at < now - FAILED_RETRY_AFTER).all()
    requeued, skipped = _requeue(db, [a.id for a in never_ran + retry_failed], "sweep")
    return {"requeued": len(requeued), "ids": requeued, "marked_failed": [a.id for a in gave_up],
            "skipped": skipped}
