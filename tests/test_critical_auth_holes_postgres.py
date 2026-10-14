"""specs/009: a legacy re-link blocked by real Postgres foreign keys.

SQLite in the default suite doesn't enforce foreign keys, so this only runs against a
migrated Postgres database (same setup as tests/test_account_deletion_postgres.py):

    TEST_POSTGRES_URL=postgresql://localhost/trooth_fk pytest tests/test_critical_auth_holes_postgres.py
"""
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.assessment import Assessment
from app.models.user import User, UserRole
from app.services.auth import find_account_for_token

PG_URL = os.getenv("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="TEST_POSTGRES_URL not set")


@pytest.fixture
def pg():
    engine = create_engine(PG_URL)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_relink_of_account_with_linked_data_is_blocked(pg):
    user = User(id=str(uuid4()), name="Legacy", email=f"legacy-{uuid4().hex[:8]}@example.com",
                role=UserRole.mentor, created_at=datetime.now(UTC))
    pg.add(user)
    pg.commit()
    assessment = Assessment(apprentice_id=user.id, answers={})
    pg.add(assessment)
    pg.commit()
    old_id, email = user.id, user.email
    try:
        found, outcome = find_account_for_token(pg, {"uid": f"new-{uuid4().hex}", "email": email, "email_verified": True})
        assert (found, outcome) == (None, "relink_blocked")
        pg.expire_all()
        assert pg.get(User, old_id) is not None  # rolled back, id unchanged
    finally:
        pg.rollback()
        pg.query(Assessment).filter_by(id=assessment.id).delete()
        pg.query(User).filter_by(id=old_id).delete()
        pg.commit()
