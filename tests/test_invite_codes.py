"""Invite codes: redeem, codes on invites, secured accept-by-token (specs/006-invite-codes)."""
import logging
import re
import uuid
from datetime import datetime, timedelta, UTC

import pytest

from app.main import app
from app.models.apprentice_invitation import ApprenticeInvitation
from app.models.invite_code_attempt import InviteCodeAttempt
from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User
from app.services.auth import get_current_user
from app.services.invitations import accept_invitation

CODE_RE = re.compile(r"^[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$")


def _naive_now():
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture
def act_as():
    """Sign requests in as a real (persisted) user; clear the override afterwards."""
    def _set(user):
        app.dependency_overrides[get_current_user] = lambda: user
    yield _set
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def make_user(db_session):
    def _make(role, email=None, name=None):
        user = User(
            id=str(uuid.uuid4()),
            name=name or f"{role.title()} {uuid.uuid4().hex[:4]}",
            email=email or f"{role}+{uuid.uuid4().hex[:8]}@example.com",
            role=role,
            created_at=datetime.now(UTC),
        )
        db_session.add(user)
        db_session.commit()
        return user
    return _make


@pytest.fixture
def make_invite(db_session):
    def _make(mentor, email="invitee@example.com", code="K7QM3XPR", expired=False, accepted=False):
        expires = _naive_now() + (timedelta(days=-1) if expired else timedelta(days=7))
        invite = ApprenticeInvitation(
            mentor_id=mentor.id,
            apprentice_email=email,
            apprentice_name="Invitee",
            token=str(uuid.uuid4()),
            code=code,
            expires_at=expires,
            accepted=accepted,
        )
        db_session.add(invite)
        db_session.commit()
        return invite
    return _make


def _attempts(db_session, user):
    db_session.expire_all()
    return db_session.query(InviteCodeAttempt).filter_by(user_id=user.id).all()


def _pairing(db_session, mentor, apprentice):
    db_session.expire_all()
    return db_session.query(MentorApprentice).filter_by(mentor_id=mentor.id, apprentice_id=apprentice.id).all()


# ---------------------------------------------------------------------------
# US1: POST /invitations/redeem
# ---------------------------------------------------------------------------

