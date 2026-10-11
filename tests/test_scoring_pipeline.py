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
from unittest.mock import ANY

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
    # ~28 open-ended answers: reasoning tokens share the output limit, so keep them low
    assert call["config"].thinking_level == "low" and call["config"].max_tokens >= 16000
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


# ---------------------------------------------------------------------------
# User Story 3: the narrative matches the numbers; Premium gets the same facts
# ---------------------------------------------------------------------------

def _facts(previous=None):
    prev = [{"mentor_report_v2": {"health_score": previous}}] if previous is not None else []
    return scoring_facts.compute(V3_ANSWERS, V3_QUESTIONS, prev)


def test_narrative_check_flags_invented_numbers():
    facts = _facts()  # Biblical Knowledge 66.7%; topics 100 / 0 / 100
    ok = {"observation": "You scored 66.7% on Biblical Knowledge (about 67%) and 100% on the Pentateuch.",
          "next_step": "Pray for five minutes each morning to improve your focus."}
    assert scoring_facts.narrative_numbers_ok(ok, facts) == []
    bad = {"observation": "An 11-point improvement from a 70% baseline.",
           "items": ["Your prayer life has improved since your last assessment."]}
    problems = scoring_facts.narrative_numbers_ok(bad, facts)
    assert any("70%" in p for p in problems) and any("11-point" in p for p in problems)
    assert any("has improved" in p for p in problems) and any("since your last" in p for p in problems)
    # With a previous assessment, comparisons are allowed (numbers still must come from the facts)
    assert scoring_facts.narrative_numbers_ok({"t": "Your prayer life has improved since 61%."}, _facts(61)) == []


def test_v3_regenerates_once_when_numbers_are_invented(fake_llm, caplog):
    bad = _v3_response()
    bad["strengths"] = ["A 12-point jump from 70% last time"]
    fake_llm.replies.extend([bad, _v3_response()])
    result = ai_scoring.score_master_v3(V3_ANSWERS, V3_QUESTIONS, [], assessment_id="a1")
    assert len(fake_llm.calls) == 2 and "## CORRECTION" in fake_llm.calls[1]["system"]
    assert result["mentor_blob_v2"]["strengths"] == ["Consistent morning prayer"]

    fake_llm.calls.clear()
    fake_llm.replies.extend([bad, bad])
    with caplog.at_level(logging.WARNING):
        result = ai_scoring.score_master_v3(V3_ANSWERS, V3_QUESTIONS, [], assessment_id="a2")
    assert len(fake_llm.calls) == 2 and result["scoring_version"] == "master_v3"  # accepted, not failed
    assert "report_number_mismatch assessment=a2" in caplog.text


def _premium_fixture(health=99, overall=50.0):
    phase = {"goal": "g", "activities": ["a"], "success_metric": "m"}
    session = {"theme": "t", "duration_minutes": 45, "key_points_to_cover": [{"point": "p", "talking_point": "tp"}],
               "questions_to_ask": ["q"]}
    return {
        "executive_summary": {"health_score": health, "health_band": "Flourishing", "one_liner": "o",
                              "trajectory": "steady", "trajectory_note": "n"},
        "strengths_deep_dive": [{"area": "Prayer Life", "summary": "s", "evidence": ["e"],
                                 "spiritual_maturity_indicator": "i", "how_to_leverage": "h",
                                 "celebration_talking_point": "c"}],
        "gaps_deep_dive": [{"area": "Evangelism", "summary": "s", "severity": "moderate", "root_cause_analysis": "r",
                            "evidence": ["e"], "biblical_perspective": "b", "why_it_matters": "w",
                            "growth_pathway": {"phase_1_weeks_1_4": phase, "phase_2_weeks_5_8": phase,
                                               "phase_3_weeks_9_12": phase}}],
        "biblical_knowledge_analysis": {
            "overall_percent": overall, "mastery_level": "Intermediate",
            "by_topic_breakdown": [{"topic": "Wisdom", "score_percent": 80, "level": "Strong", "key_gaps": []}],
            "theological_health_check": {"core_doctrines_solid": ["Trinity"], "areas_needing_clarification": [],
                                         "potential_concerns": []},
            "recommended_bible_reading_plan": {"name": "n", "description": "d", "why_this_plan": "w",
                                               "chapters_per_day": 3}},
        "spiritual_formation_insights": [{"category": "Prayer Life", "current_level": "Maturing",
                                          "detailed_observation": "d", "maturity_markers_present": ["c"],
                                          "maturity_markers_missing": ["f"],
                                          "custom_development_plan": {"immediate_30_days": "i", "quarter_goal": "q",
                                                                      "year_vision": "y"},
                                          "mentor_discussion_questions": ["q"]}],
        "conversation_guide": {"session_1_opening": session, "session_2_growth_areas": session,
                               "session_3_check_in": session},
        "progress_tracking": {"milestones_to_track": [{"milestone": "m", "expected_by": "Week 2",
                                                       "how_to_verify": "v"}],
                              "suggested_reassessment": "3 months"},
        "personalized_resources": [{"title": "Praying the Bible", "type": "book", "why_specifically_for_them": "w",
                                    "how_to_use": "h"}],
        "mentor_preparation_notes": {"handle_with_care": "h", "watch_for": "w", "cultural_considerations": "c",
                                     "prayer_focus_for_this_apprentice": "p"},
        "flags": {"red": [], "yellow": [], "green": [{"flag": "f", "detail": "d", "leverage_this": "l"}]},
    }


