"""specs/010-question-ownership: creators, edit rights, answer visibility, clone, drafts."""
import uuid
from datetime import UTC, datetime

import pytest

from app.main import app
from app.models.assessment_draft import AssessmentDraft
from app.models.assessment_template import AssessmentTemplate
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.mentor_apprentice import MentorApprentice
from app.models.question import Question, QuestionOption, QuestionType
from app.models.user import User
from app.services.auth import get_current_user
from app.services.question_access import can_see_answers, manage_block_reason


# ---------- fixtures (T001) ----------

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
def make_question(db_session):
    def _make(creator=None):
        q = Question(text=f"Q {uuid.uuid4().hex[:4]}", question_type=QuestionType.multiple_choice,
                     created_by=creator.id if creator else None)
        db_session.add(q)
        db_session.flush()
        db_session.add_all([QuestionOption(question_id=q.id, option_text="A", is_correct=True, order=1),
                            QuestionOption(question_id=q.id, option_text="B", is_correct=False, order=2)])
        db_session.commit()
        return q
    return _make


@pytest.fixture
def make_template(db_session):
    def _make(owner=None, master=False, published=False, questions=(), key=None):
        t = AssessmentTemplate(name=f"T {uuid.uuid4().hex[:4]}", created_by=owner.id if owner else None,
                               is_master_assessment=master, is_published=published, key=key)
        db_session.add(t)
        db_session.flush()
        for i, q in enumerate(questions, 1):
            db_session.add(AssessmentTemplateQuestion(template_id=t.id, question_id=q.id, order=i))
        db_session.commit()
        return t
    return _make


def _flags(options):
    # question routes use option_text; draft payloads use text
    return {(o.get("option_text") or o.get("text")): o.get("is_correct") for o in options}


def _template_flags(client, template_id):
    r = client.get(f"/admin/templates/{template_id}")
    assert r.status_code == 200, r.text
    return [_flags(q["options"]) for q in r.json()["questions"]]


# ---------- policy (T006) ----------

def test_policy(db_session, make_user, make_question, make_template):
    admin, mentor, other = make_user("admin"), make_user("mentor"), make_user("mentor")
    own_q, shared_q = make_question(mentor), make_question(None)
    make_template(owner=mentor, questions=[own_q])

    assert can_see_answers(admin, shared_q) and can_see_answers(mentor, own_q)
    assert not can_see_answers(mentor, shared_q) and not can_see_answers(other, own_q)

    assert manage_block_reason(db_session, admin, shared_q) is None
    assert manage_block_reason(db_session, mentor, own_q) is None
    assert manage_block_reason(db_session, mentor, shared_q) == "not_owner"
    assert manage_block_reason(db_session, other, own_q) == "not_owner"
    make_template(owner=other, questions=[own_q])
    assert manage_block_reason(db_session, mentor, own_q) == "used_elsewhere"


# ---------- US1: mentors manage their own questions (T009) ----------

def test_mentor_full_lifecycle_of_own_question(client, db_session, act_as, make_user, make_template):
    mentor = make_user("mentor")
    tpl = make_template(owner=mentor)
    act_as(mentor)

    created = client.post("/question/questions", json={
        "text": "My question", "question_type": "multiple_choice",
        "options": [{"option_text": "Yes", "is_correct": True, "order": 1},
                    {"option_text": "No", "is_correct": False, "order": 2}]})
    assert created.status_code == 200, created.text
    qid = created.json()["id"]
    assert created.json()["created_by"] == mentor.id
    # The database requires a unique question_code; custom questions get one generated
    assert db_session.get(Question, qid).question_code.startswith("QC")

    assert client.post(f"/admin/templates/{tpl.id}/questions", json={"question_id": qid, "order": 1}).status_code == 200
    assert _template_flags(client, tpl.id) == [{"Yes": True, "No": False}]
    assert _flags(client.get(f"/question/questions/{qid}").json()["options"]) == {"Yes": True, "No": False}

    assert client.put(f"/question/questions/{qid}", json={"text": "Edited"}).status_code == 200
    assert client.delete(f"/question/questions/{qid}").status_code == 200
    assert db_session.get(Question, qid) is None


def test_admin_created_questions_are_shared(client, act_as, make_user):
    act_as(make_user("admin"))
    r = client.post("/question/questions", json={"text": "Shared", "question_type": "open_ended"})
    assert r.status_code == 200 and r.json()["created_by"] is None


# ---------- US2: shared questions protected and private (T011) ----------

