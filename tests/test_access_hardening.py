"""Access checks: answer visibility, ended mentorships, profile lookup, draft access, question edits."""
import uuid
from datetime import UTC, datetime

import pytest

from app.main import app
from app.models.assessment import Assessment
from app.models.assessment_template import AssessmentTemplate
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.mentor_apprentice import MentorApprentice
from app.models.question import Question, QuestionOption, QuestionType
from app.models.user import User
from app.services.auth import get_current_user


@pytest.fixture
def act_as():
    def _set(user):
        app.dependency_overrides[get_current_user] = lambda: user
    yield _set
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def make_user(db_session):
    def _make(role):
        u = User(id=str(uuid.uuid4()), name=f"{role} {uuid.uuid4().hex[:4]}",
                 email=f"{role}+{uuid.uuid4().hex[:8]}@example.com", role=role, created_at=datetime.now(UTC))
        db_session.add(u)
        db_session.commit()
        return u
    return _make


@pytest.fixture
def mc_question(db_session):
    q = Question(text="How many days of creation?", question_type=QuestionType.multiple_choice)
    db_session.add(q)
    db_session.flush()
    db_session.add_all([QuestionOption(question_id=q.id, option_text="6", is_correct=True, order=1),
                        QuestionOption(question_id=q.id, option_text="7", is_correct=False, order=2)])
    db_session.commit()
    return q


def _template(db, question, **kw):
    t = AssessmentTemplate(name=f"T {uuid.uuid4().hex[:4]}", **kw)
    db.add(t)
    db.flush()
    db.add(AssessmentTemplateQuestion(template_id=t.id, question_id=question.id, order=1))
    db.commit()
    return t


def _options(payload):
    return [o for q in payload for o in q.get("options", [])]


# ---------- answers are never exposed to non-admins ----------

def test_question_bank_requires_sign_in(client, mc_question):
    app.dependency_overrides.pop(get_current_user, None)
    assert client.get("/question/questions").status_code == 401
    assert client.get(f"/question/questions/{mc_question.id}").status_code == 401


@pytest.mark.parametrize("role", ["apprentice", "mentor"])
def test_question_bank_hides_answers_from_non_admins(client, act_as, make_user, mc_question, role):
    act_as(make_user(role))
    opts = _options(client.get("/question/questions").json())
    assert opts and all("is_correct" not in o for o in opts)
    assert all("is_correct" not in o for o in client.get(f"/question/questions/{mc_question.id}").json()["options"])


def test_question_bank_shows_answers_to_admins(client, act_as, make_user, mc_question):
    act_as(make_user("admin"))
    opts = _options(client.get("/question/questions").json())
    assert {o["option_text"]: o["is_correct"] for o in opts} == {"6": True, "7": False}


def test_category_creation_is_admin_only(client, act_as, make_user):
    app.dependency_overrides.pop(get_current_user, None)
    assert client.post("/question/categories", json={"name": "Anon"}).status_code == 401
    act_as(make_user("mentor"))
    assert client.post("/question/categories", json={"name": "Mentor cat"}).status_code == 403
    act_as(make_user("admin"))
    assert client.post("/question/categories", json={"name": "Admin cat"}).status_code == 200


def test_apprentice_draft_has_no_answers(client, db_session, act_as, make_user, mc_question):
    tpl = _template(db_session, mc_question, is_published=True, key="master_trooth_v2")
    act_as(make_user("apprentice"))
    r = client.post(f"/assessment-drafts/start?template_id={tpl.id}")
    assert r.status_code == 200, r.text
    opts = _options(r.json()["questions"])
    assert opts and all(o.get("is_correct") is None for o in opts)


def test_master_template_view_hides_answers_from_other_mentors(client, db_session, act_as, make_user, mc_question):
    master = _template(db_session, mc_question, is_master_assessment=True, is_published=True)
    act_as(make_user("mentor"))
    r = client.get(f"/admin/templates/{master.id}")
    assert r.status_code == 200, r.text
    # False rather than omitted: released apps read this field as a non-null bool
    assert all(o.get("is_correct") is False for o in _options(r.json()["questions"]))

    owner = make_user("mentor")
    own = _template(db_session, mc_question, created_by=owner.id)
    act_as(owner)
    opts = _options(client.get(f"/admin/templates/{own.id}").json()["questions"])
    assert {o["option_text"]: o["is_correct"] for o in opts} == {"6": True, "7": False}


