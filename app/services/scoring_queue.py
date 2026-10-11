"""Enqueue assessment scoring (specs/004-reliable-ai-reports).

On Cloud Run this creates a Cloud Task that POSTs to /internal/score-assessment/{id} with an OIDC
token; Cloud Tasks retries failures with backoff for the queue's retry window. Local and test
runs (``settings.scoring_inline``) run the pipeline in a background thread instead.
"""
from __future__ import annotations

import logging
import threading
import time

import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)

_TASKS_API = "https://cloudtasks.googleapis.com/v2"


def _access_token() -> str:
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(Request())
    return credentials.token


def _run_inline(assessment_id: str) -> None:
    from app.services import scoring_pipeline

    try:
        scoring_pipeline.score_assessment(assessment_id, attempt_info=None)
    except Exception as e:  # inline mode has no retries; the sweep or a re-queue recovers it
        logger.warning("inline scoring for %s did not complete: %s", assessment_id, e)


def enqueue(assessment_id: str, reason: str, unique: bool = False) -> str:
    """Queue scoring for one assessment. Returns the task name ("inline" in local/test).

    ``unique=False`` names the task ``score-<id>`` so a duplicate submit can't enqueue twice;
    re-queues pass ``unique=True`` to get a fresh name.
    """
    if settings.scoring_inline:
        threading.Thread(target=_run_inline, args=(assessment_id,), daemon=True).start()
        logger.info("scoring queued inline assessment=%s reason=%s", assessment_id, reason)
        return "inline"

    parent = (f"projects/{settings.scoring_queue_project}/locations/{settings.scoring_queue_location}"
              f"/queues/{settings.scoring_queue_name}")
    task_id = f"score-{assessment_id}" + (f"-{int(time.time())}" if unique else "")
    base_url = settings.backend_api_url.rstrip("/") + "/"
    body = {"task": {
        "name": f"{parent}/tasks/{task_id}",
        "dispatchDeadline": "300s",
        "httpRequest": {
            "httpMethod": "POST",
            "url": f"{base_url}internal/score-assessment/{assessment_id}",
            "oidcToken": {"serviceAccountEmail": settings.scoring_service_account, "audience": base_url},
        },
    }}
    r = httpx.post(f"{_TASKS_API}/{parent}/tasks", json=body,
                   headers={"Authorization": f"Bearer {_access_token()}"}, timeout=15)
    if r.status_code == 409:  # a task with this name already exists: already queued
        logger.info("scoring already queued assessment=%s task=%s", assessment_id, task_id)
        return task_id
    if r.status_code >= 300:
        raise RuntimeError(f"Cloud Tasks create failed ({r.status_code}): {r.text[:300]}")
    logger.info("scoring queued assessment=%s task=%s reason=%s", assessment_id, task_id, reason)
    return task_id
