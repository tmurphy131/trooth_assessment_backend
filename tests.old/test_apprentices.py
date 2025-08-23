def test_apprentice_link(client, mentor_user, apprentice_user, mentor_apprentice_link):
    response = client.get("/my-apprentices", headers={"Authorization": "Bearer mock-mentor-token"})
    assert response.status_code == 200
    data = response.json()
    assert any(a["id"] == apprentice_user.id for a in data)
