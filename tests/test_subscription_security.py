"""Security regressions for subscription and free-tier gating."""
from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest
from fastapi import Depends

from app.main import app
from app.db import get_db
from app.core.settings import settings
from app.models.user import User, SubscriptionTier
from app.models.mentor_apprentice import MentorApprentice
from app.services.auth import get_current_user


@pytest.fixture(autouse=True)
def _clear_auth_override():
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _premium_override_off(monkeypatch):
    monkeypatch.setattr(settings, "premium_features_enabled", False)


def _user(db, role, created_at=None, **extra):
    user = User(
        id=str(uuid4()),
        name=f"{role} {uuid4().hex[:4]}",
        email=f"{uuid4().hex[:8]}@example.com",
        role=role,
        created_at=created_at or datetime.now(UTC),
        **extra,
    )
    db.add(user)
    db.commit()
    return user


def _as(user):
    # Load the user in the request's own session, like the real dependency,
    # so routes can commit/refresh it.
    user_id = user.id

    def _current(db=Depends(get_db)):
        return db.query(User).filter(User.id == user_id).first()

    app.dependency_overrides[get_current_user] = _current


# --- /subscriptions/admin/set-tier ------------------------------------------

def test_set_tier_rejects_non_admin(client, db_session):
    _as(_user(db_session, "mentor"))
    r = client.post("/subscriptions/admin/set-tier", json={"tier": "mentor_premium", "expires_days": 9999})
    assert r.status_code == 403


