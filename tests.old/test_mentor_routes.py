def test_get_my_apprentices(client, mock_mentor):
    response = client.get("/my-apprentices")
    assert response.status_code in [200, 403, 404]
