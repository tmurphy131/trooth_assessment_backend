"""Agreements and gift seats linked by apprentice account (specs/007-connected-apprentice-linking)."""
import uuid
from datetime import datetime, timedelta, UTC

import pytest

from app.main import app
from app.models.agreement import Agreement, AgreementTemplate
from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User
from app.services.auth import get_current_user
from app.services.mentorship import attach_pending_agreements, has_active_connection

FIELDS = {"meeting_location": "Cafe", "meeting_duration_minutes": 45}


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
def connect(db_session):
    def _connect(mentor, apprentice, active=True):
        db_session.add(MentorApprentice(mentor_id=mentor.id, apprentice_id=apprentice.id, active=active))
        db_session.commit()
    return _connect


@pytest.fixture
def template(db_session):
    tpl = AgreementTemplate(version=1, markdown_source="Agreement at {{meeting_location}}", is_active=True)
    db_session.add(tpl)
    db_session.commit()
    return tpl


@pytest.fixture
def make_agreement(db_session):
    def _make(mentor, email, apprentice_id=None, status="draft", **extra):
        ag = Agreement(
            template_version=1,
            mentor_id=mentor.id,
            apprentice_id=apprentice_id,
            apprentice_email=email,
            status=status,
            fields_json=dict(FIELDS),
            content_rendered="Agreement at Cafe",
            **extra,
        )
        db_session.add(ag)
        db_session.commit()
        return ag
    return _make


def _fresh(db_session, model, id_):
    db_session.expire_all()
    return db_session.get(model, id_)


# ---------------------------------------------------------------------------
# Foundational: helpers
# ---------------------------------------------------------------------------

def test_has_active_connection(db_session, mentor_user, make_user, connect):
    active, ended, stranger = make_user("apprentice"), make_user("apprentice"), make_user("apprentice")
    connect(mentor_user, active)
    connect(mentor_user, ended, active=False)
    assert has_active_connection(db_session, mentor_user.id, active.id) is True
    assert has_active_connection(db_session, mentor_user.id, ended.id) is False
    assert has_active_connection(db_session, mentor_user.id, stranger.id) is False


def test_attach_pending_agreements(db_session, mentor_user, make_user, make_agreement):
    other_mentor, apprentice, someone = make_user("mentor"), make_user("apprentice"), make_user("apprentice")
    mine = make_agreement(mentor_user, "jordan@example.com")
    mine_upper = make_agreement(mentor_user, "JORDAN@example.com")
    other_mentors = make_agreement(other_mentor, "jordan@example.com")
    already_tied = make_agreement(mentor_user, "jordan@example.com", apprentice_id=someone.id)
    different_email = make_agreement(mentor_user, "casey@example.com")

    count = attach_pending_agreements(db_session, mentor_user.id, " Jordan@Example.com ", apprentice.id)
    db_session.commit()

    assert count == 2
    assert _fresh(db_session, Agreement, mine.id).apprentice_id == apprentice.id
    assert _fresh(db_session, Agreement, mine_upper.id).apprentice_id == apprentice.id
    assert _fresh(db_session, Agreement, other_mentors.id).apprentice_id is None
    assert _fresh(db_session, Agreement, already_tied.id).apprentice_id == someone.id
    assert _fresh(db_session, Agreement, different_email.id).apprentice_id is None


# ---------------------------------------------------------------------------
# US1: agreements to a connected apprentice, by account
# ---------------------------------------------------------------------------

def _create(client, **body):
    return client.post("/agreements", json={"template_version": 1, "fields": FIELDS, **body})


def test_create_by_id_ties_agreement_to_account(client, act_as, template, mentor_user, make_user, connect):
    apprentice = make_user("apprentice", email="Relay123@privaterelay.appleid.com", name="Jordan")
    connect(mentor_user, apprentice)
    act_as(mentor_user)

    r = _create(client, apprentice_id=apprentice.id)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["apprentice_id"] == apprentice.id
    assert body["apprentice_email"] == "relay123@privaterelay.appleid.com"
    assert body["apprentice_name"] == "Jordan"


def test_create_by_id_ignores_sent_email(client, act_as, template, mentor_user, make_user, connect):
    apprentice = make_user("apprentice")
    connect(mentor_user, apprentice)
    act_as(mentor_user)
    r = _create(client, apprentice_id=apprentice.id, apprentice_email="someone-else@example.com")
    assert r.status_code == 200
    assert r.json()["apprentice_email"] == apprentice.email.lower()


