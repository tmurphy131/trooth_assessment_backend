import pytest
from httpx import AsyncClient
from app.main import app
from app.models import User, Category, AssessmentTemplate
from app.db import get_db
import uuid

@pytest.mark.asyncio
async def test_clone_assessment_template(test_db):
    # Create an admin user and a category
    admin_id = str(uuid.uuid4())
    category_id = str(uuid.uuid4())
    template_id = str(uuid.uuid4())

    admin = User(id=admin_id, name="Admin", email="admin@example.com", role="admin")
    category = Category(id=category_id, name="Fellowship")
    template = AssessmentTemplate(id=template_id, name="Original Template", categories=[category])

    test_db.add_all([admin, category, template])
    test_db.commit()

    # Use mocked token header
    token = f"Bearer {admin_id}"

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/admin/assessment-templates/{template_id}/clone",
            headers={"Authorization": token}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"].startswith("Original Template")
    assert data["id"] != template_id
    assert category_id in data["category_ids"]
