"""Server-rendered HTML pages must render (not 500).

Regression for Starlette 1.x, which requires TemplateResponse(request, name, context);
the old TemplateResponse(name, {...}) form raised "TypeError: unhashable type: 'dict'".
"""
import uuid
from datetime import datetime, timedelta, UTC

import pytest

from app.models.agreement import Agreement, AgreementToken
from app.models.apprentice_invitation import ApprenticeInvitation


def _naive_now():
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture
def invite(db_session, mentor_user):
    def _make(expired=False, accepted=False):
        inv = ApprenticeInvitation(
            mentor_id=mentor_user.id,
            apprentice_email="invitee@example.com",
            apprentice_name="Invitee",
            token=str(uuid.uuid4()),
            expires_at=_naive_now() + (timedelta(days=-1) if expired else timedelta(days=7)),
            accepted=accepted,
        )
        db_session.add(inv)
        db_session.commit()
        return inv
    return _make


def _assert_html_page(response, *texts):
    assert response.status_code == 200, response.text[:300]
    assert response.headers["content-type"].startswith("text/html")
    for text in texts:
        assert text in response.text


def test_invitation_page_valid(client, invite, mentor_user):
    inv = invite()
    r = client.get("/invitations/accept-invitation", params={"token": inv.token})
    _assert_html_page(r, "Invitee", mentor_user.name)


def test_invitation_page_unknown_token(client):
    r = client.get("/invitations/accept-invitation", params={"token": "nope"})
    _assert_html_page(r, "Invitation Not Found")


def test_invitation_page_expired(client, invite):
    inv = invite(expired=True)
    r = client.get("/invitations/accept-invitation", params={"token": inv.token})
    _assert_html_page(r, "Invitation Expired")


def test_invitation_page_already_accepted(client, invite):
    inv = invite(accepted=True)
    r = client.get("/invitations/accept-invitation", params={"token": inv.token})
    _assert_html_page(r, "Already Accepted")


def test_agreement_sign_page(client, db_session, mentor_user):
    agreement = Agreement(
        template_version=1,
        mentor_id=mentor_user.id,
        apprentice_email="apprentice@example.com",
        apprentice_name="Apprentice",
        status="awaiting_apprentice",
        fields_json={},
        content_rendered="# Agreement\n\nWe agree.",
    )
    db_session.add(agreement)
    db_session.commit()
    token = AgreementToken(agreement_id=agreement.id, token_type="apprentice", expires_at=_naive_now() + timedelta(days=7))
    db_session.add(token)
    db_session.commit()

    r = client.get(f"/agreements/sign/apprentice/{token.token}")
    _assert_html_page(r, "We agree.")


@pytest.mark.parametrize("path", ["/agreements/public/signed-success", "/agreements/public/parent-signed-success"])
def test_agreement_success_pages(client, path):
    r = client.get(path)
    _assert_html_page(r)
