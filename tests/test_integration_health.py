"""Integration health check and diagnostic endpoint access (specs/003-integration-health-alerts).

Every probe is replaced with a fake; no live integration is called.
"""
import asyncio
import logging
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import integration_health as ih

SECRET = {"X-Cron-Secret": "test-cron-secret"}  # matches conftest's CRON_SECRET
ORDER = ["database", "llm_primary", "llm_fallback", "email",
         "firebase_auth", "firebase_messaging", "revenuecat", "shopify"]

client = TestClient(app)


def _ok(detail=None):
    return lambda: ih.ProbeOutcome(detail=detail)


def _raise(exc):
    def probe():
        raise exc
    return probe


@pytest.fixture(autouse=True)
def no_skips(monkeypatch):
    """Probe everything unless a test opts into HEALTHCHECK_SKIP behavior."""
    from app.core.settings import settings
    monkeypatch.setattr(settings, "healthcheck_skip", set())


@pytest.fixture
def probes(monkeypatch):
    """All probes up by default; tests override individual entries."""
    table = {name: _ok("gemini" if name == "llm_primary" else None) for name in ORDER}

    def install(**overrides):
        table.update(overrides)
        monkeypatch.setattr(ih, "PROBES", [(name, table[name]) for name in ORDER])

    install()
    return install


def _arun(coro):
    # Private loop: asyncio.run() would clear the current loop that older tests rely on
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _run(timeout_s=ih.PROBE_TIMEOUT_S):
    return _arun(ih.run_all(timeout_s=timeout_s))


# ---------- run_all ----------

def test_all_up_is_healthy_in_fixed_order(probes):
    report = _run()
    assert report.status == "healthy"
    assert [r.name for r in report.integrations] == ORDER
    assert all(r.status == "up" and r.latency_ms is not None for r in report.integrations)
    assert report.integrations[1].detail == "gemini"


def test_down_probe_is_scrubbed_and_logged_once(probes, caplog):
    probes(llm_fallback=_raise(RuntimeError(
        "Error code: 429 insufficient_quota key sk-abcdefghijklmnop SG.abcdefghijklmnop.xyz "
        "AIzaSyDTzy7Z-LaX4wC1EH3k Bearer abc.def " + "x" * 300)))
    with caplog.at_level(logging.WARNING, logger="app.services.integration_health"):
        report = _run()
    fallback = report.integrations[2]
    assert report.status == "degraded"
    assert fallback.status == "down" and len(fallback.error) <= 200
    assert "insufficient_quota" in fallback.error
    for leaked in ("sk-abcdefghijklmnop", "SG.abcdefghijklmnop", "AIzaSyDTzy7Z", "abc.def"):
        assert leaked not in fallback.error
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("integration_down")]
    assert len(lines) == 1
    assert "integration=llm_fallback" in lines[0] and "env=" in lines[0]
    assert "sk-abcdefghijklmnop" not in lines[0]


def test_hanging_probe_times_out_without_blocking_others(probes):
    def hang():
        time.sleep(1.5)
        return ih.ProbeOutcome()

    probes(email=hang)

    async def timed():
        start = time.monotonic()
        report = await ih.run_all(timeout_s=0.3)
        return report, time.monotonic() - start

    # run_all returns at the timeout; the stray worker thread finishes on its own later
    report, elapsed = _arun(timed())
    assert elapsed < 1.0
    email = report.integrations[3]
    assert email.status == "down" and "timed out" in email.error
    assert sum(r.status == "up" for r in report.integrations) == 7


def test_not_configured_is_reported_without_alert(probes, caplog):
    probes(shopify=_raise(ih.NotConfigured("no creds")), llm_fallback=_raise(ih.NotConfigured("off")))
    with caplog.at_level(logging.WARNING, logger="app.services.integration_health"):
        report = _run()
    assert report.status == "healthy"
    for r in (report.integrations[2], report.integrations[7]):
        assert r.status == "not_configured" and r.latency_ms is None and r.error is None
    assert not [r for r in caplog.records if r.getMessage().startswith("integration_down")]


def test_skipped_integration_is_not_probed_or_alerted(probes, monkeypatch, caplog):
    from app.core.settings import settings
    monkeypatch.setattr(settings, "healthcheck_skip", {"llm_fallback"})
    probes(llm_fallback=_raise(AssertionError("skipped probes must not run")))
    with caplog.at_level(logging.WARNING, logger="app.services.integration_health"):
        report = _run()
    fallback = report.integrations[2]
    assert report.status == "healthy"
    assert (fallback.status, fallback.latency_ms, fallback.error) == ("skipped", None, None)
    assert not [r for r in caplog.records if r.getMessage().startswith("integration_down")]


def test_llm_fallback_is_skipped_by_default():
    from app.core.settings import Settings
    assert "llm_fallback" in Settings().healthcheck_skip


# ---------- GET /health/integrations ----------

def test_integrations_endpoint_returns_contract_shape(probes):
    probes(revenuecat=_raise(RuntimeError("RevenueCat subscribers returned 500")))
    r = client.get("/health/integrations", headers=SECRET)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"environment", "status", "checked_at", "duration_ms", "integrations"}
    assert body["status"] == "degraded"
    assert [i["name"] for i in body["integrations"]] == ORDER
    assert set(body["integrations"][0]) == {"name", "status", "latency_ms", "detail", "error"}


@pytest.mark.parametrize("headers", [{}, {"X-Cron-Secret": "guess"},
                                     {"X-Cron-Secret": "dev-cron-secret-change-in-prod"}])
def test_integrations_endpoint_rejects_bad_secret(probes, headers):
    assert client.get("/health/integrations", headers=headers).status_code == 403


def test_integrations_endpoint_fails_closed_when_secret_unset(probes, monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    assert client.get("/health/integrations", headers=SECRET).status_code == 403


# ---------- diagnostic endpoints locked down ----------

DIAGNOSTIC = ["/health/health/detailed", "/health/health/llm",
              "/health/health/llm?test_generation=true", "/health/health/metrics"]


@pytest.mark.parametrize("path", DIAGNOSTIC)
def test_diagnostic_endpoints_need_secret(path, monkeypatch):
    # Never spend tokens in tests, even if a request slipped through
    from app.services import llm as llm_mod

    class _NoCall:
        def __getattr__(self, name):
            raise AssertionError("LLM must not be called without the secret")

    monkeypatch.setattr(llm_mod, "get_llm_service", lambda *a, **k: _NoCall())
    assert client.get(path).status_code == 403
    assert client.get(path, headers={"X-Cron-Secret": "guess"}).status_code == 403
    monkeypatch.delenv("CRON_SECRET", raising=False)
    assert client.get(path, headers=SECRET).status_code == 403


@pytest.mark.parametrize("path", ["/health/health/detailed", "/health/health/metrics"])
def test_diagnostic_endpoints_work_with_secret(path):
    assert client.get(path, headers=SECRET).status_code == 200


def test_basic_health_stays_public():
    assert client.get("/health").status_code == 200
    assert client.get("/health/health").status_code == 200


# ---------- scheduler routes fail closed ----------

@pytest.mark.parametrize("path", ["/scheduled/weekly-tips", "/campaigns/run-draft-reminders"])
def test_scheduler_routes_refuse_old_default_when_secret_unset(path, monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    r = client.post(path, headers={"X-Cron-Secret": "dev-cron-secret-change-in-prod"})
    assert r.status_code == 403


def test_scheduler_route_still_accepts_real_secret():
    r = client.post("/scheduled/weekly-tips", headers=SECRET)
    assert r.status_code == 200
