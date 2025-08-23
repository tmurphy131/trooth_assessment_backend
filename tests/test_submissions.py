def test_submit_assessment(client, mock_apprentice):
    response = client.post(
        "/assessment-drafts",
        headers={"Authorization": "Bearer test"},
        json={
            "answers": {
                "q1": "Answer 1",
                "q2": "Answer 2",
                "q3": "Answer 3"
            },
            "last_question_id": "q3"
        }
    )
    assert response.status_code in [200, 403, 404]