def test_shared_questions_protected_and_private(client, db_session, act_as, make_user, make_question, make_template):
    mentor = make_user("mentor")
    shared = make_question(None)
    master = make_template(master=True, published=True, questions=[shared])
    own = make_template(owner=mentor)
    act_as(mentor)

    assert client.put(f"/question/questions/{shared.id}", json={"text": "Hacked"}).status_code == 403
    assert client.delete(f"/question/questions/{shared.id}").status_code == 403
    db_session.expire_all()
    assert db_session.get(Question, shared.id).text != "Hacked"

    assert _template_flags(client, master.id) == [{"A": False, "B": False}]
    assert client.post(f"/admin/templates/{own.id}/questions",
                       json={"question_id": shared.id, "order": 1}).status_code == 403

    listed = {q["id"]: q for q in client.get("/question/questions").json()}
    assert all("is_correct" not in o for o in listed[shared.id]["options"])


def test_clone_keeps_scoring_inputs_but_hides_answers(client, db_session, act_as, make_user, make_question, make_template):
    mentor = make_user("mentor")
    shared = make_question(None)
    master = make_template(master=True, published=True, questions=[shared])
    act_as(mentor)

    r = client.post(f"/admin/templates/{master.id}/clone")
    assert r.status_code == 200, r.text
    clone_id = r.json()["id"]
    # Same question rows -> identical server-side scoring (SC-004)
    linked = [l.question_id for l in db_session.query(AssessmentTemplateQuestion).filter_by(template_id=clone_id)]
    assert linked == [shared.id]
    assert db_session.get(Question, shared.id).created_by is None
    # The mentor owns the clone but not the questions -> answers stay hidden
    assert _template_flags(client, clone_id) == [{"A": False, "B": False}]


def test_admin_sees_and_edits_everything(client, act_as, make_user, make_question, make_template):
    shared = make_question(None)
    master = make_template(master=True, questions=[shared])
    act_as(make_user("admin"))
    assert _template_flags(client, master.id) == [{"A": True, "B": False}]
    assert client.put(f"/question/questions/{shared.id}", json={"text": "Fixed typo"}).status_code == 200


# ---------- US3: nobody sees answers while taking (T013) ----------

def test_mentor_taking_an_assessment_gets_no_answers(client, act_as, make_user, make_question, make_template):
    shared = make_question(None)
    tpl = make_template(published=True, questions=[shared], key="master_trooth_v2")
    act_as(make_user("mentor"))
    r = client.post(f"/assessment-drafts/start?template_id={tpl.id}")
    assert r.status_code == 200, r.text
    assert all(o.get("is_correct") is None for q in r.json()["questions"] for o in q["options"])


def test_linked_mentor_reviewing_sees_answers_apprentice_does_not(client, db_session, act_as, make_user, make_question, make_template):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    db_session.add(MentorApprentice(mentor_id=mentor.id, apprentice_id=apprentice.id, active=True))
    q = make_question(None)
    tpl = make_template(published=True, questions=[q], key="master_trooth_v2")
    db_session.add(AssessmentDraft(apprentice_id=apprentice.id, template_id=tpl.id, answers={q.id: "A"}, is_submitted=True))
    db_session.commit()

    act_as(mentor)
    r = client.get(f"/assessment-drafts/submitted-assessments/{apprentice.id}")
    assert r.status_code == 200, r.text
    assert _flags(r.json()[0]["questions"][0]["options"]) == {"A": True, "B": False}

    act_as(apprentice)
    r = client.get(f"/assessment-drafts/submitted-assessments/{apprentice.id}")
    assert r.status_code == 200, r.text
    assert all(o.get("is_correct") is None for o in r.json()[0]["questions"][0]["options"])


# ---------- US4: never change someone else's assessment (T014) ----------

def test_creator_cannot_change_a_question_others_use(client, act_as, make_user, make_question, make_template):
    mentor, other = make_user("mentor"), make_user("mentor")
    q = make_question(mentor)
    make_template(owner=mentor, questions=[q])
    make_template(owner=other, questions=[q])
    act_as(mentor)
    r = client.put(f"/question/questions/{q.id}", json={"text": "Changed"})
    assert r.status_code == 409 and "used by other assessments" in r.json()["detail"]
    assert client.delete(f"/question/questions/{q.id}").status_code == 409
    act_as(make_user("admin"))
    assert client.put(f"/question/questions/{q.id}", json={"text": "Changed"}).status_code == 200


# ---------- account deletion (T015) ----------

def test_deleting_a_mentor_makes_their_questions_shared(db_session, make_user, make_question, make_template):
    from app.services.account_deletion import delete_user_account

    mentor = make_user("mentor")
    q = make_question(mentor)
    tpl = make_template(owner=mentor, questions=[q])
    delete_user_account(db_session, mentor)
    db_session.expire_all()
    assert db_session.get(Question, q.id).created_by is None
    assert db_session.query(AssessmentTemplateQuestion).filter_by(template_id=tpl.id).count() == 1
