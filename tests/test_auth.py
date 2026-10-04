def test_public_health_check(client):
    response = client.get("/")
    assert response.status_code == 200


def test_mock_tokens_rejected_outside_test_env(monkeypatch, db_session):
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials
    import pytest
    from app.models.user import User
    from app.services.auth import get_current_user

    monkeypatch.setenv("ENV", "production")
    for token in ("mock-admin-token", "mock-mentor-token", "mock-apprentice-token"):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc:
            get_current_user(credentials=creds, db=db_session)
        assert exc.value.status_code == 401
    assert db_session.query(User).count() == 0
