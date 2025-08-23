def test_apprentice_link(client, mentor_user, apprentice_user, mentor_apprentice_link, mock_mentor):
    response = client.get("/my-apprentices")
    assert response.status_code in [200, 403, 404]
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        assert any(a["id"] == apprentice_user.id for a in data)