"""Durable scoring (specs/004-reliable-ai-reports, User Story 1).

The AI scorer, Cloud Tasks and Google OIDC verification are mocked; the pipeline runs against
the test database.
"""
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Assessment, User
from app.models.assessment_draft import AssessmentDraft
from app.models.assessment_template import AssessmentTemplate
from app.models.mentor_apprentice import MentorApprentice
from app.routes import admin_scoring, internal_scoring
from app.services import scoring_pipeline, scoring_queue
from app.services.auth import get_current_user, get_current_user_optional, verify_token
from sqlalchemy.orm import sessionmaker

client = TestClient(app)
SA = "trooth-run-sa@trooth-prod.iam.gserviceaccount.com"
TASK = {"Authorization": "Bearer task-token"}
CRON = {"X-Cron-Secret": "test-cron-secret"}


def _naive_now():
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture(autouse=True)
def wiring(monkeypatch, db_session):
    """Point the pipeline at the test DB, accept the fake task token, capture enqueues and emails."""
    # Same engine as conftest's sessions (importing tests.conftest again would create a second DB)
    test_sessions = sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())
    monkeypatch.setattr(scoring_pipeline, "SessionLocal", test_sessions)
    monkeypatch.setattr(internal_scoring, "SessionLocal", test_sessions)

    def verify(token, request, audience=None):
        if token != "task-token":
            raise ValueError("bad token")
        return {"email": SA, "email_verified": True, "aud": audience}

    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", verify)
    enqueued = []
    monkeypatch.setattr(scoring_queue, "enqueue", lambda aid, reason, unique=False: enqueued.append((aid, reason)) or "t")
    emails = []
    monkeypatch.setattr(scoring_pipeline, "notify_mentors", lambda *a, **k: emails.append(a[1].id))
    yield {"enqueued": enqueued, "emails": emails}
    for dep in (get_current_user, get_current_user_optional, verify_token):
        app.dependency_overrides.pop(dep, None)


def _real_result():
    return {
        "overall_score": 7, "category_scores": {"Prayer Life": 7},
        "recommendations": {"Prayer Life": "Pray before checking your phone each morning."},
        "question_feedback": [], "summary_recommendation": "Keep going",
        "mentor_blob_v2": {"health_score": 76, "health_band": "Maturing", "strengths": ["Faithful"],
                           "gaps": [], "insights": [{"category": "Prayer Life", "level": "Stable",
                                                    "observation": "o", "next_step": "n"}],
                           "biblical_knowledge": {"percent": 80.0}, "flags": {}},
    }


def _fallback_result():
    r = _real_result()
    r["mentor_blob_v2"] = {"health_score": 0, "health_band": "Beginning", "strengths": [], "gaps": [],
                           "insights": [], "biblical_knowledge": {"percent": 0.0}, "flags": {}}
    r["recommendations"] = {"Prayer Life": "Continue developing your prayer life practices."}
    return r


@pytest.fixture
def make(db_session):
    def _make(status="processing", queued_ago=timedelta(0), attempts=0, lease_until=None, blob=None, created_ago=None):
        user = User(id=str(uuid4()), name="Jordan", email=f"a{uuid4().hex[:6]}@example.com", role="apprentice")
        now = _naive_now()
        a = Assessment(id=str(uuid4()), apprentice_id=user.id, template_id=None, category="master_trooth",
                       answers={"q1": "I pray every morning and journal what I hear."},
                       status=status, scoring_attempts=attempts, scoring_queued_at=now - queued_ago,
                       scoring_lease_until=lease_until, mentor_report_v2=blob,
                       created_at=now - (created_ago or queued_ago))
        db_session.add_all([user, a])
        db_session.commit()
        return a
    return _make


def _reload(db_session, aid):
    db_session.expire_all()
    return db_session.get(Assessment, aid)


def _score(aid, headers=TASK, retry=0):
    return client.post(f"/internal/score-assessment/{aid}",
                       headers={**headers, "X-CloudTasks-TaskRetryCount": str(retry)})


