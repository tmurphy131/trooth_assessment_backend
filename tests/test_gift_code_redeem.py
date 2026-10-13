"""POST /apprentice/redeem-code with seats that have an expiry date.

Regression: seats store expires_at as a naive DateTime, and comparing it with an aware
"now" raised "can't compare offset-naive and offset-aware datetimes" (500 in prod).
"""
import uuid
from datetime import datetime, timedelta, UTC

import pytest
from fastapi import Depends

from app.db import get_db
from app.main import app
from app.models.mentor_premium_seat import MentorPremiumSeat
from app.models.user import User, SubscriptionTier
from app.services.auth import get_current_user


@pytest.fixture
def make_user(db_session):
    def _make(role):
        user = User(
            id=str(uuid.uuid4()), name=f"{role} {uuid.uuid4().hex[:4]}",
            email=f"{role}+{uuid.uuid4().hex[:8]}@example.com", role=role, created_at=datetime.now(UTC),
        )
        db_session.add(user)
        db_session.commit()
        return user
    return _make


@pytest.fixture
def act_as():
    """Load the user in the request's own session (the route commits user changes)."""
    def _set(user):
        user_id = user.id

        def _current(db=Depends(get_db)):
            return db.query(User).filter(User.id == user_id).first()

        app.dependency_overrides[get_current_user] = _current
    yield _set
    app.dependency_overrides.pop(get_current_user, None)


def _seat(db_session, mentor, expires_at):
    # Stored naive, as PostgreSQL TIMESTAMP WITHOUT TIME ZONE returns it.
    seat = MentorPremiumSeat(mentor_id=mentor.id, expires_at=expires_at)
    db_session.add(seat)
    db_session.commit()
    return seat


def _naive(dt):
    return dt.replace(tzinfo=None)


def test_redeem_seat_with_future_expiry(client, db_session, act_as, make_user):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    seat = _seat(db_session, mentor, _naive(datetime.now(UTC) + timedelta(days=30)))
    act_as(apprentice)

    r = client.post("/apprentice/redeem-code", json={"code": seat.redemption_code})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["expires_at"]
    db_session.expire_all()
    assert db_session.get(MentorPremiumSeat, seat.id).is_redeemed is True
    assert db_session.get(User, apprentice.id).subscription_tier == SubscriptionTier.mentor_gifted


def test_redeem_seat_with_past_expiry_says_expired(client, db_session, act_as, make_user):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    seat = _seat(db_session, mentor, _naive(datetime.now(UTC) - timedelta(days=1)))
    act_as(apprentice)

    r = client.post("/apprentice/redeem-code", json={"code": seat.redemption_code})

    assert r.status_code == 200, r.text
    assert r.json() == {**r.json(), "success": False, "message": "This code has expired."}
    db_session.expire_all()
    assert db_session.get(MentorPremiumSeat, seat.id).is_redeemed is False


def test_redeem_seat_without_expiry(client, db_session, act_as, make_user):
    mentor, apprentice = make_user("mentor"), make_user("apprentice")
    seat = _seat(db_session, mentor, None)
    act_as(apprentice)
    r = client.post("/apprentice/redeem-code", json={"code": seat.redemption_code})
    assert r.status_code == 200
    assert r.json()["success"] is True
