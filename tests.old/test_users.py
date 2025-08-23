def test_root_route(client):
    response = client.get("/")
    assert response.status_code == 404  # Or 200 if your app defines `/`