# ---------- T007: OIDC ----------

def test_task_endpoint_requires_valid_oidc(make, monkeypatch):
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a: _real_result())
    a = make()
    assert _score(a.id, headers={}).status_code == 403
    assert _score(a.id, headers={"Authorization": "Bearer forged"}).status_code == 403
    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token",
                        lambda *a, **k: {"email": "someone@else.com", "email_verified": True})
    assert _score(a.id).status_code == 403


# ---------- T008: success, idempotency, lease ----------

def test_success_marks_done_once_and_is_idempotent(make, db_session, monkeypatch, wiring):
    calls = []
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a: calls.append(1) or _real_result())
    a = make()
    r = _score(a.id)
    assert r.status_code == 200 and r.json() == {"result": "done"}
    row = _reload(db_session, a.id)
    assert row.status == "done" and row.scoring_completed_at and row.scoring_lease_until is None
    assert row.mentor_report_v2["insights"] and row.scoring_attempts == 1
    assert _score(a.id).json() == {"result": "already_done"}
    assert len(calls) == 1 and wiring["emails"] == [a.id]


def test_live_lease_returns_503_and_expired_lease_is_reclaimed(make, db_session, monkeypatch):
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a: _real_result())
    a = make(lease_until=_naive_now() + timedelta(minutes=10), attempts=1)
    r = _score(a.id)
    assert r.status_code == 503 and "leased" in r.json()["detail"]
    assert _reload(db_session, a.id).status == "processing"
    db_session.query(Assessment).filter_by(id=a.id).update({"scoring_lease_until": _naive_now() - timedelta(minutes=1)})
    db_session.commit()
    assert _score(a.id).json() == {"result": "done"}


def test_missing_assessment_is_not_retried():
    r = _score("does-not-exist")
    assert r.status_code == 200 and r.json() == {"result": "missing"}


# ---------- T009: retries, fallback, exhaustion ----------

def test_scorer_error_and_fallback_content_are_retried_not_done(make, db_session, monkeypatch, caplog, wiring):
    a = make()
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a: (_ for _ in ()).throw(RuntimeError("404 model")))
    assert _score(a.id).status_code == 503
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a: _fallback_result())
    with caplog.at_level(logging.ERROR):
        assert _score(a.id).status_code == 503
    row = _reload(db_session, a.id)
    assert row.status == "processing" and row.scoring_lease_until is None
    assert any("Failed to build mentor_blob" in r.getMessage() for r in caplog.records)
    assert wiring["emails"] == []


def test_exhausted_window_marks_failed_with_reason(make, db_session, monkeypatch, caplog, wiring):
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a: _fallback_result())
    a = make(queued_ago=timedelta(seconds=3550))
    with caplog.at_level(logging.ERROR):
        r = _score(a.id, retry=12)
    assert r.status_code == 200 and r.json()["result"] == "failed"
    row = _reload(db_session, a.id)
    assert row.status == "failed" and row.failure_reason == "AI provider unavailable"
    assert any(m.getMessage().startswith("scoring_failed assessment=") for m in caplog.records)
    assert wiring["emails"] == []


def test_requeued_old_assessment_gets_a_fresh_window(make, db_session, monkeypatch):
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a: _fallback_result())
    a = make(queued_ago=timedelta(seconds=10), created_ago=timedelta(days=2))
    assert _score(a.id, retry=3).status_code == 503
    assert _reload(db_session, a.id).status == "processing"


# ---------- T010: sweep and re-queue ----------

def test_sweep_requires_secret_and_handles_stuck(make, db_session, wiring):
    never_ran = make(queued_ago=timedelta(minutes=90), attempts=0)
    gave_up = make(queued_ago=timedelta(minutes=90), attempts=4)
    fresh = make(queued_ago=timedelta(minutes=5))
    old_failed = make(status="failed", queued_ago=timedelta(hours=7))
    assert client.post("/scheduled/scoring-sweep").status_code == 403
    body = client.post("/scheduled/scoring-sweep", headers=CRON).json()
    assert set(body["ids"]) == {never_ran.id, old_failed.id}
    assert body["marked_failed"] == [gave_up.id]
    assert _reload(db_session, gave_up.id).status == "failed"
    assert _reload(db_session, fresh.id).status == "processing"
    assert _reload(db_session, old_failed.id).status == "processing"


