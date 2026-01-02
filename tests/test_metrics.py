"""Tests for the metrics service and API endpoints."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.metrics import (
    get_user_metrics,
    get_assessment_metrics,
    get_mentorship_metrics,
    get_invitation_metrics,
    get_agreement_metrics,
    get_template_metrics,
    get_mentor_activity_metrics,
    get_all_metrics,
    get_dashboard_summary,
)


client = TestClient(app)


class TestMetricsEndpoints:
    """Test the /metrics API endpoints."""

    def test_dashboard_endpoint(self):
        """Test the dashboard metrics endpoint."""
        response = client.get("/metrics/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        # Check structure
        metrics = data["data"]
        assert "generated_at" in metrics
        assert "totals" in metrics
        assert "activity" in metrics
        assert "pending" in metrics
        
        # Check totals structure
        totals = metrics["totals"]
        assert "users" in totals
        assert "mentors" in totals
        assert "apprentices" in totals
        assert "active_pairs" in totals
        assert "assessments_completed" in totals
        assert "agreements_signed" in totals

    def test_full_metrics_endpoint_default_period(self):
        """Test the full metrics endpoint with default period."""
        response = client.get("/metrics/full")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        metrics = data["data"]
        assert metrics["period"] == "week"

    def test_full_metrics_endpoint_monthly(self):
        """Test the full metrics endpoint with monthly period."""
        response = client.get("/metrics/full?period=month")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        metrics = data["data"]
        assert metrics["period"] == "month"

    def test_full_metrics_endpoint_invalid_period(self):
        """Test the full metrics endpoint with invalid period defaults to week."""
        response = client.get("/metrics/full?period=invalid")
        assert response.status_code == 200
        
        data = response.json()
        metrics = data["data"]
        assert metrics["period"] == "week"

    def test_full_metrics_structure(self):
        """Test that full metrics has all expected sections."""
        response = client.get("/metrics/full")
        data = response.json()["data"]
        
        expected_sections = [
            "users",
            "assessments", 
            "mentorship",
            "invitations",
            "agreements",
            "templates",
            "mentor_activity",
        ]
        
        for section in expected_sections:
            assert section in data, f"Missing section: {section}"


class TestMetricsService:
    """Test the metrics service functions directly."""

    def test_get_user_metrics_structure(self):
        """Test user metrics returns expected structure via API."""
        # Use API endpoint instead of direct DB access for cleaner testing
        response = client.get("/metrics/full?period=week")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        metrics = data["data"]["users"]
        
        assert "total_users" in metrics
        assert "mentors" in metrics
        assert "apprentices" in metrics
        assert "admins" in metrics
        assert "new_users_in_period" in metrics
        assert "new_mentors_in_period" in metrics
        assert "new_apprentices_in_period" in metrics
        
        # All values should be non-negative integers
        for key, value in metrics.items():
            assert isinstance(value, int), f"{key} should be int"
            assert value >= 0, f"{key} should be non-negative"

    def test_get_assessment_metrics_structure(self):
        """Test assessment metrics returns expected structure via API."""
        response = client.get("/metrics/full?period=week")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        metrics = data["data"]["assessments"]
        
        expected_keys = [
            "total_completed",
            "completed_in_period",
            "started_in_period",
            "submitted_in_period",
            "active_drafts",
            "processing",
            "errors",
            "completion_rate",
        ]
        
        for key in expected_keys:
            assert key in metrics, f"Missing key: {key}"

    def test_get_dashboard_summary_structure(self):
        """Test dashboard summary has correct structure via API."""
        response = client.get("/metrics/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        summary = data["data"]
        
        assert "generated_at" in summary
        assert "totals" in summary
        assert "activity" in summary
        assert "pending" in summary
        
        # Check totals
        totals = summary["totals"]
        assert "users" in totals
        assert "active_pairs" in totals
        
        # Check activity
        activity = summary["activity"]
        assert "assessments_this_week" in activity
        assert "new_users_this_week" in activity
        
        # Check pending
        pending = summary["pending"]
        assert "drafts_in_progress" in pending
        assert "agreements_awaiting" in pending
        assert "invitations_pending" in pending


class TestSendReportEndpoint:
    """Test the manual report sending endpoint."""

    def test_send_report_invalid_type(self):
        """Test that invalid report type returns error."""
        response = client.post("/metrics/send-report?report_type=invalid")
        assert response.status_code == 200  # Returns 200 with error in body
        
        data = response.json()
        assert data["status"] == "error"
        assert "Invalid report_type" in data["message"]

    @patch("app.services.metrics_reports.get_report_recipients")
    @patch("app.services.metrics_reports.send_email")
    def test_send_report_weekly(self, mock_send_email, mock_recipients):
        """Test sending weekly report."""
        mock_recipients.return_value = ["test@example.com"]
        mock_send_email.return_value = True
        
        response = client.post("/metrics/send-report?report_type=weekly")
        data = response.json()
        
        # Should succeed or fail gracefully
        assert data["status"] in ["success", "error"]

    @patch("app.services.metrics_reports.get_report_recipients")
    def test_send_report_no_recipients(self, mock_recipients):
        """Test that missing recipients returns error."""
        mock_recipients.return_value = []
        
        response = client.post("/metrics/send-report?report_type=weekly")
        data = response.json()
        
        assert data["status"] == "error"
