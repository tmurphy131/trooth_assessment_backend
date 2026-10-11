"""Premium full report: generated once per assessment (specs/004-reliable-ai-reports, US4).

The scoring task generates it right after the free report when the apprentice or one of their
mentors is premium. The full-report endpoints call ``get_or_generate_full_report``, which returns
the stored copy, or claims generation (a conditional UPDATE, so only one caller generates) while
other callers wait for it. Malformed AI output is retried; a final failure is a 503, never a 500.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, or_

from app.models.assessment import Assessment
from app.services.report_summary import public_full_report

logger = logging.getLogger(__name__)

CLAIM_STALE = timedelta(minutes=5)
GENERATE_ATTEMPTS = 3  # first try + 2 retries
UNAVAILABLE = "Report is temporarily unavailable"


class FullReportUnavailable(Exception):
    pass


def _clock() -> float:  # wrappers so tests can control waiting without patching the time module
    return time.monotonic()


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def stored_report(assess: Assessment) -> Optional[dict]:
    return (assess.scores or {}).get("full_report_v1")


def claim(session, assessment_id: str) -> bool:
    """Take the right to generate: nobody is generating, or the last claim went stale."""
    now = _now()
    claimed = (
        session.query(Assessment)
        .filter(
            Assessment.id == assessment_id,
            or_(
                Assessment.full_report_status.is_(None),
                Assessment.full_report_status == "failed",
                and_(Assessment.full_report_status == "generating",
                     or_(Assessment.full_report_claimed_at.is_(None),
                         Assessment.full_report_claimed_at < now - CLAIM_STALE)),
            ),
        )
        .update({Assessment.full_report_status: "generating", Assessment.full_report_claimed_at: now},
                synchronize_session=False)
    )
    session.commit()
    return claimed == 1


def _set_status(session, assessment_id: str, status: str) -> None:
    session.query(Assessment).filter(Assessment.id == assessment_id).update(
        {Assessment.full_report_status: status, Assessment.full_report_claimed_at: None},
        synchronize_session=False)
    session.commit()


def generate_and_store(session, assess: Assessment, questions: Optional[list] = None,
                       previous: Optional[list] = None) -> dict:
    """Generate the Premium report (caller holds the claim) and store it on the assessment.

    Retries failed or malformed generations; on final failure sets ``full_report_status='failed'``
    and raises FullReportUnavailable.
    """
    from app.models.user import User
    from app.services import scoring_pipeline
    from app.services.ai_scoring import _build_v2_prompt_input, generate_full_report

    if questions is None:
        questions = scoring_pipeline._build_questions(session, assess)
    if previous is None:
        previous = scoring_pipeline._previous_assessments(session, assess)
    apprentice = session.query(User).filter_by(id=assess.apprentice_id).first()
    payload, _ = _build_v2_prompt_input(
        apprentice={"id": assess.apprentice_id, "name": getattr(apprentice, "name", None) or "Apprentice"},
        assessment_id=assess.id, template_id=assess.template_id,
        submitted_at=assess.created_at.isoformat() if assess.created_at else None,
        answers=assess.answers or {}, questions=questions, previous_assessments=previous)
    facts = (assess.scores or {}).get("computed_facts")

    last_error = None
    for attempt in range(1, GENERATE_ATTEMPTS + 1):
        try:
            report = generate_full_report(payload, previous, computed_facts=facts)
            if not isinstance(report, dict) or not report.get("executive_summary"):
                raise ValueError("full report is missing executive_summary")
            break
        except Exception as e:
            last_error = e
            logger.warning("full report attempt %s/%s failed for %s: %s", attempt, GENERATE_ATTEMPTS,
                           assess.id, str(e)[:300])
    else:
        _set_status(session, assess.id, "failed")
        logger.error("full_report_failed assessment=%s error=%s", assess.id, str(last_error)[:300])
        raise FullReportUnavailable(str(last_error))

    session.refresh(assess)
    scores = dict(assess.scores or {})
    scores["full_report_v1"] = report
    scores["full_report_generated_at"] = _now().isoformat()
    assess.scores = scores
    assess.full_report_status = "ready"
    assess.full_report_claimed_at = None
    session.commit()
    logger.info("full report ready assessment=%s attempts=%s", assess.id, attempt)
    return report


def _response(assess: Assessment, report: dict, cached: bool) -> dict:
    return {"report": public_full_report(report, assess.mentor_report_v2), "cached": cached,
            "generated_at": (assess.scores or {}).get("full_report_generated_at")}


def get_or_generate_full_report(db, assess: Assessment, wait_s: float = 90, poll_s: float = 2) -> dict:
    """Stored report, or generate it once, or wait for the caller who is generating it.

    Returns ``{"report", "cached", "generated_at"}``, or ``{"status": "generating", "cached": False}``
    while the free report is still being scored or another caller's generation outlasts the wait.
    Raises a 503 HTTPException when generation fails.
    """
    deadline = _clock() + wait_s
    while True:
        db.refresh(assess)
        report = stored_report(assess)
        if report:
            return _response(assess, report, cached=True)
        if assess.status == "processing":  # Premium needs the scored facts; the scoring task generates it
            return {"status": "generating", "cached": False}
        if claim(db, assess.id):
            try:
                report = generate_and_store(db, assess)
            except FullReportUnavailable:
                raise HTTPException(status_code=503, detail=UNAVAILABLE)
            return _response(assess, report, cached=False)
        if _clock() >= deadline:
            return {"status": "generating", "cached": False}
        _sleep(poll_s)
