import pytest


@pytest.fixture
def apprentice_ctx(apprentice_user, client):
    from app.services.auth import get_current_user
    class _U:
        id = apprentice_user.id
        role = apprentice_user.role
        email = apprentice_user.email
        name = apprentice_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _U()
    return {"Authorization": f"Bearer mock-{apprentice_user.id}"}


@pytest.fixture
def mentor_ctx(mentor_user, client):
    from app.services.auth import get_current_user
    class _U:
        id = mentor_user.id
        role = mentor_user.role
        email = mentor_user.email
        name = mentor_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _U()
    return {"Authorization": f"Bearer mock-{mentor_user.id}"}


def _submit_master(client, headers):
    payload = {"answers": {"Q1": "Yes", "Q2": "No", "Q3": "Sometimes"}}
    r = client.post("/assessments/master-trooth/submit", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_apprentice_email_report_success(client, apprentice_ctx):
    assess_id = _submit_master(client, apprentice_ctx)
    body = {"to_email": "apprentice@example.com", "include_pdf": True}
    r = client.post("/assessments/master-trooth/email-report", json=body, headers=apprentice_ctx)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sent"] is True
    assert data["assessment_id"]


def test_apprentice_email_must_match_self_email(client, apprentice_ctx):
    _submit_master(client, apprentice_ctx)
    body = {"to_email": "someoneelse@example.com"}
    r = client.post("/assessments/master-trooth/email-report", json=body, headers=apprentice_ctx)
    assert r.status_code == 400


def test_mentor_email_report_flow(client, mentor_user, apprentice_user, mentor_apprentice_link):
    # impersonate apprentice to create an assessment first
    from app.services.auth import get_current_user
    class _A:
        id = apprentice_user.id
        role = apprentice_user.role
        email = apprentice_user.email
        name = apprentice_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _A()
    _submit_master(client, {"Authorization": f"Bearer mock-{apprentice_user.id}"})

    # switch auth to mentor
    class _M:
        id = mentor_user.id
        role = mentor_user.role
        email = mentor_user.email
        name = mentor_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _M()

    body = {"to_email": "mentor_dest@example.com", "include_pdf": True}
    r = client.post(f"/assessments/master-trooth/{apprentice_user.id}/email-report", json=body, headers={"Authorization": f"Bearer mock-{mentor_user.id}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sent"] is True
    assert data["assessment_id"]


def test_mentor_email_report_denied_without_link(client, mentor_user, apprentice_user):
    # No link created
    from app.services.auth import get_current_user
    # create assessment as apprentice first
    class _A:
        id = apprentice_user.id
        role = apprentice_user.role
        email = apprentice_user.email
        name = apprentice_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _A()
    _submit_master(client, {"Authorization": f"Bearer mock-{apprentice_user.id}"})
    # switch to mentor
    class _M:
        id = mentor_user.id
        role = mentor_user.role
        email = mentor_user.email
        name = mentor_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _M()
    body = {"to_email": "dest@example.com"}
    r = client.post(f"/assessments/master-trooth/{apprentice_user.id}/email-report", json=body, headers={"Authorization": f"Bearer mock-{mentor_user.id}"})
    assert r.status_code == 403
