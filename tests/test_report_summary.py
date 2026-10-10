"""Report numbers agree everywhere: Health Score, Biblical Knowledge %, Premium report, no model name."""
import copy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.settings import settings
from app.main import app
from app.models import Assessment, User
from app.models.assessment_draft import AssessmentDraft
from app.models.mentor_apprentice import MentorApprentice
from app.services.auth import get_current_user
from app.services.report_summary import (
    apply_canonical_scores,
    compute_health_score,
    public_full_report,
    summarize_mentor_blob,
)

client = TestClient(app)


def _blob(**overrides):
    blob = {
        "health_score": 80,
        "health_band": "Maturing",
        "strengths": ["Consistent morning Psalm reading"],
        "gaps": ["Fear of sharing faith at work"],
        "priority_action": {"title": "Pray first under stress", "steps": ["Pause and pray"], "scripture": "Phil 4:6-7"},
        "biblical_knowledge": {"percent": 86.2, "weak_topics": ["Bible Study"], "study_recommendation": ""},
        "insights": [
            {"category": "Prayer Life", "level": "Stable", "observation": "o", "next_step": "n"},
            {"category": "Discipleship", "level": "Developing", "observation": "o", "next_step": "n"},
        ],
        "flags": {"red": [], "yellow": [], "green": []},
        "conversation_starters": ["What fears come up?"],
        "recommended_resources": [{"title": "Praying the Bible", "why": "w", "type": "book"}],
    }
    blob.update(overrides)
    return blob


def _full_report(health=81):
    return {
        "report_version": "premium_v1",
        "executive_summary": {"health_score": health, "health_band": "Maturing", "one_liner": "Teachable"},
        "_meta": {"generated_at": "2026-10-11T09:00:00Z", "provider": "gemini", "model": "gemini-3.5-flash",
                  "tokens_used": 9000, "cost_usd": 0.04, "latency_ms": 41000},
    }


# ---------- pure functions ----------

def test_health_score_formula_uses_mc_and_open_levels():
    # MC 86.2 * 0.6 = 51.72; open = avg(Stable 67, Developing 50) = 58.5 * 0.4 = 23.4 -> 75
    assert compute_health_score(86.2, _blob()["insights"]) == 75


def test_health_score_without_open_insights_is_mc_percent():
    assert compute_health_score(64.0, []) == 64
    assert compute_health_score(64.0, [{"level": "unknown"}]) == 64


def test_apply_canonical_scores_overrides_llm_numbers():
    blob = _blob(health_score=99, health_band="Flourishing", biblical_knowledge={"percent": 0.0})
    apply_canonical_scores(blob, 86.2)
    assert blob["biblical_knowledge"]["percent"] == 86.2
    assert blob["health_score"] == 75
    assert blob["health_band"] == "Maturing"


def test_summarize_reads_biblical_knowledge_for_v21_and_snapshot_for_legacy():
    v21 = summarize_mentor_blob(_blob())
    assert (v21["health_score"], v21["mc_percent"], v21["weak_topics"]) == (80, 86.2, ["Bible Study"])
    legacy = summarize_mentor_blob({"snapshot": {"overall_mc_percent": 72, "knowledge_band": "Average"}})
    assert (legacy["health_score"], legacy["mc_percent"], legacy["health_band"]) == (72, 72.0, "Average")
    assert summarize_mentor_blob(None)["health_score"] == 0


def test_public_full_report_aligns_health_and_hides_model_without_mutating():
    stored = _full_report(health=81)
    original = copy.deepcopy(stored)
    out = public_full_report(stored, _blob())
    assert out["executive_summary"]["health_score"] == 80
    assert out["_meta"] == {"generated_at": "2026-10-11T09:00:00Z"}
    assert stored == original


# ---------- endpoints ----------

@pytest.fixture
def people(db_session):
    mentor = User(id=str(uuid4()), name="Marcus", email=f"m{uuid4().hex[:6]}@example.com", role="mentor")
    apprentice = User(id=str(uuid4()), name="Jordan", email=f"a{uuid4().hex[:6]}@example.com", role="apprentice")
    db_session.add_all([mentor, apprentice,
                        MentorApprentice(mentor_id=mentor.id, apprentice_id=apprentice.id, active=True)])
    db_session.commit()
    yield mentor, apprentice
    app.dependency_overrides.pop(get_current_user, None)


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _assessment(db, apprentice, *, created, report=None):
    a = Assessment(id=str(uuid4()), apprentice_id=apprentice.id, template_id="master-template", answers={},
                   category="master_trooth", status="done", created_at=created,
                   scores={"overall_score": 7, "category_scores": {"Prayer Life": 7},
                           **({"full_report_v1": report} if report else {})},
                   mentor_report_v2=_blob())
    db.add(a)
    db.commit()
    return a


