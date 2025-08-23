def test_apprentice_cannot_access_mentor_routes(client, mock_apprentice):
    response = client.get("/my-apprentices")
    assert response.status_code in [403, 404]