def test_set_tier_disabled_in_production(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    _as(_user(db_session, "admin"))
    r = client.post("/subscriptions/admin/set-tier", json={"tier": "mentor_premium"})
    assert r.status_code == 403


# --- free-tier apprentice limit ----------------------------------------------

@pytest.fixture
def mentor_with_two_apprentices(db_session):
    mentor = _user(db_session, "mentor")
    first = _user(db_session, "apprentice", created_at=datetime.now(UTC) - timedelta(days=10))
    second = _user(db_session, "apprentice", created_at=datetime.now(UTC))
    for a in (first, second):
        db_session.add(MentorApprentice(mentor_id=mentor.id, apprentice_id=a.id, active=True))
    db_session.commit()
    return mentor, first, second


def test_my_apprentices_ordered_oldest_first(client, mentor_with_two_apprentices):
    mentor, first, second = mentor_with_two_apprentices
    _as(mentor)
    r = client.get("/mentor/my-apprentices")
    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == [first.id, second.id]


def test_free_mentor_blocked_from_second_apprentice(client, mentor_with_two_apprentices):
    mentor, first, second = mentor_with_two_apprentices
    _as(mentor)
    assert client.get(f"/mentor/apprentice/{first.id}/submitted-assessments").status_code == 200
    assert client.get(f"/mentor/apprentice/{second.id}/submitted-assessments").status_code == 403


def test_premium_mentor_sees_all_apprentices(client, db_session, mentor_with_two_apprentices):
    mentor, _, second = mentor_with_two_apprentices
    mentor.subscription_tier = SubscriptionTier.mentor_premium
    mentor.subscription_expires_at = datetime.now(UTC) + timedelta(days=30)
    db_session.commit()
    _as(mentor)
    assert client.get(f"/mentor/apprentice/{second.id}/submitted-assessments").status_code == 200


def test_grandfathered_mentor_sees_all_apprentices(client, db_session, mentor_with_two_apprentices):
    mentor, _, second = mentor_with_two_apprentices
    mentor.is_grandfathered_mentor = True
    db_session.commit()
    _as(mentor)
    assert client.get(f"/mentor/apprentice/{second.id}/submitted-assessments").status_code == 200


# --- purchases are verified with RevenueCat, not the client -------------------

from app.services import revenuecat
from app.models.mentor_premium_seat import MentorPremiumSeat


def _fake_customer(monkeypatch, customer=None, unavailable=False):
    def fetch(app_user_id):
        if unavailable:
            raise revenuecat.RevenueCatUnavailable("not configured")
        return customer
    monkeypatch.setattr(revenuecat, "fetch_customer", fetch)


CLAIM = {"is_active": True, "product_id": "mentor_premium_monthly", "expiration_date": "2099-01-01T00:00:00Z", "store": "APP_STORE"}


def test_restore_ignores_client_claimed_premium(client, db_session, monkeypatch):
    _fake_customer(monkeypatch, revenuecat.VerifiedCustomer(premium=None))
    user = _user(db_session, "mentor")
    _as(user)
    r = client.post("/subscriptions/restore", json=CLAIM)
    assert r.status_code == 200
    assert r.json()["current_status"]["has_premium"] is False


def test_restore_grants_nothing_when_revenuecat_unavailable(client, db_session, monkeypatch):
    _fake_customer(monkeypatch, unavailable=True)
    _as(_user(db_session, "mentor"))
    r = client.post("/subscriptions/restore", json=CLAIM)
    assert r.status_code == 200
    assert r.json()["current_status"]["has_premium"] is False


def test_restore_grants_verified_premium(client, db_session, monkeypatch):
    expires = datetime.now(UTC) + timedelta(days=30)
    _fake_customer(monkeypatch, revenuecat.VerifiedCustomer(
        premium=revenuecat.VerifiedEntitlement("mentor_premium_monthly", expires, "app_store")))
    _as(_user(db_session, "mentor"))
    r = client.post("/subscriptions/restore")
    assert r.status_code == 200
    assert r.json()["current_status"]["has_premium"] is True


def test_seat_confirm_rejects_unverified_purchase(client, db_session, monkeypatch):
    _fake_customer(monkeypatch, revenuecat.VerifiedCustomer(premium=None, gift_seat_purchases=0))
    mentor = _user(db_session, "mentor")
    _as(mentor)
    r = client.post("/mentor/seats/purchase", json={"subscription_id": "made_up_123", "product_id": "mentor_gift_seat_monthly"})
    assert r.status_code == 409
    assert db_session.query(MentorPremiumSeat).filter_by(mentor_id=mentor.id).count() == 0


def test_seat_confirm_creates_seat_for_verified_purchase(client, db_session, monkeypatch):
    _fake_customer(monkeypatch, revenuecat.VerifiedCustomer(premium=None, gift_seat_purchases=1))
    mentor = _user(db_session, "mentor")
    _as(mentor)
    r = client.post("/mentor/seats/purchase", json={"subscription_id": "sub_1", "product_id": "mentor_gift_seat_monthly"})
    assert r.status_code == 200
    # A second confirm for the same single purchase can't mint another seat.
    r2 = client.post("/mentor/seats/purchase", json={"subscription_id": "sub_2", "product_id": "mentor_gift_seat_monthly"})
    assert r2.status_code == 409


def test_parse_subscriber():
    now = datetime(2026, 10, 1, tzinfo=UTC)
    payload = {"subscriber": {
        "entitlements": {"premium": {"expires_date": "2026-11-01T00:00:00Z", "product_identifier": "mentor_premium_monthly"}},
        "subscriptions": {
            "mentor_premium_monthly": {"expires_date": "2026-11-01T00:00:00Z", "store": "app_store"},
            "mentor_gift_seat_monthly": {"expires_date": "2026-10-15T00:00:00Z", "store": "app_store"},
            "mentor_gift_seat_yearly": {"expires_date": "2026-09-01T00:00:00Z", "store": "app_store"},  # expired
        },
        "non_subscriptions": {"gift_seat_onetime": [{"id": "a"}, {"id": "b"}]},
    }}
    c = revenuecat.parse_subscriber(payload, now=now)
    assert c.premium.product_id == "mentor_premium_monthly"
    assert c.premium.store == "app_store"
    assert c.gift_seat_purchases == 3

    expired = {"subscriber": {"entitlements": {"premium": {"expires_date": "2026-09-01T00:00:00Z", "product_identifier": "x"}}}}
    assert revenuecat.parse_subscriber(expired, now=now).premium is None