@pytest.mark.parametrize("setup", ["ended", "none", "mentor_role"])
def test_create_by_id_requires_active_connection(client, db_session, act_as, template, mentor_user, make_user, connect, setup):
    if setup == "mentor_role":
        target = make_user("mentor")
    else:
        target = make_user("apprentice")
        if setup == "ended":
            connect(mentor_user, target, active=False)
    act_as(mentor_user)

    r = _create(client, apprentice_id=target.id)

    assert r.status_code == 403
    assert r.json()["detail"] == "This apprentice is not connected to you"
    db_session.expire_all()
    assert db_session.query(Agreement).count() == 0


def test_create_needs_id_or_email(client, act_as, template, mentor_user):
    act_as(mentor_user)
    assert _create(client).status_code == 422


def test_create_by_email_unchanged(client, act_as, template, mentor_user):
    act_as(mentor_user)
    r = _create(client, apprentice_email="New.Person@Example.com")
    assert r.status_code == 200
    assert r.json()["apprentice_id"] is None
    assert r.json()["apprentice_email"] == "new.person@example.com"


def test_apprentice_cannot_create_agreement(client, act_as, template, apprentice_user):
    act_as(apprentice_user)
    assert _create(client, apprentice_email="x@example.com").status_code == 403


def test_tied_agreement_reads_work_with_different_email(client, act_as, mentor_user, make_user, make_agreement):
    apprentice = make_user("apprentice", email="relay@privaterelay.appleid.com")
    ag = make_agreement(mentor_user, "typed-by-mentor@example.com", apprentice_id=apprentice.id, status="awaiting_apprentice")
    act_as(apprentice)

    assert ag.id in [a["id"] for a in client.get("/agreements/my").json()]
    assert client.get(f"/agreements/{ag.id}").status_code == 200
    assert ag.id in [a["id"] for a in client.get("/apprentice/agreements/pending").json()]


def test_tied_agreement_resend_and_reschedule_allowed(client, act_as, mentor_user, make_user, make_agreement):
    apprentice = make_user("apprentice", email="relay@privaterelay.appleid.com")
    parent_ag = make_agreement(
        mentor_user, "typed@example.com", apprentice_id=apprentice.id, status="awaiting_parent",
        parent_required=True, parent_email="parent@example.com", apprentice_signed_at=datetime.now(UTC),
    )
    active_ag = make_agreement(mentor_user, "typed@example.com", apprentice_id=apprentice.id, status="active")
    act_as(apprentice)

    r1 = client.post(f"/agreements/{parent_ag.id}/request-resend-parent", json={})
    r2 = client.post(f"/agreements/{active_ag.id}/request-reschedule", json={"reason": "Schedule change"})
    assert r1.status_code != 403, r1.text
    assert r2.status_code != 403, r2.text


def test_tied_agreement_signs_in_app(client, act_as, mentor_user, make_user, make_agreement):
    apprentice = make_user("apprentice", email="relay@privaterelay.appleid.com")
    ag = make_agreement(mentor_user, "typed@example.com", apprentice_id=apprentice.id, status="awaiting_apprentice")
    act_as(apprentice)
    r = client.post(f"/agreements/{ag.id}/sign/apprentice", json={"typed_name": "Jordan"})
    assert r.status_code == 200, r.text


def test_agreement_tied_to_someone_else_cannot_be_signed_by_email_match(client, act_as, mentor_user, make_user, make_agreement):
    owner = make_user("apprentice")
    impostor = make_user("apprentice", email="shared@example.com")
    ag = make_agreement(mentor_user, "shared@example.com", apprentice_id=owner.id, status="awaiting_apprentice")
    act_as(impostor)
    r = client.post(f"/agreements/{ag.id}/sign/apprentice", json={"typed_name": "Nope"})
    assert r.status_code == 403
    assert r.json()["detail"] == "Not authorized to sign"


def test_untied_agreement_signs_by_email_as_before(client, act_as, mentor_user, make_user, make_agreement):
    apprentice = make_user("apprentice", email="match@example.com")
    ag = make_agreement(mentor_user, "match@example.com", status="awaiting_apprentice")
    act_as(apprentice)
    assert client.post(f"/agreements/{ag.id}/sign/apprentice", json={"typed_name": "Match Person"}).status_code == 200


def test_pending_tied_agreement_blocks_ending_mentorship(client, act_as, mentor_user, make_user, connect, make_agreement):
    apprentice = make_user("apprentice", email="relay@privaterelay.appleid.com")
    connect(mentor_user, apprentice)
    make_agreement(mentor_user, "typed@example.com", apprentice_id=apprentice.id, status="awaiting_apprentice")
    act_as(apprentice)
    r = client.post("/apprentice/mentor/revoke", json={"mentor_id": mentor_user.id})
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# US2: agreements sent by email attach when the apprentice joins
# ---------------------------------------------------------------------------

