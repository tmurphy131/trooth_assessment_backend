import pytest
from unittest.mock import patch
from app.services import email


@pytest.fixture
def mock_sendgrid_client():
    with patch("app.services.email.SendGridAPIClient") as mock_client:
        instance = mock_client.return_value
        instance.send.return_value.status_code = 202
        yield instance


def test_send_assessment_email_success(mock_sendgrid_client):
    status = email.send_assessment_email(
        to_email="mentor@example.com",
        apprentice_name="John Doe",
        assessment_title="Spiritual Growth",
        score=85,
        feedback_summary="Excellent overall faith and obedience.",
        details={
            "Faith": {
                "score": 9,
                "feedback": "Strong prayer life and deep knowledge of Scripture.",
                "recommendation": "Encourage them to mentor others."
            },
            "Obedience": {
                "score": 8,
                "feedback": "Shows spiritual discipline and consistency.",
                "recommendation": "Challenge them to take on a leadership role."
            }
        }
    )
    assert status == 202
    mock_sendgrid_client.send.assert_called_once()


def test_send_invitation_email_success(mock_sendgrid_client):
    email.send_invitation_email(
        to_email="apprentice@example.com",
        apprentice_name="Jane Smith",
        token="mocktoken123"
    )
    mock_sendgrid_client.send.assert_called_once()
