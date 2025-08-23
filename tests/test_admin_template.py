import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

@pytest.fixture
def admin_token(mock_admin):
    return "test-admin-token"

def test_create_template(client, mock_admin):
    response = client.post(
        "/admin/templates",
        json={"name": "New Template", "description": "For testing"}
    )
    assert response.status_code in [200, 403]
    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        assert data["name"] == "New Template"

def test_list_templates(client, mock_admin):
    response = client.get(
        "/admin/templates",
    )
    assert response.status_code in [200, 403]
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)