"""Durable assessment scoring (specs/004-reliable-ai-reports).

``score_assessment`` is called by the Cloud Tasks handler (/internal/score-assessment/{id}) or, in
local/test, inline. It never marks an assessment ``done`` with fallback content: a failed AI run
raises ``ScoringRetryable`` so Cloud Tasks retries; the handler calls ``mark_failed`` once the
retry window (measured from ``scoring_queued_at``) is exhausted.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import or_

from app.db import SessionLocal
from app.models.assessment import Assessment

logger = logging.getLogger(__name__)

LEASE = timedelta(minutes=15)
DEFAULT_RECOMMENDATION_PREFIX = "Continue developing your"  # ai_scoring's per-category fallback text

# Internal codes -> user-safe reasons shown in the app (<= 300 chars)
FAILURE_REASONS = {
    "ai_unavailable": "AI provider unavailable",
    "ai_invalid_output": "The report could not be generated",
    "internal": "The report could not be generated",
}


class ScoringRetryable(Exception):
    """Transient failure; the queue should retry later. ``code`` maps to FAILURE_REASONS."""

    def __init__(self, message: str, code: str = "ai_unavailable"):
        super().__init__(message)
        self.code = code


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)  # columns are naive UTC


def _claim_lease(session, assessment_id: str) -> bool:
    now = _now()
    claimed = (
        session.query(Assessment)
        .filter(
            Assessment.id == assessment_id,
            Assessment.status != "done",
            or_(Assessment.scoring_lease_until.is_(None), Assessment.scoring_lease_until < now),
        )
        .update({
            Assessment.scoring_lease_until: now + LEASE,
            Assessment.scoring_attempts: Assessment.scoring_attempts + 1,
        }, synchronize_session=False)
    )
    session.commit()
    return claimed == 1


def _release_lease(session, assessment_id: str) -> None:
    session.query(Assessment).filter(Assessment.id == assessment_id).update(
        {Assessment.scoring_lease_until: None}, synchronize_session=False)
    session.commit()


def _build_questions(session, assess) -> list[dict]:
    from app.models.assessment_template_question import AssessmentTemplateQuestion as _ATQ
    from app.models.category import Category as _Category
    from app.models.question import Question as _Question

    questions = []
    if assess.template_id:
        tqs = (
            session.query(_ATQ)
            .join(_Question, _ATQ.question_id == _Question.id)
            .filter(_ATQ.template_id == assess.template_id)
            .order_by(_ATQ.order)
            .all()
        )
        for tq in tqs:
            cat_name = None
            if getattr(tq.question, "category_id", None):
                cat = session.query(_Category).filter_by(id=tq.question.category_id).first()
                cat_name = cat.name if cat else None
            opts = []
            for opt in (tq.question.options or []):
                opts.append({
                    "id": str(opt.id) if getattr(opt, "id", None) else None,
                    "text": getattr(opt, "option_text", None),
                    "is_correct": bool(getattr(opt, "is_correct", False)),
                })
            qtype = getattr(tq.question, "question_type", None)
            qtype = qtype.value if hasattr(qtype, "value") else qtype
            questions.append({
                "id": str(tq.question.id),
                "text": tq.question.text,
                "category": cat_name or "General Assessment",
                "question_type": qtype,
                "options": opts,
            })
    if not questions:
        questions = [{"id": k, "text": f"Question {k}", "category": "General Assessment"}
                     for k in (assess.answers or {}).keys()]
    return questions


def _previous_assessments(session, assess) -> list[dict]:
    if not assess.previous_assessment_id:
        return []
    prev = session.query(Assessment).filter_by(id=assess.previous_assessment_id).first()
    if prev and prev.scores:
        return [{"id": prev.id, "created_at": str(prev.created_at) if prev.created_at else None,
                 "scores": prev.scores, "mentor_report_v2": prev.mentor_report_v2}]
    return []


def _has_open_ended(answers: dict, questions: list[dict]) -> bool:
    qmap = {str(q.get("id")): q for q in questions}
    for qid, ans in (answers or {}).items():
        q = qmap.get(str(qid))
        if q and (q.get("question_type") or "").lower() != "multiple_choice" and str(ans or "").strip():
            return True
    return False


def _is_fallback(scoring: dict, answers: dict, questions: list[dict]) -> Optional[str]:
    """Why this result is fallback content (not a real AI report), or None if it's real."""
    blob = scoring.get("mentor_blob_v2") or {}
    if _has_open_ended(answers, questions) and not blob.get("insights") and not blob.get("strengths"):
        return "mentor report has no AI insights"
    recs = scoring.get("recommendations") or {}
    if recs and all(str(v).startswith(DEFAULT_RECOMMENDATION_PREFIX) for v in recs.values()):
        return "every category used the default recommendation"
    return None


