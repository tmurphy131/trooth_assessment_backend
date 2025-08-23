"""
Enhanced test configuration and fixtures.
"""
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db import get_db, Base
from app.core.settings import settings

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine with SQLite."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_url = f"sqlite:///{tmp.name}"
    
    engine = create_engine(
        test_db_url, 
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    
    # Cleanup
    try:
        os.unlink(tmp.name)
    except:
        pass

@pytest.fixture
def test_db(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    connection = test_engine.connect()
    transaction = connection.begin()
    
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_client(test_db):
    """Create test client with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_auth_headers():
    """Mock authentication headers for testing."""
    return {
        "Authorization": "Bearer mock-mentor-token"
    }

@pytest.fixture
def mock_admin_headers():
    """Mock admin authentication headers for testing."""
    return {
        "Authorization": "Bearer mock-admin-token"
    }

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "role": "mentor"
    }

@pytest.fixture
def sample_assessment_data():
    """Sample assessment data for testing."""
    return {
        "answers": {
            "q1": "I pray daily and read scripture regularly.",
            "q2": "I participate in weekly fellowship and serve others.",
            "q3": "I try to live according to biblical principles."
        }
    }

@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for testing."""
    # Set test environment variables
    original_env = os.environ.get("ENV")
    original_rate_limit = settings.rate_limit_enabled
    
    os.environ["ENV"] = "test"
    settings.rate_limit_enabled = False
    
    yield
    
    # Restore original values
    if original_env:
        os.environ["ENV"] = original_env
    else:
        os.environ.pop("ENV", None)
    settings.rate_limit_enabled = original_rate_limit

class MockOpenAIClient:
    """Mock OpenAI client for testing."""
    
    class Chat:
        class Completions:
            @staticmethod
            def create(**kwargs):
                class MockResponse:
                    choices = [
                        type('obj', (object,), {
                            'message': type('obj', (object,), {
                                'content': '{"overall_score": 8.5, "recommendation": "Continue your spiritual growth journey."}'
                            })()
                        })()
                    ]
                return MockResponse()
        
        completions = Completions()
    
    chat = Chat()

@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI client for testing."""
    def mock_get_client():
        return MockOpenAIClient()
    
    monkeypatch.setattr("app.services.ai_scoring.get_openai_client", mock_get_client)
    return MockOpenAIClient()

class MockSendGridClient:
    """Mock SendGrid client for testing."""
    
    def send(self, message):
        class MockResponse:
            status_code = 202
        return MockResponse()

@pytest.fixture
def mock_sendgrid_client(monkeypatch):
    """Mock SendGrid client for testing."""
    def mock_get_client():
        return MockSendGridClient()
    
    monkeypatch.setattr("app.services.email.get_sendgrid_client", mock_get_client)
    return MockSendGridClient()
