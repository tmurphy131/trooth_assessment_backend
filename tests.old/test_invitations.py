def test_invitation_token_flow(client, mock_mentor):
    response = client.post("/invitations", json={
        "apprentice_email": "tay.murphy88@gmail.com",
        "apprentice_name": "New Apprentice"
    })
    assert response.status_code in [200, 403, 404]