def test_requeue_endpoint_auth_and_selection(make, db_session, wiring):
    failed = make(status="failed", queued_ago=timedelta(hours=1))
    empty_done = make(status="done", blob={"insights": [], "strengths": []})
    good_done = make(status="done", blob=_real_result()["mentor_blob_v2"])

    admin = User(id=str(uuid4()), name="Admin", email=f"ad{uuid4().hex[:5]}@example.com", role="admin")
    mentor = User(id=str(uuid4()), name="M", email=f"m{uuid4().hex[:5]}@example.com", role="mentor")
    db_session.add_all([admin, mentor])
    db_session.commit()

    app.dependency_overrides[get_current_user_optional] = lambda: mentor
    assert client.post("/admin/assessments/requeue", json={"ids": [failed.id]}).status_code == 403
    app.dependency_overrides[get_current_user_optional] = lambda: None
    assert client.post("/admin/assessments/requeue", json={"ids": [failed.id]}).status_code == 403
    assert client.post("/admin/assessments/requeue", json={}, headers=CRON).status_code == 422

    app.dependency_overrides[get_current_user_optional] = lambda: admin
    since = (_naive_now() - timedelta(days=1)).isoformat()
    body = client.post("/admin/assessments/requeue",
                       json={"since": since, "include_done_fallback": True}).json()
    assert failed.id in body["ids"] and empty_done.id in body["ids"] and good_done.id not in body["ids"]
    row = _reload(db_session, failed.id)
    assert row.status == "processing" and row.failure_reason is None
    assert (_naive_now() - row.scoring_queued_at).total_seconds() < 60

    app.dependency_overrides.pop(get_current_user_optional, None)
    assert client.post("/admin/assessments/requeue", json={"ids": [good_done.id]}, headers=CRON).status_code == 200


# ---------- T011: status endpoint ----------

def test_status_reports_failed_reason_and_auth_codes(make, db_session):
    a = make(status="failed")
    db_session.query(Assessment).filter_by(id=a.id).update({"failure_reason": "AI provider unavailable"})
    db_session.commit()
    app.dependency_overrides[verify_token] = lambda: {"uid": a.apprentice_id}
    body = client.get(f"/assessments/{a.id}/status").json()
    assert body["status"] == "failed" and body["reason"] == "AI provider unavailable"
    app.dependency_overrides[verify_token] = lambda: {"uid": "stranger"}
    assert client.get(f"/assessments/{a.id}/status").status_code == 403
    assert client.get("/assessments/nope/status").status_code == 404


def test_status_reports_health_when_done(make):
    a = make(status="done", blob=_real_result()["mentor_blob_v2"])
    app.dependency_overrides[verify_token] = lambda: {"uid": a.apprentice_id}
    body = client.get(f"/assessments/{a.id}/status").json()
    assert body["status"] == "done" and body["health_score"] == 76 and "reason" not in body


# ---------- T012: submit enqueues ----------

def test_submit_enqueues_scoring(db_session, wiring):
    user = User(id=str(uuid4()), name="Jordan", email=f"s{uuid4().hex[:6]}@example.com", role="apprentice")
    template = AssessmentTemplate(id=str(uuid4()), name="Master T[root]H Assessment")
    draft = AssessmentDraft(id=str(uuid4()), apprentice_id=user.id, template_id=template.id,
                            answers={"q1": "I pray daily."}, is_submitted=False)
    db_session.add_all([user, template, draft])
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    r = client.post(f"/assessment-drafts/submit?draft_id={draft.id}")
    assert r.status_code == 200, r.text
    assessment_id = r.json()["id"]
    assert wiring["enqueued"] == [(assessment_id, "submit")]
    row = _reload(db_session, assessment_id)
    assert row.status == "processing" and row.scoring_queued_at is not None


