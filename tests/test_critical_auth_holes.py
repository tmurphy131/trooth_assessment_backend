"""specs/009-critical-auth-holes: signup identity/role, parent consent, direct linking."""
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User, UserRole

BEARER = {"Authorization": "Bearer fake-firebase-token"}


# ---------- fixtures (T001) ----------

@pytest.fixture
def firebase_token(monkeypatch):
    """Make firebase_admin.auth.verify_id_token return the given claims.

    Both aliases in app/services/auth.py (`auth`, `firebase_auth`) are the same module object.
    """
    import firebase_admin.auth as fb_auth

    state = {}

    def _verify(token, *args, **kwargs):
        return dict(state["claims"])

    monkeypatch.setattr(fb_auth, "verify_id_token", _verify)

    def _set(uid, email, email_verified=True, **extra):
        claims = {"uid": uid, "email_verified": email_verified, **extra}
        if email is not None:
            claims["email"] = email
        state["claims"] = claims
        return claims

    return _set


@pytest.fixture(autouse=True)
def claims_spy(monkeypatch):
    """Autouse so no test can reach Firebase (Principle VIII)."""
    import firebase_admin.auth as fb_auth

    calls = []
    monkeypatch.setattr(fb_auth, "set_custom_user_claims", lambda uid, claims: calls.append((uid, claims)))
    return calls


