def test_apprentice_cannot_access_mentor_routes(client, mock_apprentice):
    response = client.get("/my-apprentices")
    assert response.status_code in [403, 404]
    if response.status_code == 403:
        assert response.json()["detail"] or "forbidden" in response.text.lower()