def _is_master(session, assess) -> bool:
    if assess.category == "master_trooth":
        return True
    if not assess.template_id:
        return False
    from app.models.assessment_template import AssessmentTemplate

    tpl = session.query(AssessmentTemplate).filter_by(id=assess.template_id).first()
    return bool(tpl and tpl.is_master_assessment)


def _run_scorer(answers: dict, questions: list[dict], previous: list[dict], master: bool = False) -> dict:
    from app.services.ai_scoring import score_assessment_by_category, score_master_v3

    if master:  # one structured AI call; numbers computed in code
        return score_master_v3(answers, questions, previous)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(score_assessment_by_category(answers, questions, previous))
    finally:
        loop.close()


def score_assessment(assessment_id: str, attempt_info: Optional[dict] = None) -> str:
    """Score one assessment. Returns "done", "already_done" or "missing".

    Raises ScoringRetryable for anything the queue should retry, including a live lease held by
    another worker (so a crashed worker's task isn't dropped).
    """
    session = SessionLocal()
    try:
        assess = session.query(Assessment).filter_by(id=assessment_id).first()
        if not assess:
            return "missing"
        if assess.status == "done":
            return "already_done"
        if not _claim_lease(session, assessment_id):
            session.refresh(assess)
            if assess.status == "done":
                return "already_done"
            raise ScoringRetryable("leased", code="internal")

        try:
            session.refresh(assess)
            questions = _build_questions(session, assess)
            previous = _previous_assessments(session, assess)
            try:
                scoring = _run_scorer(assess.answers or {}, questions, previous, _is_master(session, assess))
            except Exception as e:
                raise ScoringRetryable(f"scorer error: {e}", code=getattr(e, "code", "ai_unavailable")) from e
            why = _is_fallback(scoring, assess.answers or {}, questions)
            if why:
                # Same text feature 003's "Scoring fallback" alert matches
                logger.error("Failed to build mentor_blob v2 for assessment %s: %s (will retry)", assessment_id, why)
                raise ScoringRetryable(why, code="ai_unavailable")

            completed = _now()
            updated = (
                session.query(Assessment)
                .filter(Assessment.id == assessment_id, Assessment.status != "done")
                .update({
                    Assessment.scores: scoring,
                    Assessment.mentor_report_v2: scoring.get("mentor_blob_v2"),
                    Assessment.recommendation: scoring.get("summary_recommendation"),
                    Assessment.status: "done",
                    Assessment.failure_reason: None,
                    Assessment.scoring_completed_at: completed,
                    Assessment.scoring_lease_until: None,
                }, synchronize_session=False)
            )
            session.commit()
            if updated != 1:
                return "already_done"
        except Exception:
            session.rollback()
            _release_lease(session, assessment_id)
            raise

        logger.info("scoring done assessment=%s attempts=%s version=%s", assessment_id,
                    (assess.scoring_attempts or 0), scoring.get("scoring_version", "v2"))
        session.refresh(assess)
        try:
            notify_mentors(session, assess, questions, previous)
        except Exception as e:  # the report is done; a mail failure must not trigger a re-score
            logger.error("mentor notification failed for %s: %s", assessment_id, e)
        return "done"
    finally:
        session.close()


