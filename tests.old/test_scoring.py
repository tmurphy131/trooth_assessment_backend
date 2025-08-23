def test_scoring_stub():
    from app.services.ai_scoring import score_assessment
    answers = {"q1": "I pray", "q2": "I evangelize"}
    result = score_assessment(answers)
    assert "score" in result
    assert "recommendation" in result
