"""Email/PDF report routes never wait on Premium generation; it's queued for next time."""
import uuid
from datetime import UTC, datetime

import pytest

from app.main import app
from app.models.assessment import Assessment
from app.models.user import User
from app.services import full_report
from app.services.auth import verify_token


@pytest.fixture
def premium_everyone(monkeypatch):
    import app.services.auth as auth_mod
    monkeypatch.setattr(auth_mod, "is_premium_user", lambda user: True)


@pytest.fixture
def no_inline_generation(monkeypatch):
    import app.services.ai_scoring as ai_scoring

    def _boom(*a, **k):
        raise AssertionError("report routes must not generate the Premium report inline")

    monkeypatch.setattr(ai_scoring, "generate_full_report_for_assessment", _boom, raising=False)


@pytest.fixture
def queued(monkeypatch):
    calls = []
    import app.services.scoring_queue as scoring_queue
    monkeypatch.setattr(scoring_queue, "enqueue", lambda aid, reason, unique=False: calls.append((aid, reason, unique)) or "t")
    return calls


def _apprentice_assessment(db, **scores):
    u = User(id=str(uuid.uuid4()), name="Ap", email=f"ap+{uuid.uuid4().hex[:8]}@example.com",
             role="apprentice", created_at=datetime.now(UTC))
    db.add(u)
    db.flush()
    a = Assessment(apprentice_id=u.id, answers={}, scores=dict(scores),
                   mentor_report_v2={"health_score": 60, "health_band": "Growing"}, status="done")
    db.add(a)
    db.commit()
    return u, a


def test_pdf_without_premium_report_returns_now_and_queues(client, db_session, premium_everyone, no_inline_generation, queued):
    user, a = _apprentice_assessment(db_session)
    app.dependency_overrides[verify_token] = lambda: {"uid": user.id}
    try:
        r = client.get(f"/assessments/{a.id}/mentor-report-v2.pdf")
    finally:
        app.dependency_overrides.pop(verify_token, None)
    assert r.status_code == 200 and r.content.startswith(b"%PDF-")
    assert queued == [(a.id, "premium-requested", True)]


def test_pdf_with_stored_premium_report_does_not_queue(client, db_session, premium_everyone, no_inline_generation, queued):
    user, a = _apprentice_assessment(db_session, full_report_v1={"executive_summary": {"one_liner": "x"}})
    app.dependency_overrides[verify_token] = lambda: {"uid": user.id}
    try:
        r = client.get(f"/assessments/{a.id}/mentor-report-v2.pdf")
    finally:
        app.dependency_overrides.pop(verify_token, None)
    assert r.status_code == 200
    assert queued == []


def test_queue_premium_skips_when_stored_or_generating(db_session, queued):
    _, stored = _apprentice_assessment(db_session, full_report_v1={"executive_summary": {}})
    _, busy = _apprentice_assessment(db_session)
    busy.full_report_status = "generating"
    db_session.commit()
    full_report.queue_premium(stored)
    full_report.queue_premium(busy)
    assert queued == []


def test_scoring_task_fills_in_missing_premium_for_scored_assessment(db_session, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    import app.services.scoring_pipeline as pipeline

    _, a = _apprentice_assessment(db_session)
    calls = []
    monkeypatch.setattr(pipeline, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    monkeypatch.setattr(pipeline, "generate_premium", lambda session, assess, q, p: calls.append(assess.id))
    assert pipeline.score_assessment(a.id) == "already_done"
    assert calls == [a.id]
