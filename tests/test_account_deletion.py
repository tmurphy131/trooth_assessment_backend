"""Tests for account deletion endpoints."""
import pytest
from uuid import uuid4
from datetime import datetime, UTC
from app.models.user import User, UserRole


@pytest.fixture
def apprentice_headers(apprentice_user, client):
    from app.services.auth import get_current_user
    class _User:
        id = apprentice_user.id
        role = apprentice_user.role
        email = apprentice_user.email
        name = apprentice_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _User()
    return {"Authorization": f"Bearer mock-{apprentice_user.id}"}


@pytest.fixture
def mentor_headers(mentor_user, client):
    from app.services.auth import get_current_user
    class _User:
        id = mentor_user.id
        role = mentor_user.role
        email = mentor_user.email
        name = mentor_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _User()
    return {"Authorization": f"Bearer mock-{mentor_user.id}"}


@pytest.fixture
def admin_user(db_session):
    email = f"admin+{uuid4().hex[:8]}@example.com"
    user = User(
        id=str(uuid4()),
        name="Admin User",
        email=email,
        role=UserRole.admin,
        created_at=datetime.now(UTC)
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_headers(admin_user, client):
    from app.services.auth import get_current_user
    class _User:
        id = admin_user.id
        role = admin_user.role
        email = admin_user.email
        name = admin_user.name
    client.app.dependency_overrides[get_current_user] = lambda: _User()
    return {"Authorization": f"Bearer mock-{admin_user.id}"}


def test_get_deletion_summary_apprentice(client, apprentice_headers):
    """Test that apprentice can get deletion summary."""
    response = client.get("/users/me/deletion-summary", headers=apprentice_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items_to_delete" in data
    assert "role" in data
    assert data["role"] == "apprentice"


def test_get_deletion_summary_mentor(client, mentor_headers):
    """Test that mentor can get deletion summary."""
    response = client.get("/users/me/deletion-summary", headers=mentor_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items_to_delete" in data
    assert "role" in data
    assert data["role"] == "mentor"


def test_close_account_without_confirmation(client, apprentice_headers):
    """Test that account deletion fails without proper confirmation."""
    import json
    response = client.request(
        "DELETE",
        "/users/me/close-account",
        content=json.dumps({"confirmation_text": "wrong"}),
        headers={**apprentice_headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert "DELETE" in response.json()["detail"]


def test_close_account_apprentice(client, db_session, apprentice_headers, apprentice_user):
    """Test that apprentice can close their account."""
    import json
    # Store user ID before deletion
    user_id = apprentice_user.id
    
    # Verify user exists before deletion
    user_before = db_session.query(User).filter(User.id == user_id).first()
    assert user_before is not None

    response = client.request(
        "DELETE",
        "/users/me/close-account",
        content=json.dumps({"confirmation_text": "DELETE"}),
        headers={**apprentice_headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()

    # Verify user is deleted
    db_session.expire_all()
    user_after = db_session.query(User).filter(User.id == user_id).first()
    assert user_after is None


def test_close_account_mentor(client, db_session, mentor_headers, mentor_user):
    """Test that mentor can close their account."""
    import json
    # Store user ID before deletion
    user_id = mentor_user.id
    
    # Verify user exists before deletion
    user_before = db_session.query(User).filter(User.id == user_id).first()
    assert user_before is not None

    response = client.request(
        "DELETE",
        "/users/me/close-account",
        content=json.dumps({"confirmation_text": "DELETE"}),
        headers={**mentor_headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()

    # Verify user is deleted
    db_session.expire_all()
    user_after = db_session.query(User).filter(User.id == user_id).first()
    assert user_after is None


def test_close_account_admin_fails(client, admin_headers):
    """Test that admin accounts cannot be closed through this endpoint."""
    import json
    response = client.request(
        "DELETE",
        "/users/me/close-account",
        content=json.dumps({"confirmation_text": "DELETE"}),
        headers={**admin_headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()