# ---------------------------------------------------------------------------
# User Story 2: computed facts and the single-call v3 scorer
# ---------------------------------------------------------------------------
from types import SimpleNamespace

from app.services import ai_scoring, scoring_facts

V3_QUESTIONS = [
    {"id": "mc1", "text": "Who led Israel out of Egypt?", "category": "Bible Knowledge", "topic": "Pentateuch",
     "question_type": "multiple_choice",
     "options": [{"id": "o1", "text": "Moses", "is_correct": True}, {"id": "o2", "text": "David", "is_correct": False}]},
    {"id": "mc2", "text": "Who wrote most of the Psalms?", "category": "Bible Knowledge", "topic": "Wisdom",
     "question_type": "multiple_choice",
     "options": [{"id": "o3", "text": "David", "is_correct": True}, {"id": "o4", "text": "Paul", "is_correct": False}]},
    {"id": "mc3", "text": "Where was Jesus born?", "category": "Bible Knowledge", "topic": "Gospels",
     "question_type": "multiple_choice",
     "options": [{"id": "o5", "text": "Bethlehem", "is_correct": True}, {"id": "o6", "text": "Rome", "is_correct": False}]},
    {"id": "open1", "text": "Describe your prayer life.", "category": "Prayer Life", "question_type": "open_ended"},
]
V3_ANSWERS = {"mc1": "o1", "mc2": "o4", "mc3": "Bethlehem", "open1": "I pray most mornings.", "ghost": "o1"}


def _v3_response():
    return {
        "categories": [{"category": "Prayer Life", "level": "Maturing",
                        "observation": "Prays most mornings.", "next_step": "Add intercession."}],
        "open_feedback": [{"question_id": "open1", "feedback": "A steady rhythm."}],
        "strengths": ["Consistent morning prayer"], "gaps": ["Psalms"],
        "priority_action": {"title": "Pray for others", "description": "Widen your prayers.",
                            "steps": ["List five names"], "scripture": "1 Tim 2:1 - pray for all people"},
        "study_recommendation": "Read Psalms 1-20.",
        "flags": {"red": [], "yellow": [], "green": ["Faithful"]},
        "four_week_plan": {"rhythm": ["Week 1"], "checkpoints": ["Check 1"]},
        "conversation_starters": ["What do you pray about?"],
        "recommended_resources": [{"title": "Praying the Bible", "why": "Simple method", "type": "book"}],
    }


@pytest.fixture
def fake_llm(monkeypatch):
    calls, replies = [], []

    class _Svc:
        def generate(self, system_prompt, user_content, config=None):
            calls.append({"system": system_prompt, "user": user_content, "config": config})
            content = replies.pop(0) if replies else _v3_response()
            return SimpleNamespace(success=True, content=content, raw_response="", error=None,
                                   provider="gemini", model="m", total_tokens=1, estimated_cost_usd=0.0)

    monkeypatch.setattr(ai_scoring, "get_llm_service", lambda: _Svc())
    return SimpleNamespace(calls=calls, replies=replies)


def test_compute_facts_grades_mc_in_code():
    prev = [{"mentor_report_v2": {"health_score": 61, "health_band": "Stable", "biblical_knowledge": {"percent": 50}}}]
    facts = scoring_facts.compute(V3_ANSWERS, V3_QUESTIONS, prev)
    assert facts.biblical_knowledge_percent == 66.7  # mc1 by id, mc3 by legacy text; ghost id ignored
    assert facts.mc_by_category == [{"category": "Bible Knowledge", "correct": 2, "total": 3, "percent": 66.7}]
    assert {t["topic"]: t["percent"] for t in facts.mc_by_topic} == {"Pentateuch": 100.0, "Wisdom": 0.0, "Gospels": 100.0}
    assert facts.weak_topics == ["Wisdom"]
    assert facts.previous_health_score == 61
    assert facts.open_ended_count == 1
    assert "health_score" not in facts.for_ai() and "mc_results" not in facts.for_ai()