@pytest.fixture(autouse=True)
def quiet_welcome_email(monkeypatch, db_session):
    """create_user queues a welcome email that opens its own session; keep it on the test DB."""
    from sqlalchemy.orm import sessionmaker

    import app.db as app_db
    from app.services import email as email_mod

    monkeypatch.setattr(app_db, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    monkeypatch.setattr(email_mod, "send_welcome_email", lambda db, user: True)


@pytest.fixture(autouse=True)
def no_auth_overrides(client):
    """These tests exercise real token handling; drop any leaked get_current_user override."""
    from app.services.auth import get_current_user

    client.app.dependency_overrides.pop(get_current_user, None)
    yield
    client.app.dependency_overrides.pop(get_current_user, None)


def _user(db, role="apprentice", email=None, name="Existing Person", uid=None):
    u = User(id=uid or str(uuid4()), name=name, email=email or f"u{uuid4().hex[:8]}@example.com",
             role=role, created_at=datetime.now(UTC))
    db.add(u)
    db.commit()
    return u


def _signup(client, role="apprentice", email="body@example.com", name="New Person"):
    return client.post("/users/", json={"uid": "body-uid", "email": email, "name": name, "role": role}, headers=BEARER)


# ---------- helper (T003) ----------

def test_find_account_by_uid(db_session):
    from app.services.auth import find_account_for_token

    u = _user(db_session)
    assert find_account_for_token(db_session, {"uid": u.id, "email": u.email}) == (u, "by_uid")


def test_find_account_relinks_only_verified_email(db_session):
    from app.services.auth import find_account_for_token

    u = _user(db_session, email="legacy@example.com")
    old_id = u.id
    user, outcome = find_account_for_token(db_session, {"uid": "new-uid", "email": "legacy@example.com", "email_verified": False})
    assert (user, outcome) == (None, "unverified_email")
    assert db_session.get(User, old_id) is not None

    user, outcome = find_account_for_token(db_session, {"uid": "new-uid", "email": "legacy@example.com", "email_verified": True})
    assert outcome == "relinked" and user.id == "new-uid"


def test_find_account_none(db_session):
    from app.services.auth import find_account_for_token

    assert find_account_for_token(db_session, {"uid": "nobody", "email": "nobody@example.com"}) == (None, "none")
    assert find_account_for_token(db_session, {"uid": "nobody"}) == (None, "none")


# ---------- US1: signup (T006) ----------

def test_new_signup_uses_token_email_not_body(client, db_session, firebase_token, claims_spy):
    firebase_token("uid-new", "real@example.com")
    r = _signup(client, role="apprentice", email="someone-else@example.com")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == "uid-new" and r.json()["email"] == "real@example.com"
    assert db_session.query(User).filter_by(email="someone-else@example.com").first() is None
    assert claims_spy == [("uid-new", {"role": "apprentice"})]


@pytest.mark.parametrize("requested", ["mentor", "admin"])
def test_repeat_signup_cannot_change_role(client, db_session, firebase_token, claims_spy, requested):
    u = _user(db_session, role="apprentice")
    firebase_token(u.id, u.email)
    r = _signup(client, role=requested, email=u.email, name=u.name)
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "apprentice"
    db_session.expire_all()
    assert db_session.get(User, u.id).role == UserRole.apprentice
    assert claims_spy == [(u.id, {"role": "apprentice"})]


def test_new_account_cannot_register_as_admin(client, db_session, firebase_token, claims_spy, caplog):
    firebase_token("uid-admin-try", "try@example.com")
    with caplog.at_level("WARNING", logger="app.routes.user"):
        r = _signup(client, role="admin", email="try@example.com")
    assert r.status_code == 403
    assert db_session.get(User, "uid-admin-try") is None
    assert claims_spy == []
    # Logged for the post-release audit: uid and reason only, never the email (Principle V)
    lines = [rec.getMessage() for rec in caplog.records if rec.name == "app.routes.user"]
    assert any("uid=uid-admin-try" in m and "outcome=admin_requested" in m for m in lines), lines
    assert not any("try@example.com" in m for m in lines)


def test_naming_another_persons_email_never_touches_their_account(client, db_session, firebase_token):
    a = _user(db_session, role="mentor", email="a@example.com", name="Person A")
    firebase_token("uid-b", "b@example.com")
    r = _signup(client, role="apprentice", email="a@example.com", name="Person B")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == "uid-b" and r.json()["email"] == "b@example.com"
    db_session.expire_all()
    a_row = db_session.query(User).filter_by(email="a@example.com").one()
    assert (a_row.id, a_row.role, a_row.name) == (a.id, UserRole.mentor, "Person A")


def test_repeat_signup_updates_name_only(client, db_session, firebase_token, claims_spy):
    u = _user(db_session, role="mentor", name="Old Name")
    firebase_token(u.id, u.email)
    r = _signup(client, role="apprentice", email=u.email, name="New Name")
    assert r.status_code == 200
    db_session.expire_all()
    row = db_session.get(User, u.id)
    assert (row.name, row.role) == ("New Name", UserRole.mentor)


def test_legacy_relink_requires_verified_email(client, db_session, firebase_token):
    from app.routes.user import SIGNUP_CONFLICT_DETAIL

    legacy = _user(db_session, role="mentor", email="legacy@example.com", name="Legacy")
    firebase_token("uid-fresh", "legacy@example.com", email_verified=False)
    r = _signup(client, role="apprentice", email="legacy@example.com")
    assert r.status_code == 409
    # FR-013: generic, reveals nothing about the existing account
    assert r.json()["detail"] == SIGNUP_CONFLICT_DETAIL
    body = r.text.lower()
    for leak in (legacy.id.lower(), "legacy", "mentor", "exists"):
        assert leak not in body
    db_session.expire_all()
    assert db_session.get(User, legacy.id) is not None

    firebase_token("uid-fresh", "legacy@example.com", email_verified=True)
    r = _signup(client, role="apprentice", email="legacy@example.com")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == "uid-fresh" and r.json()["role"] == "mentor"


def test_token_without_email_is_refused(client, db_session, firebase_token):
    firebase_token("uid-noemail", None)
    r = _signup(client)
    assert r.status_code == 400
    assert db_session.get(User, "uid-noemail") is None


# ---------- US1: signed-in requests (T007) ----------

def test_signed_in_request_does_not_relink_unverified_email(client, db_session, firebase_token):
    legacy = _user(db_session, email="legacy2@example.com")
    firebase_token("uid-other", "legacy2@example.com", email_verified=False)
    r = client.get("/users/me/deletion-summary", headers=BEARER)
    assert r.status_code == 404
    db_session.expire_all()
    assert db_session.get(User, legacy.id) is not None
    assert db_session.get(User, "uid-other") is None


# ---------- US2: parent consent (T010) ----------

def _minor_agreement_awaiting_parent(client):
    r = client.get("/agreements/templates", headers={"Authorization": "Bearer mock-mentor-token"})
    if r.status_code == 200 and len(r.json()) == 0:
        client.post("/agreements/templates", json={"markdown_source": "Minor {{meeting_location}}", "notes": "init"},
                    headers={"Authorization": "Bearer mock-admin-token"})
    created = client.post("/agreements", json={
        "template_version": 1,
        "apprentice_email": "apprentice@example.com",
        "apprentice_is_minor": True,
        "parent_required": True,
        "parent_email": "parent@example.com",
        "fields": {"meeting_location": "Library", "meeting_duration_minutes": 30},
    }, headers={"Authorization": "Bearer mock-mentor-token"})
    assert created.status_code == 200, created.text
    ag_id = created.json()["id"]
    client.post(f"/agreements/{ag_id}/submit", headers={"Authorization": "Bearer mock-mentor-token"})
    signed = client.post(f"/agreements/{ag_id}/sign/apprentice", json={"typed_name": "Minor"},
                         headers={"Authorization": "Bearer mock-apprentice-token"})
    assert signed.json()["status"] == "awaiting_parent", signed.text
    return ag_id


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer mock-mentor-token"},
    {"Authorization": "Bearer mock-apprentice-token"},
])
def test_parent_signature_without_token_link_is_refused(client, db_session, headers):
    from app.models.agreement import Agreement, AgreementToken

    ag_id = _minor_agreement_awaiting_parent(client)
    r = client.post(f"/agreements/{ag_id}/sign/parent", json={"typed_name": "Forged Parent"}, headers=headers)
    assert r.status_code in (404, 405)
    db_session.expire_all()
    ag = db_session.get(Agreement, ag_id)
    assert ag.status == "awaiting_parent" and ag.parent_signed_at is None
    assert db_session.query(MentorApprentice).filter_by(mentor_id=ag.mentor_id, active=True).count() == 0

    # The emailed one-time link still works
    token = db_session.query(AgreementToken).filter_by(agreement_id=ag_id, token_type="parent", used_at=None).first()
    ok = client.post(f"/agreements/public/{token.token}/sign", json={"typed_name": "Real Parent"})
    assert ok.status_code == 200 and ok.json()["status"] == "fully_signed"


# ---------- US3: direct linking (T012) ----------

@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer mock-mentor-token"}])
def test_direct_mentor_apprentice_link_is_gone(client, db_session, mentor_user, apprentice_user, headers):
    r = client.post(f"/users/assign-apprentice?mentor_id={mentor_user.id}&apprentice_id={apprentice_user.id}", headers=headers)
    assert r.status_code in (404, 405)
    assert db_session.query(MentorApprentice).filter_by(mentor_id=mentor_user.id, apprentice_id=apprentice_user.id).count() == 0