def test_premium_generation_uses_schema_and_computed_facts(monkeypatch, fake_llm):
    fake_llm.replies.append(_premium_fixture(health=99, overall=50.0))
    monkeypatch.setattr(ai_scoring, "_load_full_report_prompt_text", lambda: "PREMIUM PROMPT")
    facts = {"health_score": 73, "health_band": "Maturing", "biblical_knowledge_percent": 66.7,
             "mc_by_topic": [{"topic": "Wisdom", "correct": 0, "total": 1, "percent": 0.0}]}
    report = ai_scoring.generate_full_report({"assessment": {}}, None, computed_facts=facts)
    call = fake_llm.calls[0]
    assert call["config"].response_schema is ai_scoring.PremiumReportV1 and call["config"].thinking_level == "low"
    assert "PREMIUM PROMPT" in call["system"] and "PREMIUM PROMPT" not in call["user"]  # cacheable instructions
    assert '"computed_facts": {"health_score": 73' in call["user"]
    assert "must equal computed_facts.health_score" in call["system"]
    assert ai_scoring.NUMBERS_INSTRUCTION in call["system"]
    # Headline numbers come from code even if the model drifts
    assert (report["executive_summary"]["health_score"], report["executive_summary"]["health_band"]) == (73, "Maturing")
    bk = report["biblical_knowledge_analysis"]
    assert bk["overall_percent"] == 66.7 and bk["by_topic_breakdown"][0]["score_percent"] == 0.0
    assert report["report_version"] == "premium_v1" and report["generated_at"]
    assert report["progress_tracking"]["previous_assessment_comparison"] is None


def test_premium_output_failing_schema_raises_for_retry(monkeypatch, fake_llm):
    fake_llm.replies.append({"executive_summary": {"health_score": 73}})  # e.g. the JSON-mode fallback
    monkeypatch.setattr(ai_scoring, "_load_full_report_prompt_text", lambda: "PREMIUM PROMPT")
    with pytest.raises(ValueError, match="schema validation"):
        ai_scoring.generate_full_report({"assessment": {}}, None)


# ---------------------------------------------------------------------------
# User Story 4: Premium generated once in the scoring task; on-demand claimed once, never a 500
# ---------------------------------------------------------------------------
from app.core.settings import settings
from app.services import full_report

PREMIUM = {"executive_summary": {"health_score": 99, "health_band": "Flourishing", "summary": "s"},
           "_meta": {"generated_at": "2026-10-11T00:00:00Z", "model": "m"}}


@pytest.fixture
def premium_gen(monkeypatch):
    """Count Premium generations; queue exceptions to raise."""
    state = SimpleNamespace(calls=0, errors=[], facts=[])

    def gen(payload, previous=None, computed_facts=None):
        state.calls += 1
        state.facts.append(computed_facts)
        if state.errors:
            raise state.errors.pop(0)
        return dict(PREMIUM)

    monkeypatch.setattr(ai_scoring, "generate_full_report", gen)
    monkeypatch.setattr(full_report, "_sleep", lambda s: None)
    return state


def _premium(db_session, a, on=True):
    user = db_session.get(User, a.apprentice_id)
    user.subscription_tier = "apprentice_premium" if on else "free"
    db_session.commit()
    return user


def test_pipeline_generates_premium_before_the_mentor_email(make, db_session, monkeypatch, premium_gen, wiring):
    a = make()
    _premium(db_session, a)
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a, **k: {**_real_result(), "computed_facts": {"health_score": 76}})
    seen = []
    monkeypatch.setattr(scoring_pipeline, "notify_mentors",
                        lambda s, x, *r: seen.append((x.full_report_status, bool((x.scores or {}).get("full_report_v1")))))
    assert _score(a.id).json() == {"result": "done"}
    a = _reload(db_session, a.id)
    assert a.full_report_status == "ready" and a.scores["full_report_v1"]["executive_summary"]["summary"] == "s"
    assert premium_gen.calls == 1 and premium_gen.facts == [{"health_score": 76}]
    assert seen == [("ready", True)]  # email went out once, after the Premium step


def test_pipeline_premium_failure_keeps_report_done(make, db_session, monkeypatch, premium_gen, wiring):
    a = make()
    _premium(db_session, a)
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a, **k: _real_result())
    premium_gen.errors.extend([ValueError("Could not parse JSON")] * 3)
    assert _score(a.id).json() == {"result": "done"}
    a = _reload(db_session, a.id)
    assert a.status == "done" and a.full_report_status == "failed" and premium_gen.calls == 3
    assert wiring["emails"] == [a.id]  # the free email still goes out


