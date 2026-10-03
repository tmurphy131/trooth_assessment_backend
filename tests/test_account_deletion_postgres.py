"""Account deletion against real Postgres foreign keys.

The default suite runs on SQLite, which doesn't enforce foreign keys, so a
table that references users.id but isn't cleaned up by account deletion
passes there and only fails in production. These tests run against a
migrated Postgres database when TEST_POSTGRES_URL is set, e.g.:

    createdb trooth_fk
    DATABASE_URL=postgresql://localhost/trooth_fk alembic upgrade head
    TEST_POSTGRES_URL=postgresql://localhost/trooth_fk pytest tests/test_account_deletion_postgres.py
"""
import os
from datetime import datetime, UTC
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User, UserRole
from app.models.mentor_apprentice import MentorApprentice
from app.models.email_send_event import EmailSendEvent
from app.models.subscription_event import SubscriptionEvent
from app.models.mentor_premium_seat import MentorPremiumSeat
from app.models.prayer_entry import PrayerEntry
from app.models.trivia import (
    TriviaSingleScore, TriviaBadge, TriviaChallenge, TriviaCompetition,
    TriviaCompetitionWinner, TriviaCategory, TriviaDifficulty, TriviaChallengeStatus,
)
from app.services.account_deletion import delete_user_account

PG_URL = os.getenv("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="TEST_POSTGRES_URL not set")


@pytest.fixture
def pg():
    engine = create_engine(PG_URL)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _user(db, role):
    u = User(id=str(uuid4()), name=f"{role.value} {uuid4().hex[:4]}",
             email=f"{role.value}-{uuid4().hex[:8]}@example.com", role=role,
             created_at=datetime.now(UTC))
    db.add(u)
    db.commit()
    return u


def _trivia_history(db, user, opponent, comp):
    db.add_all([
        TriviaSingleScore(user_id=user.id, category=TriviaCategory.old_testament,
                          difficulty=TriviaDifficulty.challenger, score=1200,
                          streak_length=12, correct_count=12),
        TriviaBadge(user_id=user.id, badge_type="faithful_disciple", streak_at_earn=10),
        TriviaChallenge(challenger_id=user.id, challenged_id=opponent.id,
                        category=TriviaCategory.new_testament, difficulty=TriviaDifficulty.beginner,
                        num_questions=20, question_ids=[], status=TriviaChallengeStatus.complete,
                        winner_id=user.id),
        TriviaChallenge(challenger_id=opponent.id, challenged_id=user.id,
                        category=TriviaCategory.new_testament, difficulty=TriviaDifficulty.beginner,
                        num_questions=20, question_ids=[], status=TriviaChallengeStatus.pending),
        TriviaCompetitionWinner(competition_id=comp.id, user_id=user.id, display_name=user.name,
                                place=1, score=1200, discount_code="TROOTH-1ST-TEST01"),
    ])
    # Campaign emails are logged with the user as both sender and target
    db.add(EmailSendEvent(sender_user_id=user.id, target_user_id=user.id,
                          purpose="engagement", campaign_type="welcome"))
    db.add(SubscriptionEvent(user_id=user.id, event_type="initial_purchase"))
    db.commit()


@pytest.fixture
def comp(pg):
    c = TriviaCompetition(slug=f"test-{uuid4().hex[:8]}", name="Test", difficulty="challenger",
                          starts_at=datetime(2026, 11, 1, tzinfo=UTC), ends_at=datetime(2026, 12, 31, tzinfo=UTC),
                          prizes=[{"place": 1, "amount": 59, "label": "x"}], code_valid_days=90)
    pg.add(c)
    pg.commit()
    return c


def test_delete_apprentice_with_trivia_and_campaign_history(pg, comp):
    apprentice = _user(pg, UserRole.apprentice)
    mentor = _user(pg, UserRole.mentor)
    pg.add(MentorApprentice(mentor_id=mentor.id, apprentice_id=apprentice.id))
    pg.add(PrayerEntry(apprentice_id=apprentice.id, title="Peace"))
    pg.add(MentorPremiumSeat(mentor_id=mentor.id, apprentice_id=apprentice.id, is_redeemed=True,
                             apprentice_email=apprentice.email))
    pg.commit()
    _trivia_history(pg, apprentice, mentor, comp)
    apprentice_id = apprentice.id

    result = delete_user_account(pg, apprentice)
    pg.expire_all()

    assert result["success"] is True
    assert pg.get(User, apprentice_id) is None
    assert pg.get(User, mentor.id) is not None
    assert pg.query(TriviaSingleScore).filter_by(user_id=apprentice_id).count() == 0
    assert pg.query(TriviaChallenge).filter(
        (TriviaChallenge.challenger_id == apprentice_id) | (TriviaChallenge.challenged_id == apprentice_id)
    ).count() == 0
    # Podium survives without the account
    winner = pg.query(TriviaCompetitionWinner).filter_by(competition_id=comp.id).one()
    assert winner.user_id is None and winner.display_name
    # Mentor keeps the gift seat, freed for reuse
    seat = pg.query(MentorPremiumSeat).filter_by(mentor_id=mentor.id).one()
    assert seat.apprentice_id is None and seat.is_redeemed is False


def test_delete_mentor_with_trivia_and_gift_seats(pg, comp):
    mentor = _user(pg, UserRole.mentor)
    apprentice = _user(pg, UserRole.apprentice)
    pg.add(MentorApprentice(mentor_id=mentor.id, apprentice_id=apprentice.id))
    pg.add(MentorPremiumSeat(mentor_id=mentor.id, apprentice_id=apprentice.id, is_redeemed=True))
    pg.add(SubscriptionEvent(user_id=apprentice.id, event_type="gift_seat_assigned",
                             triggered_by_user_id=mentor.id))
    pg.commit()
    _trivia_history(pg, mentor, apprentice, comp)
    mentor_id = mentor.id

    result = delete_user_account(pg, mentor)
    pg.expire_all()

    assert result["success"] is True
    assert pg.get(User, mentor_id) is None
    assert pg.get(User, apprentice.id) is not None
    assert pg.query(MentorPremiumSeat).filter_by(mentor_id=mentor_id).count() == 0
    # The apprentice's own subscription history stays, minus the link to the mentor
    event = pg.query(SubscriptionEvent).filter_by(user_id=apprentice.id).one()
    assert event.triggered_by_user_id is None
