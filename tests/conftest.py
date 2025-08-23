import random
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db import Base, get_db
from app.models.user import User
from app.models.mentor_apprentice import MentorApprentice
from app.services.auth import get_current_user
import uuid
from datetime import datetime, UTC
import os
from uuid import uuid4

os.environ["ENV"] = "test"

# Use SQLite in-memory for test DB
TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    return TestClient(app)

class MockUser:
    def __init__(self, role):
        self.id = str(uuid.uuid4())
        self.name = f"{role.title()} User"
        self.email = f"{role}@example.com"
        self.role = role

@pytest.fixture
def mock_admin(monkeypatch):
    def _get_mock_admin():
        return MockUser(role="admin")
    monkeypatch.setattr("app.services.auth.get_current_user", _get_mock_admin)

@pytest.fixture
def mock_apprentice(monkeypatch):
    def _get_mock_apprentice():
        return MockUser(role="apprentice")
    monkeypatch.setattr("app.services.auth.get_current_user", _get_mock_apprentice)

@pytest.fixture
def mock_mentor(monkeypatch):
    def _get_mock_mentor():
        return MockUser(role="mentor")
    monkeypatch.setattr("app.services.auth.get_current_user", _get_mock_mentor)

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

from app.db import SessionLocal

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture
def test_db(db_session):
    return db_session