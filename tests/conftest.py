import random
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import Base, get_db
from app.models.user import User, UserRole
from app.models.mentor_apprentice import MentorApprentice
from app.services.auth import get_current_user
import uuid
from datetime import datetime, UTC
import os
from uuid import uuid4

os.environ["ENV"] = "test"

# Use SQLite in-memory for test DB
TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
# For in-memory SQLite we must use a StaticPool so multiple connections share the
# same in-memory database during the test run. Otherwise each connection gets
# an isolated empty in-memory DB which breaks tests that use separate sessions
# (e.g. TestClient requests vs test DB setup).
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_test_db():
    # recreate schema for each test to ensure isolation
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# ensure the app uses the testing DB session factory
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    return TestClient(app)

class MockUser:
    def __init__(self, role):
        # role may be passed in as a string like 'mentor' — store as UserRole
        self.id = str(uuid.uuid4())
        self.name = f"{str(role).title()} User"
        self.email = f"{role}@example.com"
        # ensure the mock user's role matches the UserRole enum used by auth
        try:
            self.role = UserRole(role)
        except Exception:
            # if already an enum, keep it
            self.role = role

@pytest.fixture
def mock_admin(monkeypatch):
    user = MockUser(role="admin")
    def _get_mock_admin():
        return user
    # ensure FastAPI dependency uses the mock user
    app.dependency_overrides[get_current_user] = lambda: user
    return user.id

@pytest.fixture
def mock_apprentice(monkeypatch):
    user = MockUser(role="apprentice")
    def _get_mock_apprentice():
        return user
    app.dependency_overrides[get_current_user] = lambda: user
    return user.id

@pytest.fixture
def mock_mentor(monkeypatch):
    user = MockUser(role="mentor")
    def _get_mock_mentor():
        return user
    app.dependency_overrides[get_current_user] = lambda: user
    return user.id

@pytest.fixture
def mentor_user(db_session):
    email = f"user+{uuid4().hex[:8]}@example.com"
    user = User(
        id=str(uuid4()),
        name="Mentor One",
        email=email,
        role="mentor",
        created_at=datetime.now(UTC)
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def apprentice_user(db_session):
    email = f"user+{uuid4().hex[:8]}@example.com"
    user = User(
        id=str(uuid4()),
        name="Apprentice One",
        email=email,
        role="apprentice",
        created_at=datetime.now(UTC)
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def mentor_apprentice_link(db_session, mentor_user, apprentice_user):
    link = MentorApprentice(apprentice_id=apprentice_user.id, mentor_id=mentor_user.id)
    db_session.add(link)
    db_session.commit()
    return link

@pytest.fixture
def db_session():
    # use the testing session factory bound to the in-memory SQLite engine
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture
def test_db(db_session):
    return db_session