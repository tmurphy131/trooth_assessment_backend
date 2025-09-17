import pytest
from uuid import uuid4


@pytest.fixture
def apprentice_headers(apprentice_user, client):
    # Override current_user dependency globally to apprentice_user
    from app.services.auth import get_current_user

    class _User:
        id = apprentice_user.id
        role = apprentice_user.role
        email = apprentice_user.email
        name = apprentice_user.name

    client.app.dependency_overrides[get_current_user] = lambda: _User()
    return {"Authorization": f"Bearer mock-{apprentice_user.id}"}


@pytest.fixture
def generic_template_id(db_session):
    """Create a published, non-master generic template accessible to any apprentice."""
    from app.models.assessment_template import AssessmentTemplate

    tpl = AssessmentTemplate(
        id=str(uuid4()),
        name="Generic Assessment E2E",
        description="E2E test template",
        is_published=True,
        is_master_assessment=False,
        created_by=None,  # accessible to all apprentices when published
        version=1,
        key="generic_e2e_v1",
        scoring_strategy="ai_generic",
        rubric_json={
            "categories": [
                {"name": "Math", "question_ids": ["q1", "q2"], "weight": 1},
                {"name": "Science", "question_ids": ["q3"], "weight": 1},
            ],
            "overall_weights": {"method": "average"},
        },
        report_template="generic_assessment_report.html",
        pdf_renderer="generic",
    )
    db_session.add(tpl)
    db_session.commit()
    return tpl.id


def test_submit_latest_history_flow(client, apprentice_headers, generic_template_id):
    # Submit twice to build some history
    payload = {"answers": {"q1": 5, "q2": 3, "q3": 4}}
    r1 = client.post(f"/templates/{generic_template_id}/submit", json=payload, headers=apprentice_headers)
    assert r1.status_code == 200, r1.text
    r2 = client.post(f"/templates/{generic_template_id}/submit", json=payload, headers=apprentice_headers)
    assert r2.status_code == 200, r2.text

    # Latest should return only scores
    latest = client.get(f"/templates/{generic_template_id}/latest", headers=apprentice_headers)
    assert latest.status_code == 200
    scores = latest.json()
    assert "overall_score" in scores
    assert isinstance(scores.get("categories"), list)
    # With q1=5, q2=3, q3=4 -> Math=4.0, Science=4.0, overall=4.0
    assert pytest.approx(scores.get("overall_score"), 0.01) == 4.0
    assert scores.get("template_version") == 1

    # History should return two results in order
    history = client.get(f"/templates/{generic_template_id}/history?limit=2", headers=apprentice_headers)
    assert history.status_code == 200
    body = history.json()
    assert "results" in body
    assert len(body["results"]) == 2
    # results are scores dicts
    assert all("overall_score" in r for r in body["results"])


def test_history_cursor_pagination(client, apprentice_headers, generic_template_id):
    payload = {"answers": {"q1": 5, "q2": 3, "q3": 4}}
    # Create three submissions to paginate with limit=2
    for _ in range(3):
        r = client.post(f"/templates/{generic_template_id}/submit", json=payload, headers=apprentice_headers)
        assert r.status_code == 200

    first = client.get(f"/templates/{generic_template_id}/history?limit=2", headers=apprentice_headers)
    assert first.status_code == 200
    page1 = first.json()
    assert len(page1["results"]) == 2
    assert page1["next_cursor"] is not None

    second = client.get(
        f"/templates/{generic_template_id}/history?limit=2&cursor={page1['next_cursor']}",
        headers=apprentice_headers,
    )
    assert second.status_code == 200
    page2 = second.json()
    assert len(page2["results"]) == 1
    assert page2["next_cursor"] is None


def test_email_report_success(client, apprentice_headers, generic_template_id):
    # Must have at least one submission to email
    payload = {"answers": {"q1": 5, "q2": 3, "q3": 4}}
    r = client.post(f"/templates/{generic_template_id}/submit", json=payload, headers=apprentice_headers)
    assert r.status_code == 200

    email_payload = {"to_email": "apprentice@example.com", "include_pdf": False}
    er = client.post(f"/templates/{generic_template_id}/email-report", json=email_payload, headers=apprentice_headers)
    assert er.status_code == 200, er.text
    body = er.json()
    assert body.get("sent") is True
    assert body.get("assessment_id")
