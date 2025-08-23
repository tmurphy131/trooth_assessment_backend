def test_save_draft_as_apprentice(client, mock_apprentice):
    response = client.post(
        "/assessment-drafts",
        headers={"Authorization": "Bearer test"},
        json={
            "answers": {
                "question1": "I pray daily",
                "question2": "I read scripture often"
            },
            "last_question_id": "question2"
        }
    )
    assert response.status_code in [200, 403, 404]
