"""Internal endpoint Cloud Tasks calls to score an assessment (specs/004-reliable-ai-reports).

Auth: a Google-signed OIDC token for the scoring service account, audience = BACKEND_API_URL.
Cloud Tasks retries any non-2xx response, so permanent outcomes return 200 with a ``result`` and
only retryable failures return 503.
"""
import logging
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.db import SessionLocal
from app.models.assessment import Assessment
from app.services import scoring_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_task_token(authorization: Optional[str]) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=403, detail="Missing task token")
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    audience = settings.backend_api_url.rstrip("/") + "/"
    try:
        claims = id_token.verify_oauth2_token(authorization.split(" ", 1)[1], google_requests.Request(),
                                              audience=audience)
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid task token")
    if claims.get("email") != settings.scoring_service_account or not claims.get("email_verified"):
        raise HTTPException(status_code=403, detail="Invalid task token")


def _retry_window_exhausted(assessment_id: str) -> bool:
    session = SessionLocal()
    try:
        a = session.query(Assessment).filter_by(id=assessment_id).first()
        queued_at = (a.scoring_queued_at or a.created_at) if a else None
    finally:
        session.close()
    if not queued_at:
        return False
    elapsed = (datetime.now(UTC).replace(tzinfo=None) - queued_at).total_seconds()
    return elapsed >= settings.scoring_retry_window_s - 60


@router.post("/internal/score-assessment/{assessment_id}", include_in_schema=False)
def score_assessment_task(
    assessment_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    x_cloudtasks_taskretrycount: Optional[str] = Header(None),
):
    verify_task_token(authorization)
    retry_count = int(x_cloudtasks_taskretrycount or 0)
    try:
        result = scoring_pipeline.score_assessment(assessment_id, attempt_info={"retry_count": retry_count})
        return {"result": result}
    except scoring_pipeline.ScoringRetryable as e:
        if str(e) != "leased" and _retry_window_exhausted(assessment_id):
            scoring_pipeline.mark_failed(assessment_id, e.code, str(e))
            return {"result": "failed", "reason": scoring_pipeline.FAILURE_REASONS.get(e.code)}
        logger.warning("scoring retry assessment=%s retry=%s reason=%s", assessment_id, retry_count, e)
        return JSONResponse(status_code=503, content={"detail": f"retry: {e}"})
    except Exception as e:  # unexpected: retry, and give up at the window like any other failure
        logger.error("scoring error assessment=%s: %s", assessment_id, e, exc_info=True)
        if _retry_window_exhausted(assessment_id):
            scoring_pipeline.mark_failed(assessment_id, "internal", str(e))
            return {"result": "failed", "reason": scoring_pipeline.FAILURE_REASONS["internal"]}
        return JSONResponse(status_code=503, content={"detail": "retry: internal error"})