def test_pipeline_skips_premium_when_nobody_is_premium(make, db_session, monkeypatch, premium_gen):
    a = make()
    monkeypatch.setattr(scoring_pipeline, "_run_scorer", lambda *a, **k: _real_result())
    assert _score(a.id).json() == {"result": "done"}
    assert premium_gen.calls == 0 and _reload(db_session, a.id).full_report_status is None


def _done_with_draft(make, db_session, status="done"):
    a = make(status=status, blob=_real_result()["mentor_blob_v2"])
    a.template_id = "master-template"
    db_session.add(AssessmentDraft(id=str(uuid4()), apprentice_id=a.apprentice_id, template_id="master-template",
                                   answers={}, is_submitted=True))
    db_session.commit()
    return a


def _get_full(aid):
    return client.get(f"/assessments/{aid}/my-full-report")


def test_on_demand_generates_once_then_serves_stored(make, db_session, premium_gen):
    a = _done_with_draft(make, db_session)
    user = _premium(db_session, a)
    app.dependency_overrides[get_current_user] = lambda: user
    first = _get_full(a.id).json()
    assert first["cached"] is False and first["report"]["executive_summary"]["health_score"] == 76  # canonical
    assert "model" not in first["report"]["_meta"]
    second = _get_full(a.id).json()
    assert second["cached"] is True and premium_gen.calls == 1


def test_on_demand_waits_for_a_live_claim_and_reclaims_a_stale_one(make, db_session, premium_gen, monkeypatch):
    a = _done_with_draft(make, db_session)
    user = _premium(db_session, a)
    app.dependency_overrides[get_current_user] = lambda: user
    db_session.query(Assessment).filter_by(id=a.id).update(
        {"full_report_status": "generating", "full_report_claimed_at": _naive_now()})
    db_session.commit()

    # The other caller stores the report while we wait
    def finish(_s):
        db_session.query(Assessment).filter_by(id=a.id).update(
            {"scores": {"full_report_v1": PREMIUM}, "full_report_status": "ready"})
        db_session.commit()
    monkeypatch.setattr(full_report, "_sleep", finish)
    assert _get_full(a.id).json()["cached"] is True and premium_gen.calls == 0

    # Still generating after the wait -> "generating", no report key
    db_session.query(Assessment).filter_by(id=a.id).update(
        {"scores": {}, "full_report_status": "generating", "full_report_claimed_at": _naive_now()})
    db_session.commit()
    monkeypatch.setattr(full_report, "_sleep", lambda s: None)
    monkeypatch.setattr(full_report, "_clock", iter([0, 0, 1000, 1000]).__next__)
    assert _get_full(a.id).json() == {"status": "generating", "cached": False, "draft_id": ANY}

    # A claim older than 5 minutes is taken over
    db_session.query(Assessment).filter_by(id=a.id).update(
        {"full_report_claimed_at": _naive_now() - timedelta(minutes=6)})
    db_session.commit()
    monkeypatch.undo()
    monkeypatch.setattr(ai_scoring, "generate_full_report", lambda *a, **k: dict(PREMIUM))
    assert _get_full(a.id).json()["cached"] is False


def test_on_demand_failure_is_503_on_all_endpoints_and_premium_gate_unchanged(make, db_session, premium_gen):
    a = _done_with_draft(make, db_session)
    user = _premium(db_session, a)
    mentor = User(id=str(uuid4()), name="Marcus", email=f"m{uuid4().hex[:6]}@example.com", role="mentor",
                  subscription_tier="mentor_premium")
    db_session.add_all([mentor, MentorApprentice(mentor_id=mentor.id, apprentice_id=user.id, active=True)])
    db_session.commit()
    premium_gen.errors.extend([ValueError("Could not parse JSON from LLM response")] * 9)
    paths = [(user.id, f"/assessments/{a.id}/my-full-report"), (user.id, f"/apprentice/my-assessments/{a.id}/full-report"),
             (mentor.id, f"/mentor/submitted-drafts/{a.id}/full-report")]
    for uid, path in paths:
        app.dependency_overrides[get_current_user] = lambda uid=uid: db_session.get(User, uid)
        r = client.get(path)
        assert r.status_code == 503 and r.json()["detail"] == "Report is temporarily unavailable", path
    assert premium_gen.calls == 9 and _reload(db_session, a.id).full_report_status == "failed"

    _premium(db_session, a, on=False)
    app.dependency_overrides[get_current_user] = lambda: db_session.get(User, a.apprentice_id)
    assert _get_full(a.id).status_code == 403


def test_on_demand_while_scoring_reports_generating(make, db_session, premium_gen):
    a = _done_with_draft(make, db_session, status="processing")
    user = _premium(db_session, a)
    app.dependency_overrides[get_current_user] = lambda: user
    assert _get_full(a.id).json()["status"] == "generating" and premium_gen.calls == 0
