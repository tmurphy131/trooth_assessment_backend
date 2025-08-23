import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, Assessment, MentorApprentice, MentorNote

client = TestClient(app)


@pytest.mark.asyncio
async def test_create_mentor_note(test_db, mock_mentor):
    mentor_id = mock_mentor
    apprentice_id = str(uuid4())
    assessment_id = str(uuid4())

    # Set up mentor-apprentice relationship and an assessment
    apprentice = User(id=apprentice_id, name="Apprentice", email="apprentice@example.com", role="apprentice")
    assessment = Assessment(id=assessment_id, apprentice_id=apprentice_id, template_id="template1")

    test_db.add_all([
        apprentice,
        assessment,
        MentorApprentice(mentor_id=mentor_id, apprentice_id=apprentice_id)
    ])
    test_db.commit()

    token = f"Bearer {mentor_id}"
    payload = {
        "assessment_id": assessment_id,
        "content": "You're doing great. Keep praying daily.",
        "follow_up_plan": "Text next Monday to ask how things are going.",
        "is_private": True
    }

    response = client.post("/mentor-notes/", json=payload, headers={"Authorization": token})
    assert response.status_code == 200

    note = response.json()
    assert note["content"] == payload["content"]
    assert note["is_private"] is True
    assert note["mentor_id"] == mentor_id


@pytest.mark.asyncio
async def test_get_mentor_notes(test_db, mock_mentor):
    mentor_id = mock_mentor
    apprentice_id = str(uuid4())
    assessment_id = str(uuid4())
    note_id = str(uuid4())

    apprentice = User(id=apprentice_id, name="Apprentice2", email="a2@example.com", role="apprentice")
    assessment = Assessment(id=assessment_id, apprentice_id=apprentice_id, template_id="templateX")

    note = MentorNote(
        id=note_id,
        assessment_id=assessment_id,
        mentor_id=mentor_id,
        content="Strong faith response",
        follow_up_plan="Check again in a week",
        is_private=False
    )

    test_db.add_all([apprentice, assessment, note])
    test_db.add(MentorApprentice(mentor_id=mentor_id, apprentice_id=apprentice_id))
    test_db.commit()

    response = client.get(f"/mentor-notes/assessment/{assessment_id}", headers={"Authorization": f"Bearer {mentor_id}"})
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["content"] == "Strong faith response"


@pytest.mark.asyncio
async def test_delete_mentor_note(test_db, mock_mentor):
    mentor_id = mock_mentor
    apprentice_id = str(uuid4())
    assessment_id = str(uuid4())
    note_id = str(uuid4())

    apprentice = User(id=apprentice_id, name="Apprentice3", email="a3@example.com", role="apprentice")
    assessment = Assessment(id=assessment_id, apprentice_id=apprentice_id, template_id="templateZ")
    note = MentorNote(
        id=note_id,
        assessment_id=assessment_id,
        mentor_id=mentor_id,
        content="Delete this note",
        is_private=True
    )

    test_db.add_all([apprentice, assessment, note])
    test_db.add(MentorApprentice(mentor_id=mentor_id, apprentice_id=apprentice_id))
    test_db.commit()

    response = client.delete(f"/mentor-notes/{note_id}", headers={"Authorization": f"Bearer {mentor_id}"})
    assert response.status_code == 204

    # Verify it's deleted
    deleted = test_db.query(MentorNote).filter_by(id=note_id).first()
    assert deleted is None