@pytest.fixture
def make_invite(db_session):
    from app.models.apprentice_invitation import ApprenticeInvitation

    def _make(mentor, email, code="K7QM3XPR"):
        inv = ApprenticeInvitation(
            mentor_id=mentor.id, apprentice_email=email, apprentice_name="Invitee",
            token=str(uuid.uuid4()), code=code,
            expires_at=(datetime.now(UTC) + timedelta(days=7)).replace(tzinfo=None),
        )
        db_session.add(inv)
        db_session.commit()
        return inv
    return _make


def _my_agreement_ids(client):
    return [a["id"] for a in client.get("/agreements/my").json()]


def test_redeem_attaches_mentors_agreements_for_invited_email(client, db_session, act_as, mentor_user, make_user, make_agreement, make_invite):
    make_invite(mentor_user, "Jordan@Example.com")
    ag = make_agreement(mentor_user, "jordan@example.com", status="awaiting_apprentice")
    jordan = make_user("apprentice", email="relay@privaterelay.appleid.com")
    act_as(jordan)

    assert client.post("/invitations/redeem", json={"code": "K7QM-3XPR"}).status_code == 200

    assert _fresh(db_session, Agreement, ag.id).apprentice_id == jordan.id
    assert ag.id in _my_agreement_ids(client)


def test_accept_by_token_attaches_too(client, db_session, act_as, mentor_user, make_user, make_agreement, make_invite):
    inv = make_invite(mentor_user, "jordan@example.com")
    ag = make_agreement(mentor_user, "jordan@example.com")
    jordan = make_user("apprentice", email="other@example.com")
    act_as(jordan)

    assert client.post("/invitations/accept-invite", json={"token": inv.token}).status_code == 200
    assert _fresh(db_session, Agreement, ag.id).apprentice_id == jordan.id


def test_attach_leaves_other_mentors_and_tied_agreements(client, db_session, act_as, mentor_user, make_user, make_agreement, make_invite):
    other_mentor, someone = make_user("mentor"), make_user("apprentice")
    make_invite(mentor_user, "jordan@example.com")
    others = make_agreement(other_mentor, "jordan@example.com")
    tied = make_agreement(mentor_user, "jordan@example.com", apprentice_id=someone.id)
    jordan = make_user("apprentice")
    act_as(jordan)

    assert client.post("/invitations/redeem", json={"code": "K7QM3XPR"}).status_code == 200
    assert _fresh(db_session, Agreement, others.id).apprentice_id is None
    assert _fresh(db_session, Agreement, tied.id).apprentice_id == someone.id


def test_already_signed_by_email_link_attaches_as_signed(client, db_session, act_as, mentor_user, make_user, make_agreement, make_invite):
    make_invite(mentor_user, "jordan@example.com")
    ag = make_agreement(
        mentor_user, "jordan@example.com", status="active",
        apprentice_signature_name="Jordan", apprentice_signed_at=datetime.now(UTC),
    )
    jordan = make_user("apprentice")
    act_as(jordan)

    assert client.post("/invitations/redeem", json={"code": "K7QM3XPR"}).status_code == 200
    mine = [a for a in client.get("/agreements/my").json() if a["id"] == ag.id]
    assert mine and mine[0]["status"] == "active" and mine[0]["apprentice_signed_at"]


@pytest.mark.parametrize("existing", ["active", "inactive"])
def test_attach_runs_when_already_connected(client, db_session, act_as, mentor_user, make_user, connect, make_agreement, make_invite, existing):
    jordan = make_user("apprentice")
    connect(mentor_user, jordan, active=(existing == "active"))
    make_invite(mentor_user, "jordan@example.com")
    ag = make_agreement(mentor_user, "jordan@example.com")
    act_as(jordan)

    r = client.post("/invitations/redeem", json={"code": "K7QM3XPR"})
    assert r.status_code == 200
    assert r.json()["relationship"] == ("already_active" if existing == "active" else "reactivated")
    assert _fresh(db_session, Agreement, ag.id).apprentice_id == jordan.id


# ---------------------------------------------------------------------------
# US3: gift seats only for current apprentices; only apprentices redeem codes
# ---------------------------------------------------------------------------

