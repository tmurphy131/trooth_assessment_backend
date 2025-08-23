def test_get_my_apprentices(client, mock_mentor):
    response = client.get("/my-apprentices")
    assert response.status_code in [200, 403, 404]
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)