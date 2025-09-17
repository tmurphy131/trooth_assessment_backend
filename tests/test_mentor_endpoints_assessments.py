import pytest
from uuid import uuid4


def _override_user(client, user):
    from app.services.auth import get_current_user

    class _User:
        id = user.id
        role = user.role
        email = user.email
        name = user.name

    client.app.dependency_overrides[get_current_user] = lambda: _User()


@pytest.fixture
def mentor_link(db_session, mentor_user, apprentice_user):
    from app.models.mentor_apprentice import MentorApprentice

    link = MentorApprentice(apprentice_id=apprentice_user.id, mentor_id=mentor_user.id, active=True)
    db_session.add(link)
    db_session.commit()
    return link


@pytest.fixture
def generic_template_id(db_session):
    from app.models.assessment_template import AssessmentTemplate

    tpl = AssessmentTemplate(
        id=str(uuid4()),
        name="Generic Mentor View",
        is_published=True,
        is_master_assessment=False,
        created_by=None,
        version=1,
        key="generic_mentor_view_v1",
        scoring_strategy="ai_generic",
        rubric_json={
            "categories": [
                {"name": "A", "question_ids": ["q1"]},
            ]
        },
        report_template="generic_assessment_report.html",
        pdf_renderer="generic",
    )
    db_session.add(tpl)
    db_session.commit()
    return tpl.id


def test_mentor_views_master_latest_history(client, apprentice_user, mentor_user, mentor_link):
    # Apprentice submits two master assessments
    payload = {"answers": {"Q1": "Yes", "Q2": "No"}}
    _override_user(client, apprentice_user)
    r1 = client.post("/assessments/master-trooth/submit", json=payload)
    assert r1.status_code == 200
    r2 = client.post("/assessments/master-trooth/submit", json=payload)
    assert r2.status_code == 200

    # Mentor can see latest and history
    apprentice_id = mentor_link.apprentice_id
    _override_user(client, mentor_user)
    latest = client.get(f"/assessments/master-trooth/{apprentice_id}/latest")
    assert latest.status_code == 200
    hist = client.get(f"/assessments/master-trooth/{apprentice_id}/history?limit=2")
    assert hist.status_code == 200
    assert len(hist.json().get("results", [])) == 2


def test_mentor_views_generic_latest_history_and_email(client, apprentice_user, mentor_user, mentor_link, generic_template_id):
    # Apprentice submits two for the template
    payload = {"answers": {"q1": 5}}
    _override_user(client, apprentice_user)
    r1 = client.post(f"/templates/{generic_template_id}/submit", json=payload)
    assert r1.status_code == 200
    r2 = client.post(f"/templates/{generic_template_id}/submit", json=payload)
    assert r2.status_code == 200

    apprentice_id = mentor_link.apprentice_id
    _override_user(client, mentor_user)
    latest = client.get(f"/templates/{generic_template_id}/{apprentice_id}/latest")
    assert latest.status_code == 200
    hist = client.get(f"/templates/{generic_template_id}/{apprentice_id}/history?limit=2")
    assert hist.status_code == 200
    assert len(hist.json().get("results", [])) == 2

    # Mentor email-report
    er = client.post(f"/templates/{generic_template_id}/{apprentice_id}/email-report", json={"to_email": "someone@example.com", "include_pdf": False})
    assert er.status_code == 200
    assert er.json().get("sent") is True
