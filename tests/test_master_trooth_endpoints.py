import pytest


@pytest.fixture
def apprentice_headers(apprentice_user, client):
    from app.services.auth import get_current_user
    class _User:
        id = apprentice_user.id
        role = apprentice_user.role
        email = apprentice_user.email
        name = apprentice_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _User()
    return {"Authorization": f"Bearer mock-{apprentice_user.id}"}


@pytest.fixture
def mentor_headers(mentor_user, client):
    from app.services.auth import get_current_user
    class _User:
        id = mentor_user.id
        role = mentor_user.role
        email = mentor_user.email
        name = mentor_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _User()
    return {"Authorization": f"Bearer mock-{mentor_user.id}"}


def test_submit_latest_history_flow(client, apprentice_headers):
    payload = {"answers": {"Q1": "Yes", "Q2": "No", "Q3": "Sometimes"}}
    r1 = client.post("/assessments/master-trooth/submit", json=payload, headers=apprentice_headers)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/assessments/master-trooth/submit", json=payload, headers=apprentice_headers)
    assert r2.status_code == 200, r2.text

    latest = client.get("/assessments/master-trooth/latest", headers=apprentice_headers)
    assert latest.status_code == 200
    latest_scores = latest.json()
    assert "overall_score" in latest_scores
    assert "category_scores" in latest_scores

    history = client.get("/assessments/master-trooth/history?limit=2", headers=apprentice_headers)
    assert history.status_code == 200
    body = history.json()
    assert "results" in body
    assert len(body["results"]) == 2
    # next_cursor may be None with only 2 submissions
    if body.get("next_cursor"):
        r3 = client.get(f"/assessments/master-trooth/history?limit=2&cursor={body['next_cursor']}", headers=apprentice_headers)
        assert r3.status_code == 200


def test_submit_wrong_role_forbidden(client, mentor_headers):
    payload = {"answers": {"Q1": "Yes"}}
    r = client.post("/assessments/master-trooth/submit", json=payload, headers=mentor_headers)
    assert r.status_code == 403


def test_latest_404_when_none(client, apprentice_headers):
    r = client.get("/assessments/master-trooth/latest", headers=apprentice_headers)
    assert r.status_code == 404
