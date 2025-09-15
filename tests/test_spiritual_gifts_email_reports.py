import pytest


def _full_answers():
    # Minimal synthetic answers (the scorer will validate question coverage elsewhere; reuse existing test util if needed)
    from app.services.spiritual_gifts_scoring import GIFT_ITEM_MAP
    answers = {}
    for items in GIFT_ITEM_MAP.values():
        for q in items:
            answers[q] = 2
    return answers


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


def _submit_gifts(client, headers):
    payload = {"template_key": "spiritual_gifts_v1", "answers": _full_answers()}
    r = client.post("/assessments/spiritual-gifts/submit", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_apprentice_email_report_success(client, apprentice_ctx):
    assess_id = _submit_gifts(client, apprentice_ctx)
    body = {"to_email": "dest@example.com", "assessment_id": assess_id, "include_pdf": True, "include_html": False}
    r = client.post("/assessments/spiritual-gifts/email-report", json=body, headers=apprentice_ctx)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sent"] is True
    assert data["assessment_id"] == assess_id
    assert data["pdf_bytes"] is not None


def test_apprentice_email_report_rate_limit(client, apprentice_ctx, db_session):
    _submit_gifts(client, apprentice_ctx)
    body = {"to_email": "dest@example.com", "include_pdf": False, "include_html": True}
    # send 5 times (allowed)
    for i in range(5):
        r = client.post("/assessments/spiritual-gifts/email-report", json=body, headers=apprentice_ctx)
        assert r.status_code == 200, f"iteration {i} failed: {r.text}"
    # 6th should fail 429
    r6 = client.post("/assessments/spiritual-gifts/email-report", json=body, headers=apprentice_ctx)
    assert r6.status_code == 429


def test_email_report_wrong_role_for_self_endpoint(client, mentor_ctx):
    body = {"to_email": "x@example.com"}
    r = client.post("/assessments/spiritual-gifts/email-report", json=body, headers=mentor_ctx)
    assert r.status_code == 403


def test_mentor_email_report_flow(client, mentor_user, apprentice_user, mentor_apprentice_link):
    # impersonate apprentice to create an assessment first
    from app.services.auth import get_current_user
    class _A:
        id = apprentice_user.id
        role = apprentice_user.role
        email = apprentice_user.email
        name = apprentice_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _A()
    _submit_gifts(client, {"Authorization": f"Bearer mock-{apprentice_user.id}"})

    # switch auth to mentor
    class _M:
        id = mentor_user.id
        role = mentor_user.role
        email = mentor_user.email
        name = mentor_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _M()

    body = {"to_email": "mentor_dest@example.com", "include_pdf": True}
    r = client.post(f"/assessments/spiritual-gifts/{apprentice_user.id}/email-report", json=body, headers={"Authorization": f"Bearer mock-{mentor_user.id}"})
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
    _submit_gifts(client, {"Authorization": f"Bearer mock-{apprentice_user.id}"})
    # switch to mentor
    class _M:
        id = mentor_user.id
        role = mentor_user.role
        email = mentor_user.email
        name = mentor_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _M()
    body = {"to_email": "dest@example.com"}
    r = client.post(f"/assessments/spiritual-gifts/{apprentice_user.id}/email-report", json=body, headers={"Authorization": f"Bearer mock-{mentor_user.id}"})
    assert r.status_code == 403


def test_public_template_metadata(client, apprentice_ctx):
    # Submit once to ensure a template instance exists (publish step might not be explicit in test; fallback version=1)
    _submit_gifts(client, apprentice_ctx)
    r = client.get("/assessments/spiritual-gifts/template/metadata")
    # If no template published, could be 404; allow either 200 or 404 but assert schema on 200
    if r.status_code == 200:
        meta = r.json()
        assert "template_id" in meta
        assert "version" in meta
    else:
        assert r.status_code == 404
