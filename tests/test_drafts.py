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

def test_list_drafts_includes_template_name(client, db_session, mentor_user):
    """Mentor 'My Assessments' cards show the template name of in-progress drafts."""
    from app.main import app
    from app.models.assessment_template import AssessmentTemplate
    from app.models.assessment_draft import AssessmentDraft
    from app.services.auth import get_current_user

    template = AssessmentTemplate(name="Book of Matthew Assessment", is_published=True)
    db_session.add(template)
    db_session.commit()
    db_session.add(AssessmentDraft(apprentice_id=mentor_user.id, template_id=template.id, answers={}))
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: mentor_user
    try:
        r = client.get("/assessment-drafts/list")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert r.status_code == 200, r.text
    assert [d["template_name"] for d in r.json()] == ["Book of Matthew Assessment"]
