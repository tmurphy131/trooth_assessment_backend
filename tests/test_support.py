"""Tests for support request endpoint."""
import pytest
from unittest.mock import patch, MagicMock


def test_submit_support_request_success(client, mentor_user):
    """Test submitting a support request as an authenticated user."""
    with patch('app.routes.support._send_support_emails') as mock_email:
        mock_email.return_value = None
        
        response = client.post(
            "/support/submit",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "topic": "Technical Bug",
                "message": "I found a bug in the app.",
                "source": "app"
            },
            headers={"Authorization": f"Bearer {mentor_user.id}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "submitted" in data["message"].lower()


def test_submit_support_request_unauthenticated(client):
    """Test submitting a support request without authentication (website)."""
    with patch('app.routes.support._send_support_emails') as mock_email:
        mock_email.return_value = None
        
        response = client.post(
            "/support/submit",
            json={
                "name": "Website User",
                "email": "website@example.com",
                "topic": "Account Issues",
                "message": "I need help with my account.",
                "source": "website"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


def test_submit_support_request_honeypot_filled(client):
    """Test that honeypot filled submissions are silently rejected."""
    response = client.post(
        "/support/submit",
        json={
            "name": "Bot User",
            "email": "bot@example.com",
            "topic": "Other",
            "message": "I am a bot.",
            "source": "website",
            "website": "http://spam.com"  # Honeypot field filled = bot
        }
    )
    
    # Should return success to not tip off bots, but won't actually send
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_submit_support_request_missing_fields(client):
    """Test validation for missing required fields."""
    response = client.post(
        "/support/submit",
        json={
            "name": "Test User",
            # Missing email, topic, message
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_submit_support_request_invalid_email(client):
    """Test validation for invalid email format."""
    response = client.post(
        "/support/submit",
        json={
            "name": "Test User",
            "email": "not-an-email",
            "topic": "Other",
            "message": "Test message"
        }
    )
    
    assert response.status_code == 422  # Validation error