def test_category_scores_combine_mc_and_level():
    facts = scoring_facts.compute({"mc1": "o1", "mc2": "o3"}, [dict(q, category="Prayer Life") for q in V3_QUESTIONS[:2]])
    # 100% MC -> 10, Maturing -> 8: 10*0.6 + 8*0.4 = 9.2
    assert scoring_facts.category_scores(facts, {"Prayer Life": "Maturing", "Community": "Developing"}) == \
        {"Prayer Life": 9, "Community": 5}


def test_v3_scorer_makes_one_structured_call(fake_llm):
    result = ai_scoring.score_master_v3(V3_ANSWERS, V3_QUESTIONS, [])
    assert len(fake_llm.calls) == 1
    call = fake_llm.calls[0]
    assert call["config"].response_schema is ai_scoring.MentorReportV3
    assert "Health Score is computed by the system" in call["system"]
    sent = __import__("json").loads(call["user"])
    assert "Who led Israel" not in call["user"]  # correct MC answers aren't sent
    assert [q["question_id"] for q in sent["open_ended"]] == ["open1"]
    assert "health_score" not in sent["computed_facts"]

    assert result["scoring_version"] == "master_v3"
    assert result["category_scores"] == {"Bible Knowledge": 7, "Prayer Life": 8}
    blob = result["mentor_blob_v2"]
    # round(66.7*0.6 + 82*0.4) = 73
    assert (blob["health_score"], blob["health_band"]) == (73, "Maturing")
    assert blob["biblical_knowledge"]["percent"] == 66.7 and blob["insights"][0]["level"] == "Maturing"
    assert result["computed_facts"]["health_score"] == 73
    fb = {f["question_id"]: f for f in result["question_feedback"]}
    assert fb["mc2"]["correct"] is False and "David" in fb["mc2"]["explanation"]
    assert fb["open1"]["correct"] is None and fb["open1"]["explanation"] == "A steady rhythm."
    ai_scoring.MentorBlobV2.model_validate(blob)  # readers' v2.1 shape


def test_v3_no_open_ended_skips_ai(fake_llm):
    result = ai_scoring.score_master_v3({"mc1": "o1", "mc2": "o3"}, V3_QUESTIONS, [])
    assert fake_llm.calls == []
    assert result["mentor_blob_v2"]["health_score"] == 100 and result["mentor_blob_v2"]["insights"] == []


def test_v3_invalid_output_retries_once_then_raises(fake_llm):
    fake_llm.replies.extend([{"categories": "nope"}, _v3_response()])
    assert ai_scoring.score_master_v3(V3_ANSWERS, V3_QUESTIONS, [])["scoring_version"] == "master_v3"
    fake_llm.calls.clear()
    fake_llm.replies.extend([{"categories": "nope"}, {"strengths": 3}])
    with pytest.raises(ai_scoring.ReportGenerationError) as exc:
        ai_scoring.score_master_v3(V3_ANSWERS, V3_QUESTIONS, [])
    assert exc.value.code == "ai_invalid_output" and len(fake_llm.calls) == 2


def test_pipeline_uses_v3_for_master_and_retries_invalid_output(make, db_session, monkeypatch, fake_llm):
    a = make()
    monkeypatch.setattr(scoring_pipeline, "_build_questions", lambda s, x: V3_QUESTIONS)
    db_session.query(Assessment).filter_by(id=a.id).update({"answers": V3_ANSWERS})
    db_session.commit()
    fake_llm.replies.extend([{"bad": 1}, {"bad": 2}])
    r = _score(a.id)
    assert r.status_code == 503 and _reload(db_session, a.id).status == "processing"
    r = _score(a.id, retry=1)
    assert r.json() == {"result": "done"}
    a = _reload(db_session, a.id)
    assert a.scores["scoring_version"] == "master_v3" and a.mentor_report_v2["health_score"] == 73