@pytest.fixture
def act_as_bound():
    """Like act_as, but loads the user in the request's session (these routes commit user changes)."""
    from fastapi import Depends
    from app.db import get_db

    def _set(user):
        user_id = user.id

        def _current(db=Depends(get_db)):
            return db.query(User).filter(User.id == user_id).first()

        app.dependency_overrides[get_current_user] = _current
    yield _set
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def make_seat(db_session):
    from app.models.mentor_premium_seat import MentorPremiumSeat

    def _make(mentor, **extra):
        seat = MentorPremiumSeat(mentor_id=mentor.id, **extra)
        db_session.add(seat)
        db_session.commit()
        return seat
    return _make


def _seat(db_session, seat_id):
    from app.models.mentor_premium_seat import MentorPremiumSeat
    return _fresh(db_session, MentorPremiumSeat, seat_id)


def test_assign_seat_needs_active_connection(client, db_session, act_as_bound, mentor_user, make_user, connect, make_seat):
    ended = make_user("apprentice")
    connect(mentor_user, ended, active=False)
    seat = make_seat(mentor_user)
    act_as_bound(mentor_user)

    r = client.post(f"/mentor/seats/{seat.id}/assign", json={"apprentice_id": ended.id})

    assert r.status_code == 403
    assert r.json()["detail"] == "This apprentice is not linked to you"
    assert _seat(db_session, seat.id).apprentice_id is None


def test_assign_seat_to_active_apprentice(client, db_session, act_as_bound, mentor_user, make_user, connect, make_seat):
    current = make_user("apprentice")
    connect(mentor_user, current)
    seat = make_seat(mentor_user)
    act_as_bound(mentor_user)

    r = client.post(f"/mentor/seats/{seat.id}/assign", json={"apprentice_id": current.id})

    assert r.status_code == 200, r.text
    assert _seat(db_session, seat.id).apprentice_id == current.id


@pytest.fixture
def verified_seat_purchase(monkeypatch):
    from app.services import revenuecat
    customer = revenuecat.VerifiedCustomer(premium=None, gift_seat_purchases=1)
    monkeypatch.setattr(revenuecat, "fetch_customer", lambda app_user_id: customer)


@pytest.mark.parametrize("active", [False, True])
def test_purchase_assigns_only_active_apprentice(client, db_session, act_as_bound, mentor_user, make_user, connect, verified_seat_purchase, active):
    from app.models.mentor_premium_seat import MentorPremiumSeat
    apprentice = make_user("apprentice")
    connect(mentor_user, apprentice, active=active)
    act_as_bound(mentor_user)

    r = client.post("/mentor/seats/purchase", json={
        "subscription_id": "sub_1", "product_id": "mentor_gift_seat_monthly", "apprentice_id": apprentice.id,
    })

    assert r.status_code == 200, r.text
    db_session.expire_all()
    seat = db_session.query(MentorPremiumSeat).filter_by(mentor_id=mentor_user.id).one()
    if active:
        assert seat.apprentice_id == apprentice.id and seat.is_redeemed is True
    else:
        assert seat.apprentice_id is None


def test_mentor_cannot_redeem_gift_code(client, db_session, act_as_bound, mentor_user, make_user, make_seat):
    other_mentor = make_user("mentor")
    seat = make_seat(mentor_user)
    act_as_bound(other_mentor)

    r = client.post("/apprentice/redeem-code", json={"code": seat.redemption_code})

    assert r.status_code == 403
    assert _seat(db_session, seat.id).is_redeemed is False


def test_apprentice_redeems_gift_code_without_emails_in_logs(client, db_session, act_as_bound, mentor_user, make_user, make_seat, caplog):
    import logging
    apprentice = make_user("apprentice", email="apprentice-secret@example.com")
    seat = make_seat(mentor_user)
    act_as_bound(apprentice)

    with caplog.at_level(logging.INFO):
        r = client.post("/apprentice/redeem-code", json={"code": seat.redemption_code})

    assert r.status_code == 200, r.text
    assert r.json()["success"] is True
    assert _seat(db_session, seat.id).is_redeemed is True
    assert apprentice.email not in caplog.text
    assert mentor_user.email not in caplog.text


# ---- Revoking agreements must not end an unrelated mentorship ----

@pytest.fixture
def agreement_emails(monkeypatch):
    sent = []
    import app.routes.agreements as agreements_routes
    monkeypatch.setattr(agreements_routes, "send_agreement_email", lambda event, to_email, context=None: sent.append((event, to_email)))
    return sent


