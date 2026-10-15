"""RevenueCat webhook authentication fails closed and compares the secret safely."""
import pytest

from app.core.settings import settings

EVENT = {"event": {"type": "TEST", "app_user_id": "nobody"}}


@pytest.mark.parametrize("header", [None, "Bearer wrong", "Basic s3cret"])
def test_wrong_or_missing_authorization_is_refused(client, monkeypatch, header):
    monkeypatch.setattr(settings, "revenuecat_webhook_secret", "s3cret")
    headers = {"Authorization": header} if header else {}
    assert client.post("/subscriptions/webhook", json=EVENT, headers=headers).status_code == 401


def test_unconfigured_secret_refuses_everything(client, monkeypatch):
    monkeypatch.setattr(settings, "revenuecat_webhook_secret", "")
    r = client.post("/subscriptions/webhook", json=EVENT, headers={"Authorization": "Bearer anything"})
    assert r.status_code == 503


def test_correct_secret_is_accepted(client, monkeypatch):
    monkeypatch.setattr(settings, "revenuecat_webhook_secret", "s3cret")
    r = client.post("/subscriptions/webhook", json=EVENT, headers={"Authorization": "Bearer s3cret"})
    assert r.status_code not in (401, 503), r.text
