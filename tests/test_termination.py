import uuid
from app.models.mentor_apprentice import MentorApprentice
from unittest.mock import patch

def test_terminate_apprenticeship_flow(client, db_session, apprentice_user):
    mentor_id = "mentor-1"
    token = "mock-mentor-token"

    # Link mentor and apprentice
    link = MentorApprentice(apprentice_id=apprentice_user.id, mentor_id=mentor_id, active=True)
    db_session.add(link)
    db_session.commit()

    # Act: terminate (mock email to assert path executed)
    # Patch underlying email service function since mentor route imports within function scope
    with patch("app.services.email.send_notification_email", return_value=True) as mocked_send:
            resp = client.post(
                f"/mentor/apprentice/{apprentice_user.id}/terminate",
                json={"reason": "No longer continuing"},
                headers={"Authorization": f"Bearer {token}"}
            )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("status") == "terminated"
    assert body.get("apprentice_id") == str(apprentice_user.id)
    # Relationship should now be inactive
    db_session.refresh(link)
    assert link.active is False
    # Email helper called once
    assert mocked_send.call_count == 1

    # Act again: should fail second time (already inactive)
    resp2 = client.post(
        f"/mentor/apprentice/{apprentice_user.id}/terminate",
        json={"reason": "Repeat"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp2.status_code == 400

    # Negative: unknown apprentice id
    random_id = str(uuid.uuid4())
    resp3 = client.post(
        f"/mentor/apprentice/{random_id}/terminate",
        json={"reason": "Irrelevant"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp3.status_code in (403, 404)