def mark_failed(assessment_id: str, code: str, detail: str = "") -> None:
    reason = FAILURE_REASONS.get(code, FAILURE_REASONS["internal"])
    session = SessionLocal()
    try:
        session.query(Assessment).filter(Assessment.id == assessment_id, Assessment.status != "done").update({
            Assessment.status: "failed",
            Assessment.failure_reason: reason[:300],
            Assessment.scoring_lease_until: None,
        }, synchronize_session=False)
        session.commit()
    finally:
        session.close()
    logger.error("scoring_failed assessment=%s reason=%s detail=%s", assessment_id, code, str(detail)[:200])
    logger.error("Failed to build mentor_blob (final) for assessment %s", assessment_id)


def notify_mentors(session, assess, questions: list[dict], previous: list[dict]) -> None:
    """Email each active mentor the report once (guarded by scores.mentor_email_sent_at)."""
    from app.models.mentor_apprentice import MentorApprentice
    from app.models.user import User
    from app.services.auth import is_premium_user

    scores = dict(assess.scores or {})
    if scores.get("mentor_email_sent_at"):
        return
    apprentice = session.query(User).filter_by(id=assess.apprentice_id).first()
    apprentice_name = getattr(apprentice, "name", None) or "Apprentice"
    rels = session.query(MentorApprentice).filter_by(apprentice_id=assess.apprentice_id, active=True).all()
    sent_any = False
    for rel in rels:
        mentor = session.query(User).filter_by(id=rel.mentor_id).first()
        if not (mentor and mentor.email):
            continue
        _email_mentor(session, assess, mentor, apprentice_name, is_premium_user(mentor), questions, previous)
        sent_any = True
    if sent_any:
        scores = dict(assess.scores or {})
        scores["mentor_email_sent_at"] = _now().isoformat()
        assess.scores = scores
        session.commit()


def _email_mentor(session, assess, mentor, apprentice_name, mentor_is_premium, questions, previous) -> None:
    from app.models.assessment_template import AssessmentTemplate
    from app.services.email import render_mentor_report_v2_email, render_premium_report_email, send_email
    from app.services.master_trooth_report import build_report_context

    blob = assess.mentor_report_v2
    if not blob:
        return
    tpl = session.query(AssessmentTemplate).filter_by(id=assess.template_id).first() if assess.template_id else None
    template_name = getattr(tpl, "name", None) or "Assessment"
    context = build_report_context(
        {"apprentice": {"id": assess.apprentice_id, "name": apprentice_name},
         "template_id": assess.template_id, "created_at": assess.created_at},
        assess.scores or {}, blob)
    today = datetime.now(UTC).date()
    html = plain = None
    subject = f"{template_name} Report — {apprentice_name} — {today}"
    if mentor_is_premium:
        try:
            full_report = _ensure_full_report(session, assess, apprentice_name, questions, previous)
            html, plain = render_premium_report_email(context, full_report)
            subject = f"✦ PREMIUM {template_name} Report — {apprentice_name} — {today}"
        except Exception as e:
            logger.warning("premium report for %s failed, sending the standard email: %s", assess.id, e)
    if html is None:
        html, plain = render_mentor_report_v2_email(context)
    ok = send_email(mentor.email, subject, html, plain)
    logger.info("mentor report email sent ok=%s assessment=%s premium=%s", ok, assess.id, mentor_is_premium)


def _ensure_full_report(session, assess, apprentice_name, questions, previous) -> dict:
    """Generate and store the Premium report once (US4 replaces this with full_report.py)."""
    existing = (assess.scores or {}).get("full_report_v1")
    if existing:
        return existing
    from app.services.ai_scoring import _build_v2_prompt_input, generate_full_report

    payload, _ = _build_v2_prompt_input(
        apprentice={"id": assess.apprentice_id, "name": apprentice_name},
        assessment_id=assess.id, template_id=assess.template_id,
        submitted_at=assess.created_at.isoformat() if assess.created_at else None,
        answers=assess.answers or {}, questions=questions, previous_assessments=previous)
    full_report = generate_full_report(payload, previous)
    scores = dict(assess.scores or {})
    scores["full_report_v1"] = full_report
    scores["full_report_generated_at"] = _now().isoformat()
    assess.scores = scores
    assess.full_report_status = "ready"
    session.commit()
    return full_report
