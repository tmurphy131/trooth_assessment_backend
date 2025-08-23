def test_public_health_check(client):
    response = client.get("/")
    assert response.status_code == 404  # or 200 if you add a root endpoint