def test_revoking_a_draft_deletes_it_and_keeps_the_mentorship(client, db_session, act_as, make_user, connect, make_agreement, agreement_emails):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    connect(mentor, apprentice)
    ag = make_agreement(mentor, apprentice.email, apprentice_id=apprentice.id, status="draft")
    act_as(mentor)

    r = client.post(f"/agreements/{ag.id}/revoke")
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] is True and r.json()["status"] == "revoked"
    assert _fresh(db_session, Agreement, ag.id) is None
    rel = db_session.query(MentorApprentice).filter_by(mentor_id=mentor.id, apprentice_id=apprentice.id).one()
    assert rel.active is True
    assert agreement_emails == []  # the apprentice never saw the draft


@pytest.mark.parametrize("status", ["awaiting_apprentice", "awaiting_parent"])
def test_revoking_an_unsigned_agreement_keeps_an_existing_mentorship(client, db_session, act_as, make_user, connect, make_agreement, agreement_emails, status):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    connect(mentor, apprentice)
    ag = make_agreement(mentor, apprentice.email, apprentice_id=apprentice.id, status=status)
    act_as(mentor)

    r = client.post(f"/agreements/{ag.id}/revoke")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "revoked" and r.json()["deleted"] is False
    assert _fresh(db_session, Agreement, ag.id).status == "revoked"
    rel = db_session.query(MentorApprentice).filter_by(mentor_id=mentor.id, apprentice_id=apprentice.id).one()
    assert rel.active is True


def test_revoking_a_signed_agreement_still_ends_the_mentorship(client, db_session, act_as, make_user, connect, make_agreement, agreement_emails):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    connect(mentor, apprentice)
    ag = make_agreement(mentor, apprentice.email, apprentice_id=apprentice.id, status="fully_signed")
    act_as(mentor)

    r = client.post(f"/agreements/{ag.id}/revoke")
    assert r.status_code == 200, r.text
    rel = db_session.query(MentorApprentice).filter_by(mentor_id=mentor.id, apprentice_id=apprentice.id).one()
    db_session.refresh(rel)
    assert rel.active is False
    assert len(agreement_emails) == 2  # apprentice and mentor are told


# ---- Emailed-link signing notifies the mentor like in-app signing ----

@pytest.fixture
def pushes(monkeypatch):
    sent = []
    import app.routes.agreements as agreements_routes
    monkeypatch.setattr(agreements_routes, "notify_agreement_signed",
                        lambda db, user_id, signer_name, agreement_status: sent.append((user_id, signer_name, agreement_status)))
    return sent


def _token(db_session, ag, token_type):
    from app.models.agreement import AgreementToken
    t = AgreementToken(token=str(uuid.uuid4()), agreement_id=ag.id, token_type=token_type,
                       expires_at=datetime.now(UTC) + timedelta(days=7))
    db_session.add(t)
    db_session.commit()
    return t.token


def test_parent_signing_by_link_notifies_the_mentor(client, db_session, make_user, make_agreement, agreement_emails, pushes):
    from app.models.notification import Notification

    mentor, apprentice = make_user("mentor"), make_user("apprentice", name="Sam Minor")
    ag = make_agreement(mentor, apprentice.email, apprentice_id=apprentice.id, status="awaiting_parent",
                        apprentice_name="Sam Minor", parent_required=True, parent_email="parent@example.com",
                        apprentice_signed_at=datetime.now(UTC))
    r = client.post(f"/agreements/public/{_token(db_session, ag, 'parent')}/sign", json={"typed_name": "Pat Parent"})
    assert r.status_code == 200 and r.json()["status"] == "fully_signed", r.text

    notes = db_session.query(Notification).filter_by(user_id=mentor.id).all()
    assert len(notes) == 1 and "parent/guardian" in notes[0].message and "now active" in notes[0].message
    assert any(to == mentor.email for _, to in agreement_emails)  # "fully signed" email to the mentor
    assert pushes == [(mentor.id, "Sam Minor's parent/guardian", "fully_signed")]


def test_apprentice_signing_by_link_notifies_the_mentor(client, db_session, make_user, make_agreement, agreement_emails, pushes):
    from app.models.notification import Notification

    mentor, apprentice = make_user("mentor"), make_user("apprentice", name="Alex")
    ag = make_agreement(mentor, apprentice.email, apprentice_id=apprentice.id, status="awaiting_apprentice",
                        apprentice_name="Alex", parent_required=False)
    r = client.post(f"/agreements/public/{_token(db_session, ag, 'apprentice')}/sign", json={"typed_name": "Alex"})
    assert r.status_code == 200 and r.json()["status"] == "fully_signed", r.text

    assert db_session.query(Notification).filter_by(user_id=mentor.id).count() == 1
    assert any(to == mentor.email for _, to in agreement_emails)
    assert pushes == [(mentor.id, "Alex", "fully_signed")]