def test_apprentice_and_mentor_reports_agree(db_session, people):
    mentor, apprentice = people
    a = _assessment(db_session, apprentice, created=datetime.now(UTC))

    _as(apprentice)
    mine = client.get(f"/progress/reports/{a.id}/simplified").json()
    _as(mentor)
    theirs = client.get(f"/mentor/reports/{a.id}/simplified").json()

    assert mine["health_score"] == theirs["health_score"] == 80
    assert mine["mc_percent"] == theirs["mc_percent"] == 86.2  # was 0.0 for the apprentice
    assert mine["biblical_knowledge"]["percent"] == 86.2
    assert mine["resources"][0]["title"] == "Praying the Bible"  # was always empty


def test_mentor_list_and_progress_list_include_health_score(db_session, people):
    mentor, apprentice = people
    a = _assessment(db_session, apprentice, created=datetime.now(UTC))

    _as(mentor)
    rows = client.get(f"/mentor/apprentice/{apprentice.id}/submitted-assessments").json()
    assert rows[0]["health_score"] == 80 and rows[0]["health_band"] == "Maturing"

    _as(apprentice)
    items = client.get("/progress/reports").json()["items"]
    assert next(i for i in items if i["id"] == a.id)["summary"]["health_score"] == 80


def test_premium_report_uses_canonical_health_and_hides_model(db_session, people, monkeypatch):
    monkeypatch.setattr(settings, "premium_features_enabled", True)
    mentor, apprentice = people
    a = _assessment(db_session, apprentice, created=datetime.now(UTC), report=_full_report(health=81))
    db_session.add(AssessmentDraft(id=str(uuid4()), apprentice_id=apprentice.id, template_id="master-template",
                                   answers={}, is_submitted=True))
    db_session.commit()

    _as(apprentice)
    for path in (f"/assessments/{a.id}/my-full-report", f"/apprentice/my-assessments/{a.id}/full-report"):
        report = client.get(path).json()["report"]
        assert report["executive_summary"]["health_score"] == 80, path
        assert "model" not in report["_meta"] and "provider" not in report["_meta"], path

    _as(mentor)
    report = client.get(f"/mentor/submitted-drafts/{a.id}/full-report").json()["report"]
    assert report["executive_summary"]["health_score"] == 80
    assert "model" not in report["_meta"]


def test_older_assessment_gets_its_own_premium_report(db_session, people, monkeypatch):
    """The draft cache is per template; an older assessment must not show the newest report."""
    monkeypatch.setattr(settings, "premium_features_enabled", True)
    _, apprentice = people
    older_report = _full_report()
    older_report["executive_summary"]["one_liner"] = "older"
    older = _assessment(db_session, apprentice, created=datetime.now(UTC) - timedelta(days=30), report=older_report)
    newer_report = _full_report()
    newer_report["executive_summary"]["one_liner"] = "newer"
    db_session.add(AssessmentDraft(id=str(uuid4()), apprentice_id=apprentice.id, template_id="master-template",
                                   answers={}, is_submitted=True, score={"full_report_v1": newer_report}))
    db_session.commit()

    _as(apprentice)
    report = client.get(f"/assessments/{older.id}/my-full-report").json()["report"]
    assert report["executive_summary"]["one_liner"] == "older"


def test_submitted_assessments_requires_relationship(db_session, people):
    mentor, apprentice = people
    stranger = User(id=str(uuid4()), name="Stranger", email=f"s{uuid4().hex[:6]}@example.com", role="mentor")
    db_session.add(stranger)
    db_session.commit()

    _as(stranger)
    assert client.get(f"/assessment-drafts/submitted-assessments/{apprentice.id}").status_code == 403
    _as(mentor)
    assert client.get(f"/assessment-drafts/submitted-assessments/{apprentice.id}").status_code == 200
    _as(apprentice)
    assert client.get(f"/assessment-drafts/submitted-assessments/{apprentice.id}").status_code == 200


def test_premium_report_email_shows_canonical_health_score():
    """The mentor email reads Health Score from the blob, not the LLM's executive summary."""
    from app.services.email import render_premium_report_email
    from app.services.master_trooth_report import build_report_context

    scores = {"overall_score": 7, "category_scores": {"Prayer Life": 7}, "full_report_v1": _full_report(health=81)}
    context = build_report_context({"apprentice": {"name": "Jordan"}}, scores, _blob())
    assert (context["health_score"], context["full_report"]["executive_summary"]["health_score"]) == (80, 80)

    html, plain = render_premium_report_email(context, scores["full_report_v1"])
    assert ">80<" in html.replace(" ", "") and ">81<" not in html.replace(" ", "")
    assert "gemini" not in html.lower()
