import pytest
from unittest.mock import patch

@patch("app.services.ai_scoring.client.chat.completions.create")
def test_scoring_stub(mock_create):
    mock_create.return_value.choices = [
        type("Choice", (), {"message": type("Msg", (), {"content": '{"q1": {"score": 7, "feedback": "...", "recommendation": "..."}}'})})
    ]
    from app.services.ai_scoring import score_assessment
    result = score_assessment({"q1": "I pray"})
    assert "q1" in result