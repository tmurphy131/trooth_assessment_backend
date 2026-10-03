"""Tests for the apprentice prayer journal and mentor shared view."""
import pytest
from uuid import uuid4
from datetime import datetime, UTC

from app.main import app
from app.models.user import User
from app.models.mentor_apprentice import MentorApprentice
from app.models.prayer_entry import PrayerEntry
from app.services.auth import get_current_user
from app.services.account_deletion import delete_apprentice_account


def _act_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
def _clear_auth_override():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _make_user(db_session, role):
    user = User(
        id=str(uuid4()),
        name=f"{role.title()} Extra",
        email=f"{role}+{uuid4().hex[:8]}@example.com",
        role=role,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.commit()
    return user


def _create(client, **overrides):
    payload = {"title": "Pray for my brother's job search", "category": "intercession", **overrides}
    r = client.post("/prayer-journal/entries", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_create_and_list_entries(client, apprentice_user):
    _act_as(apprentice_user)
    created = _create(client, scripture_ref="Phil 4:6-7", praying_for="Marcus")
    assert created["apprentice_id"] == apprentice_user.id
    assert created["shared_with_mentor"] is False
    assert created["answered_at"] is None

    r = client.get("/prayer-journal/entries")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["scripture_ref"] == "Phil 4:6-7"


def test_default_category_and_validation(client, apprentice_user):
    _act_as(apprentice_user)
    r = client.post("/prayer-journal/entries", json={"title": "Peace this week"})
    assert r.status_code == 200
    assert r.json()["category"] == "request"

    assert client.post("/prayer-journal/entries", json={"title": ""}).status_code == 422
    assert client.post("/prayer-journal/entries", json={"title": "x", "category": "bogus"}).status_code == 422
    assert client.post("/prayer-journal/entries", json={"title": "x" * 121}).status_code == 422


def test_update_entry_and_clear_optional_field(client, apprentice_user):
    _act_as(apprentice_user)
    entry = _create(client, scripture_ref="Ps 23")
    r = client.patch(
        f"/prayer-journal/entries/{entry['id']}",
        json={"title": "Updated", "shared_with_mentor": True, "scripture_ref": None},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Updated"
    assert body["shared_with_mentor"] is True
    assert body["scripture_ref"] is None
    assert body["category"] == "intercession"  # untouched


def test_mark_and_unmark_answered_with_status_filter(client, apprentice_user):
    _act_as(apprentice_user)
    a = _create(client, title="Answered one")
    _create(client, title="Still praying")

    r = client.post(f"/prayer-journal/entries/{a['id']}/answered", json={"answer_note": "Got the job!"})
    assert r.status_code == 200
    assert r.json()["answered_at"] is not None
    assert r.json()["answer_note"] == "Got the job!"

    answered = client.get("/prayer-journal/entries", params={"status": "answered"}).json()
    active = client.get("/prayer-journal/entries", params={"status": "active"}).json()
    assert [e["title"] for e in answered] == ["Answered one"]
    assert [e["title"] for e in active] == ["Still praying"]

    r = client.delete(f"/prayer-journal/entries/{a['id']}/answered")
    assert r.status_code == 200
    assert r.json()["answered_at"] is None
    assert r.json()["answer_note"] is None


def test_category_filter(client, apprentice_user):
    _act_as(apprentice_user)
    _create(client, title="Thanks", category="thanksgiving")
    _create(client, title="Help", category="request")
    data = client.get("/prayer-journal/entries", params={"category": "thanksgiving"}).json()
    assert [e["title"] for e in data] == ["Thanks"]


def test_delete_entry(client, apprentice_user):
    _act_as(apprentice_user)
    entry = _create(client)
    assert client.delete(f"/prayer-journal/entries/{entry['id']}").status_code == 204
    assert client.get("/prayer-journal/entries").json() == []


def test_other_apprentice_cannot_touch_entry(client, db_session, apprentice_user):
    _act_as(apprentice_user)
    entry = _create(client)

    other = _make_user(db_session, "apprentice")
    _act_as(other)
    assert client.get("/prayer-journal/entries").json() == []
    assert client.patch(f"/prayer-journal/entries/{entry['id']}", json={"title": "hijack"}).status_code == 404
    assert client.delete(f"/prayer-journal/entries/{entry['id']}").status_code == 404
    assert client.post(f"/prayer-journal/entries/{entry['id']}/answered", json={}).status_code == 404


def test_mentor_cannot_use_apprentice_endpoints(client, mentor_user):
    _act_as(mentor_user)
    assert client.get("/prayer-journal/entries").status_code == 403


def test_mentor_sees_only_shared_entries(client, apprentice_user, mentor_user, mentor_apprentice_link):
    _act_as(apprentice_user)
    _create(client, title="Shared", shared_with_mentor=True)
    _create(client, title="Private")

    _act_as(mentor_user)
    r = client.get(f"/prayer-journal/mentor/apprentices/{apprentice_user.id}/entries")
    assert r.status_code == 200
    assert [e["title"] for e in r.json()] == ["Shared"]


def test_unlinked_or_inactive_mentor_forbidden(client, db_session, apprentice_user, mentor_user):
    _act_as(apprentice_user)
    _create(client, title="Shared", shared_with_mentor=True)

    _act_as(mentor_user)
    url = f"/prayer-journal/mentor/apprentices/{apprentice_user.id}/entries"
    assert client.get(url).status_code == 403

    db_session.add(MentorApprentice(apprentice_id=apprentice_user.id, mentor_id=mentor_user.id, active=False))
    db_session.commit()
    assert client.get(url).status_code == 403


def test_account_deletion_removes_entries(client, db_session, apprentice_user):
    _act_as(apprentice_user)
    _create(client)
    _create(client, title="Second")

    user_id = apprentice_user.id
    result = delete_apprentice_account(db_session, user_id, apprentice_user.email)
    assert result["deleted_counts"]["prayer_entries"] == 2
    db_session.expire_all()
    assert db_session.query(PrayerEntry).filter_by(apprentice_id=user_id).count() == 0
