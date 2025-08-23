import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import User, Category, Question, AssessmentTemplate
import uuid
from uuid import uuid4

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_assessment_draft_with_questions(test_db: Session, mock_apprentice):
    mentor_id = str(uuid.uuid4())
    apprentice_id = str(uuid.uuid4())

    mentor = User(
        id=mentor_id,
        name="Mentor",
        email=f"mentor+{uuid4().hex[:6]}@example.com",
        role="mentor"
    )
    apprentice = User(
        id=apprentice_id,
        name="Apprentice",
        email=f"apprentice+{uuid4().hex[:6]}@example.com",
        role="apprentice"
    )
    category = Category(id=str(uuid.uuid4()), name=f"Spiritual Growth {uuid.uuid4().hex[:5]}")
    question1 = Question(id=str(uuid.uuid4()), text="What is faith?", category_id=category.id)
    question2 = Question(id=str(uuid.uuid4()), text="How often do you pray?", category_id=category.id)
    template = AssessmentTemplate(id=str(uuid.uuid4()), name="Test Template")
    template.category = category

    test_db.add_all([mentor, apprentice, category, question1, question2, template])
    test_db.commit()

    token = f"Bearer {apprentice_id}"

    
    response = client.post(
        "/assessment-drafts",
        headers={"Authorization": token},
        json={"template_id": template.id}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == template.id
    assert data["apprentice_id"] == apprentice_id
    assert "questions" in data
    assert len(data["questions"]) == 2