def test_redeem_creates_pairing_even_when_email_differs(client, db_session, act_as, mentor_user, apprentice_user, make_invite):
    invite = make_invite(mentor_user, email="someone-else@example.com")
    assert apprentice_user.email != invite.apprentice_email
    act_as(apprentice_user)

    r = client.post("/invitations/redeem", json={"code": "K7QM-3XPR"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["relationship"] == "created"
    assert body["mentor_id"] == mentor_user.id
    assert body["mentor_name"] == mentor_user.name
    assert body["message"] == "Invitation accepted, relationship created"
    assert len(_pairing(db_session, mentor_user, apprentice_user)) == 1
    assert db_session.get(ApprenticeInvitation, invite.id).accepted is True


@pytest.mark.parametrize("typed", ["k7qm3xpr", " K7QM-3XPR ", "k7qm 3xpr"])
def test_redeem_normalizes_input(client, act_as, mentor_user, apprentice_user, make_invite, typed):
    make_invite(mentor_user)
    act_as(apprentice_user)
    r = client.post("/invitations/redeem", json={"code": typed})
    assert r.status_code == 200, r.text


def test_redeem_twice_is_already_accepted(client, act_as, mentor_user, apprentice_user, make_invite):
    make_invite(mentor_user)
    act_as(apprentice_user)
    assert client.post("/invitations/redeem", json={"code": "K7QM3XPR"}).status_code == 200
    r = client.post("/invitations/redeem", json={"code": "K7QM3XPR"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invitation has already been accepted"


def test_redeem_expired(client, act_as, mentor_user, apprentice_user, make_invite):
    make_invite(mentor_user, expired=True)
    act_as(apprentice_user)
    r = client.post("/invitations/redeem", json={"code": "K7QM3XPR"})
    assert r.status_code == 400
    assert r.json()["detail"] == "This invitation has expired."


@pytest.mark.parametrize("typed", ["ABCD-EFGH", "ABC", "0OIL-0OIL"])
def test_redeem_unknown_or_malformed_is_404(client, act_as, apprentice_user, typed):
    act_as(apprentice_user)
    r = client.post("/invitations/redeem", json={"code": typed})
    assert r.status_code == 404
    assert r.json()["detail"] == "Invite code not found"


def test_redeem_reactivates_inactive_pairing(client, db_session, act_as, mentor_user, apprentice_user, make_invite):
    db_session.add(MentorApprentice(mentor_id=mentor_user.id, apprentice_id=apprentice_user.id, active=False))
    db_session.commit()
    make_invite(mentor_user)
    act_as(apprentice_user)

    r = client.post("/invitations/redeem", json={"code": "K7QM3XPR"})

    assert r.status_code == 200
    assert r.json()["relationship"] == "reactivated"
    rows = _pairing(db_session, mentor_user, apprentice_user)
    assert len(rows) == 1 and rows[0].active is True


def test_redeem_already_active_pairing(client, act_as, mentor_user, apprentice_user, mentor_apprentice_link, make_invite):
    make_invite(mentor_user)
    act_as(apprentice_user)
    r = client.post("/invitations/redeem", json={"code": "K7QM3XPR"})
    assert r.status_code == 200
    assert r.json()["relationship"] == "already_active"


@pytest.mark.parametrize("role", ["mentor", "admin"])
def test_redeem_requires_apprentice_role(client, act_as, make_user, mentor_user, make_invite, role):
    make_invite(mentor_user)
    act_as(make_user(role))
    r = client.post("/invitations/redeem", json={"code": "K7QM3XPR"})
    assert r.status_code == 403


def test_redeem_requires_auth(client, mentor_user, make_invite):
    make_invite(mentor_user)
    app.dependency_overrides.pop(get_current_user, None)
    r = client.post("/invitations/redeem", json={"code": "K7QM3XPR"})
    assert r.status_code == 401


@pytest.mark.parametrize("payload", [{}, {"code": "A" * 33}])
def test_redeem_validation_422(client, act_as, apprentice_user, payload):
    act_as(apprentice_user)
    r = client.post("/invitations/redeem", json=payload)
    assert r.status_code == 422


def test_redeem_rate_limit_and_window(client, db_session, act_as, mentor_user, apprentice_user, make_invite):
    make_invite(mentor_user)
    act_as(apprentice_user)
    for _ in range(10):
        assert client.post("/invitations/redeem", json={"code": "ABCD-EFGH"}).status_code == 404

    r = client.post("/invitations/redeem", json={"code": "K7QM3XPR"})
    assert r.status_code == 429
    assert r.json()["detail"] == "Too many invalid codes. Try again later."
    assert int(r.headers["Retry-After"]) >= 1

    # Age the failures past the one-hour window: the valid code now works.
    for attempt in _attempts(db_session, apprentice_user):
        attempt.created_at = _naive_now() - timedelta(hours=1, minutes=1)
    db_session.commit()
    assert client.post("/invitations/redeem", json={"code": "K7QM3XPR"}).status_code == 200


def test_attempts_recorded_only_for_200_400_404(client, db_session, act_as, make_user, mentor_user, apprentice_user, make_invite):
    make_invite(mentor_user)
    make_invite(mentor_user, code="22223333", expired=True)
    act_as(apprentice_user)
    client.post("/invitations/redeem", json={"code": "ABCD-EFGH"})   # 404
    client.post("/invitations/redeem", json={"code": "2222-3333"})   # 400 expired
    client.post("/invitations/redeem", json={})                      # 422, not recorded
    client.post("/invitations/redeem", json={"code": "K7QM3XPR"})    # 200

    attempts = _attempts(db_session, apprentice_user)
    assert sorted(a.succeeded for a in attempts) == [False, False, True]

    mentor = make_user("mentor")
    act_as(mentor)
    client.post("/invitations/redeem", json={"code": "K7QM3XPR"})    # 403, not recorded
    assert _attempts(db_session, mentor) == []


def test_rate_limited_attempts_not_recorded(client, db_session, act_as, apprentice_user):
    act_as(apprentice_user)
    for _ in range(10):
        client.post("/invitations/redeem", json={"code": "ABCD-EFGH"})
    assert client.post("/invitations/redeem", json={"code": "ABCD-EFGH"}).status_code == 429
    assert len(_attempts(db_session, apprentice_user)) == 10


def test_concurrent_acceptance_only_one_wins(db_session, mentor_user, apprentice_user, make_user, make_invite):
    """A stale invite object (loaded before someone else accepted) must not pair a second apprentice."""
    invite = make_invite(mentor_user)
    stale = db_session.get(ApprenticeInvitation, invite.id)
    # Another request accepts it first.
    db_session.query(ApprenticeInvitation).filter_by(id=invite.id).update({"accepted": True})
    db_session.commit()
    stale.accepted = False  # simulate the in-memory copy read before that update

    with pytest.raises(Exception) as exc:
        accept_invitation(db_session, stale, apprentice_user)
    assert getattr(exc.value, "status_code", None) == 400
    assert exc.value.detail == "Invitation has already been accepted"
    assert _pairing(db_session, mentor_user, apprentice_user) == []


def test_redeem_logs_outcome_without_code(client, act_as, mentor_user, apprentice_user, make_invite, caplog):
    make_invite(mentor_user)
    act_as(apprentice_user)
    with caplog.at_level(logging.INFO, logger="app.services.invitations"):
        client.post("/invitations/redeem", json={"code": "ABCD-EFGH"})
        client.post("/invitations/redeem", json={"code": "K7QM-3XPR"})

    messages = [r.getMessage() for r in caplog.records if r.name == "app.services.invitations"]
    assert any("invite.redeem" in m and "outcome=not_found" in m for m in messages)
    assert any("invite.redeem" in m and "outcome=ok" in m for m in messages)
    for secret in ("K7QM3XPR", "K7QM-3XPR", "ABCDEFGH", "ABCD-EFGH"):
        assert secret not in caplog.text


# ---------------------------------------------------------------------------
# US2: codes on created invites, lists, email and landing page
# ---------------------------------------------------------------------------

@pytest.fixture
def sent_invites(monkeypatch):
    """Capture send_invitation_email calls made by the invite route."""
    calls = []

    def _fake(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr("app.routes.invite.send_invitation_email", _fake)
    return calls


def test_create_invite_returns_code_and_lists_it(client, act_as, mentor_user, sent_invites):
    act_as(mentor_user)
    r = client.post("/invitations/invite-apprentice",
                    json={"apprentice_email": "new@example.com", "apprentice_name": "New"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"] == "Invitation sent"
    assert body["id"] and body["expires_at"]
    assert CODE_RE.match(body["code"])

    pending = client.get("/invitations/pending-invites")
    assert pending.status_code == 200
    assert [i["code"] for i in pending.json()] == [body["code"]]

    assert len(sent_invites) == 1
    assert sent_invites[0]["code"] == body["code"]


def test_apprentice_invites_include_code(client, act_as, mentor_user, apprentice_user, make_invite):
    make_invite(mentor_user, email=apprentice_user.email)
    act_as(apprentice_user)
    r = client.get("/invitations/apprentice-invites", params={"email": apprentice_user.email})
    assert r.status_code == 200
    assert [i["code"] for i in r.json()] == ["K7QM-3XPR"]


def test_apprentice_cannot_create_invite(client, act_as, apprentice_user):
    act_as(apprentice_user)
    r = client.post("/invitations/invite-apprentice",
                    json={"apprentice_email": "new@example.com", "apprentice_name": "New"})
    assert r.status_code == 403


def test_apprentice_cannot_list_pending_invites(client, act_as, apprentice_user):
    act_as(apprentice_user)
    assert client.get("/invitations/pending-invites").status_code == 403


def test_apprentice_invites_for_someone_else_forbidden(client, act_as, apprentice_user):
    act_as(apprentice_user)
    r = client.get("/invitations/apprentice-invites", params={"email": "other@example.com"})
    assert r.status_code == 403
    assert r.json()["detail"] == "You can only view your own invitations"


def test_landing_page_shows_code_not_token(client, mentor_user, make_invite):
    invite = make_invite(mentor_user)
    r = client.get("/invitations/accept-invitation", params={"token": invite.token})
    assert r.status_code == 200
    assert "K7QM-3XPR" in r.text
    assert invite.token not in r.text


def test_invitation_email_renders_code():
    from app.services.email import render_invitation_email
    html, text = render_invitation_email("Jordan", "Marcus", "tok-123", code="K7QM-3XPR")
    assert "K7QM-3XPR" in html
    assert "K7QM-3XPR" in text


def test_invitation_email_without_code_still_renders():
    from app.services.email import render_invitation_email
    html, _ = render_invitation_email("Jordan", "Marcus", "tok-123")
    assert "Your invite code" not in html


# ---------------------------------------------------------------------------
# US3: accept-by-token requires the signed-in apprentice
# ---------------------------------------------------------------------------

def test_accept_by_token_requires_auth(client, db_session, mentor_user, make_invite):
    invite = make_invite(mentor_user)
    app.dependency_overrides.pop(get_current_user, None)
    r = client.post("/invitations/accept-invite", json={"token": invite.token})
    assert r.status_code == 401
    db_session.expire_all()
    assert db_session.get(ApprenticeInvitation, invite.id).accepted is False


def test_accept_by_token_for_someone_else_forbidden(client, db_session, act_as, make_user, mentor_user, apprentice_user, make_invite):
    invite = make_invite(mentor_user)
    other = make_user("apprentice")
    act_as(apprentice_user)
    r = client.post("/invitations/accept-invite", json={"token": invite.token, "apprentice_id": other.id})
    assert r.status_code == 403
    assert r.json()["detail"] == "You can only accept invitations for yourself"
    db_session.expire_all()
    assert db_session.get(ApprenticeInvitation, invite.id).accepted is False
    assert _pairing(db_session, mentor_user, other) == []


def test_accept_by_token_with_own_id(client, db_session, act_as, mentor_user, apprentice_user, make_invite):
    """What released apps send: the token plus their own ID."""
    invite = make_invite(mentor_user)
    act_as(apprentice_user)
    r = client.post("/invitations/accept-invite", json={"token": invite.token, "apprentice_id": apprentice_user.id})
    assert r.status_code == 200
    assert r.json() == {"message": "Invitation accepted, relationship created"}
    assert len(_pairing(db_session, mentor_user, apprentice_user)) == 1


def test_accept_by_token_without_id(client, act_as, mentor_user, apprentice_user, make_invite):
    invite = make_invite(mentor_user)
    act_as(apprentice_user)
    r = client.post("/invitations/accept-invite", json={"token": invite.token})
    assert r.status_code == 200


def test_accept_by_token_unknown_token(client, act_as, apprentice_user):
    act_as(apprentice_user)
    r = client.post("/invitations/accept-invite", json={"token": "nope"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invitation is invalid or expired"


def test_accept_by_token_mentor_forbidden(client, act_as, mentor_user, make_invite):
    invite = make_invite(mentor_user)
    act_as(mentor_user)
    r = client.post("/invitations/accept-invite", json={"token": invite.token})
    assert r.status_code == 403


@pytest.mark.parametrize("active", [False, True])
def test_accept_by_token_existing_pairing_says_reactivated(client, db_session, act_as, mentor_user, apprentice_user, make_invite, active):
    db_session.add(MentorApprentice(mentor_id=mentor_user.id, apprentice_id=apprentice_user.id, active=active))
    db_session.commit()
    invite = make_invite(mentor_user)
    act_as(apprentice_user)
    r = client.post("/invitations/accept-invite", json={"token": invite.token})
    assert r.status_code == 200
    assert r.json() == {"message": "Invitation accepted, relationship reactivated"}


# ---------------------------------------------------------------------------
# Account deletion removes the user's attempts
# ---------------------------------------------------------------------------

def test_account_deletion_removes_invite_code_attempts(db_session, apprentice_user):
    from app.services.account_deletion import delete_apprentice_account
    user_id, email = apprentice_user.id, apprentice_user.email
    db_session.add(InviteCodeAttempt(user_id=user_id, invitation_id=None, succeeded=False))
    db_session.commit()

    delete_apprentice_account(db_session, user_id, email)

    db_session.expire_all()
    assert db_session.query(InviteCodeAttempt).filter_by(user_id=user_id).count() == 0