# ---------- ended mentorships lose access ----------

def test_ended_mentorship_loses_access(client, db_session, act_as, make_user):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    db_session.add(MentorApprentice(mentor_id=mentor.id, apprentice_id=apprentice.id, active=False))
    a = Assessment(apprentice_id=apprentice.id, answers={}, scores={}, mentor_report_v2={"health_score": 50})
    db_session.add(a)
    db_session.commit()
    act_as(mentor)

    assert client.get(f"/mentor/apprentice/{apprentice.id}/submitted-assessments").status_code == 403
    assert client.get(f"/mentor/my-apprentices/{apprentice.id}").status_code in (403, 404)

    # Routes that authenticate with the raw Firebase token
    from app.services.auth import verify_token
    app.dependency_overrides[verify_token] = lambda: {"uid": mentor.id}
    try:
        assert client.get(f"/assessments/{a.id}/mentor-report-v2").status_code == 403
        assert client.get(f"/assessments/{a.id}/mentor-report-v2.pdf").status_code == 403
        listed = client.get("/assessments/list").json()
        assert client.get(f"/assessments/{a.id}").status_code == 403
        assert isinstance(listed, list) and all(x.get("apprentice_id") != apprentice.id for x in listed)
    finally:
        app.dependency_overrides.pop(verify_token, None)


def test_active_mentorship_keeps_access(client, db_session, act_as, make_user):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    db_session.add(MentorApprentice(mentor_id=mentor.id, apprentice_id=apprentice.id, active=True))
    db_session.commit()
    act_as(mentor)
    assert client.get(f"/mentor/apprentice/{apprentice.id}/submitted-assessments").status_code == 200


# ---------- profile lookup ----------

def test_profile_lookup_is_limited(client, db_session, act_as, make_user):
    me, stranger, linked = make_user("mentor"), make_user("apprentice"), make_user("apprentice")
    db_session.add(MentorApprentice(mentor_id=me.id, apprentice_id=linked.id, active=True))
    db_session.commit()
    act_as(me)
    assert client.get("/users/me").json()["id"] == me.id
    assert client.get(f"/users/{me.id}").status_code == 200
    assert client.get(f"/users/{linked.id}").status_code == 200
    r = client.get(f"/users/{stranger.id}")
    assert r.status_code == 404 and stranger.email not in r.text
    act_as(make_user("admin"))
    assert client.get(f"/users/{stranger.id}").status_code == 200


# ---------- new drafts follow /start's rules ----------

def test_new_draft_requires_published_template(client, db_session, act_as, make_user, mc_question):
    unpublished = _template(db_session, mc_question, is_published=False, key="master_trooth_v2")
    act_as(make_user("apprentice"))
    assert client.post("/assessment-drafts", json={"template_id": unpublished.id, "answers": {}}).status_code == 404


def test_new_draft_requires_premium_for_locked_template(client, db_session, act_as, make_user, mc_question):
    locked = _template(db_session, mc_question, is_published=True, key="premium_only_v1")
    act_as(make_user("apprentice"))
    r = client.post("/assessment-drafts", json={"template_id": locked.id, "answers": {}})
    assert r.status_code == 403


# ---------- shared questions can only be changed by admins ----------

def test_question_edit_and_delete_are_admin_only(client, act_as, make_user, mc_question):
    act_as(make_user("mentor"))
    assert client.put(f"/question/questions/{mc_question.id}", json={"text": "Changed"}).status_code == 403
    assert client.delete(f"/question/questions/{mc_question.id}").status_code == 403
    act_as(make_user("admin"))
    assert client.put(f"/question/questions/{mc_question.id}", json={"text": "Changed"}).status_code == 200
