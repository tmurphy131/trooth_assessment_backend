import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import User, Category, Question, AssessmentTemplate
from app.db import get_db
import uuid

@pytest.mark.asyncio
async def test_create_assessment_draft_with_questions(test_db: Session):
    # Setup: Create mentor and apprentice
    mentor_id = str(uuid.uuid4())
    apprentice_id = str(uuid.uuid4())
    category_id = str(uuid.uuid4())

    mentor = User(id=mentor_id, name="Mentor", email="mentor@example.com", role="mentor")
    apprentice = User(id=apprentice_id, name="Apprentice", email="apprentice@example.com", role="apprentice")
    category = Category(id=category_id, name="Spiritual Growth")
    question1 = Question(id=str(uuid.uuid4()), text="What is faith?", category_id=category_id)
    question2 = Question(id=str(uuid.uuid4()), text="How often do you pray?", category_id=category_id)
    template = AssessmentTemplate(id=str(uuid.uuid4()), name="Test Template", categories=[category])

    test_db.add_all([mentor, apprentice, category, question1, question2, template])
    test_db.commit()

    # Use mocked token header
    token = f"Bearer {apprentice_id}"

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
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
