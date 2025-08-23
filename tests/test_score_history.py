import pytest
from uuid import uuid4
from app.models import User, Assessment, AssessmentScoreHistory
from app.main import app
from fastapi.testclient import TestClient
from datetime import datetime
import json

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_assessment_score_history(test_db, mock_mentor):
    mentor_id = mock_mentor
    apprentice_id = str(uuid4())
    assessment_id = str(uuid4())

    # Create apprentice and assessment
    apprentice = User(id=apprentice_id, name="Apprentice", email="apprentice@example.com", role="apprentice")
    assessment = Assessment(id=assessment_id, apprentice_id=apprentice_id, template_id="template-1")

    score_data = {
        "q1": {
            "score": 7,
            "feedback": "Solid answer",
            "recommendation": "Go deeper in Scripture"
        }
    }

    history = AssessmentScoreHistory(
        id=str(uuid4()),
        assessment_id=assessment_id,
        apprentice_id=apprentice_id,
        score_data=score_data,
        model_used="gpt-4",
        triggered_by="mentor",
        notes="Test entry",
        scored_at=datetime.utcnow()
    )

    test_db.add_all([apprentice, assessment, history])
    test_db.commit()

    token = f"Bearer {mentor_id}"
    response = client.get(
        f"/assessments/{assessment_id}/history",
        headers={"Authorization": token}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["assessment_id"] == assessment_id
    assert data[0]["score_data"]["q1"]["score"] == 7
    assert data[0]["triggered_by"] == "mentor"
