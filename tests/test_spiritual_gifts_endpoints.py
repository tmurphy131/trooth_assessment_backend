import pytest
from app.services.spiritual_gifts_scoring import GIFT_ITEM_MAP


def build_full_answers():
    data = {}
    for items in GIFT_ITEM_MAP.values():
        for q in items:
            data[q] = 2
    return data

@pytest.fixture
def apprentice_headers(apprentice_user, client):
    # override current_user dependency globally to apprentice_user
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


def test_submit_success(client, apprentice_headers):
    payload = {"template_key": "spiritual_gifts_v1", "answers": build_full_answers()}
    r = client.post("/assessments/spiritual-gifts/submit", json=payload, headers=apprentice_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["template_key"] == "spiritual_gifts_v1"
    assert len(body["all_scores"]) == 24
    assert len(body["top_gifts_truncated"]) <= 3


def test_submit_reject_wrong_role(client, mentor_headers):
    payload = {"template_key": "spiritual_gifts_v1", "answers": build_full_answers()}
    r = client.post("/assessments/spiritual-gifts/submit", json=payload, headers=mentor_headers)
    assert r.status_code == 403


def test_submit_validation_error(client, apprentice_headers):
    bad_payload = {"template_key": "spiritual_gifts_v1", "answers": {"Q01": 2}}
    r = client.post("/assessments/spiritual-gifts/submit", json=bad_payload, headers=apprentice_headers)
    assert r.status_code == 400


def test_latest_and_history(client, apprentice_headers):
    payload = {"template_key": "spiritual_gifts_v1", "answers": build_full_answers()}
    r1 = client.post("/assessments/spiritual-gifts/submit", json=payload, headers=apprentice_headers)
    assert r1.status_code == 200
    r2 = client.post("/assessments/spiritual-gifts/submit", json=payload, headers=apprentice_headers)
    assert r2.status_code == 200
    latest = client.get("/assessments/spiritual-gifts/latest", headers=apprentice_headers)
    assert latest.status_code == 200
    history = client.get("/assessments/spiritual-gifts/history?limit=10", headers=apprentice_headers)
    assert history.status_code == 200
    hist_body = history.json()
    assert "results" in hist_body
    assert len(hist_body["results"]) == 2
    assert hist_body["results"][0]["created_at"] >= hist_body["results"][1]["created_at"]


def test_history_cursor_pagination_basic(client, apprentice_headers):
    payload = {"template_key": "spiritual_gifts_v1", "answers": build_full_answers()}
    # create 3 submissions so we can test pagination (limit=2)
    for _ in range(3):
        r = client.post("/assessments/spiritual-gifts/submit", json=payload, headers=apprentice_headers)
        assert r.status_code == 200
    first = client.get("/assessments/spiritual-gifts/history?limit=2", headers=apprentice_headers)
    assert first.status_code == 200
    body1 = first.json()
    assert len(body1["results"]) == 2
    assert body1["next_cursor"] is not None
    cursor = body1["next_cursor"]
    second = client.get(f"/assessments/spiritual-gifts/history?limit=2&cursor={cursor}", headers=apprentice_headers)
    assert second.status_code == 200
    body2 = second.json()
    # remaining 1 result
    assert len(body2["results"]) == 1
    # no more pages
    assert body2["next_cursor"] is None
    # ensure no overlap between pages (ids distinct)
    ids_page1 = {r["id"] for r in body1["results"]}
    ids_page2 = {r["id"] for r in body2["results"]}
    assert ids_page1.isdisjoint(ids_page2)


def test_history_cursor_invalid_cursor(client, apprentice_headers):
    payload = {"template_key": "spiritual_gifts_v1", "answers": build_full_answers()}
    client.post("/assessments/spiritual-gifts/submit", json=payload, headers=apprentice_headers)
    r = client.get("/assessments/spiritual-gifts/history?limit=2&cursor=not-base64", headers=apprentice_headers)
    assert r.status_code == 400


def test_latest_404_when_none(client, apprentice_headers):
    r = client.get("/assessments/spiritual-gifts/latest", headers=apprentice_headers)
    assert r.status_code == 404
