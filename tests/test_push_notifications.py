"""Tests for push notification endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.models.device_token import DeviceToken, DevicePlatform
from app.models.user import User, UserRole
from app.services.auth import get_current_user


class TestPushNotificationEndpoints:
    """Test push notification registration and management."""

    def test_register_device_success(self, client, mentor_user, db_session):
        """Test successful device registration."""
        # Override auth to return our mentor user
        app.dependency_overrides[get_current_user] = lambda: mentor_user
        
        response = client.post(
            "/push-notifications/register-device",
            json={
                "fcm_token": "test-fcm-token-12345",
                "platform": "ios",
                "device_name": "iPhone Test"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == mentor_user.id
        assert data["platform"] == "ios"
        assert data["device_name"] == "iPhone Test"
        assert "registered" in data["message"].lower() or "Device" in data["message"]

    def test_register_device_update_existing(self, client, mentor_user, db_session):
        """Test that registering same token updates it."""
        app.dependency_overrides[get_current_user] = lambda: mentor_user
        
        # First registration
        client.post(
            "/push-notifications/register-device",
            json={
                "fcm_token": "test-fcm-token-update",
                "platform": "android",
                "device_name": "Pixel Test"
            }
        )
        
        # Second registration with same token
        response = client.post(
            "/push-notifications/register-device",
            json={
                "fcm_token": "test-fcm-token-update",
                "platform": "android",
                "device_name": "Pixel Updated"
            }
        )
        assert response.status_code == 200
        assert "updated" in response.json()["message"].lower()

    def test_unregister_device(self, client, mentor_user, db_session):
        """Test device unregistration."""
        app.dependency_overrides[get_current_user] = lambda: mentor_user
        
        # Register first
        client.post(
            "/push-notifications/register-device",
            json={
                "fcm_token": "test-fcm-token-unregister",
                "platform": "ios"
            }
        )
        
        # Unregister
        response = client.post(
            "/push-notifications/unregister-device",
            json={"fcm_token": "test-fcm-token-unregister"}
        )
        assert response.status_code == 200
        assert response.json()["found"] is True

    def test_unregister_nonexistent_device(self, client, mentor_user):
        """Test unregistering a device that doesn't exist."""
        app.dependency_overrides[get_current_user] = lambda: mentor_user
        
        response = client.post(
            "/push-notifications/unregister-device",
            json={"fcm_token": "nonexistent-token"}
        )
        assert response.status_code == 200
        assert response.json()["found"] is False

    def test_list_my_devices(self, client, mentor_user, db_session):
        """Test listing user's registered devices."""
        app.dependency_overrides[get_current_user] = lambda: mentor_user
        
        # Register a device
        client.post(
            "/push-notifications/register-device",
            json={
                "fcm_token": "test-fcm-token-list",
                "platform": "ios",
                "device_name": "Test iPhone"
            }
        )
        
        response = client.get("/push-notifications/my-devices")
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) >= 1
        assert any(d["device_name"] == "Test iPhone" for d in devices)


class TestScheduledTasks:
    """Test scheduled task endpoints."""

    def test_weekly_tips_requires_cron_secret(self, client):
        """Test that weekly tips endpoint requires cron secret."""
        response = client.post("/scheduled/weekly-tips")
        assert response.status_code == 403

    def test_weekly_tips_invalid_secret(self, client):
        """Test that invalid cron secret is rejected."""
        response = client.post(
            "/scheduled/weekly-tips",
            headers={"X-Cron-Secret": "wrong-secret"}
        )
        assert response.status_code == 403

    def test_weekly_tips_with_valid_secret(self, client, db_session):
        """Test weekly tips with valid cron secret."""
        # Patch the CRON_SECRET to a known value
        with patch("app.routes.scheduled_tasks.CRON_SECRET", "test-secret"):
            response = client.post(
                "/scheduled/weekly-tips",
                headers={"X-Cron-Secret": "test-secret"}
            )
        assert response.status_code == 200
        data = response.json()
        assert "week_number" in data
        assert "mentor_count" in data
        assert "apprentice_count" in data


class TestPushNotificationService:
    """Test the push notification service logic."""

    def test_fcm_not_available_gracefully_handled(self, db_session, mentor_user):
        """Test that service handles FCM not being initialized."""
        from app.services.push_notification import PushNotificationService
        from app.schemas.push_notification import PushNotificationPayload
        
        payload = PushNotificationPayload(
            title="Test",
            body="Test body"
        )
        
        # FCM is not initialized in test environment, should not crash
        result = PushNotificationService.send_to_user(db_session, mentor_user.id, payload)
        
        # Should return gracefully with a message
        assert "FCM not configured" in result.get("message", "") or result.get("success_count", 0) == 0

    def test_data_conversion_to_strings(self):
        """Test that data payload values are converted to strings."""
        from app.services.push_notification import _convert_data_to_strings
        
        data = {
            "type": "test",
            "count": 42,
            "flag": True,
        }
        
        result = _convert_data_to_strings(data)
        
        assert result["type"] == "test"
        assert result["count"] == "42"
        assert result["flag"] == "True"
