"""Live health probes for every external integration (specs/003-integration-health-alerts).

Each probe makes the smallest real call that proves the integration works with the current
credentials, with no user-visible side effect. ``run_all`` runs them concurrently with a
per-probe timeout and logs one ``integration_down`` line per failure, which Cloud Monitoring
turns into an email alert.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Optional

import httpx

from app.core.settings import settings
from app.schemas.health import IntegrationResult, IntegrationsReport

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_S = 10
HTTP_TIMEOUT_S = 8


class NotConfigured(Exception):
    """The integration isn't set up in this environment; reported, never alerted."""


@dataclass
class ProbeOutcome:
    detail: Optional[str] = None


# Key-like substrings that must never reach logs or responses.
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"SG\.[A-Za-z0-9_\-\.]{8,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.=]+"),
    re.compile(r"[A-Za-z0-9_\-]{32,}"),
]


def scrub(error: object, limit: int = 200) -> str:
    text = " ".join(str(error).split())
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("***", text)
    return text[:limit]


# ---------------------------------------------------------------------------
# Probes (sync; run in threads). Raise NotConfigured, raise any other error for down.
# ---------------------------------------------------------------------------

def probe_database() -> ProbeOutcome:
    from sqlalchemy import text
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()
    return ProbeOutcome()


def _probe_llm(provider) -> ProbeOutcome:
    # Model-metadata lookup, not a generation: free, and it doesn't write "[llm] ... error" lines
    # that would trip the real-traffic AI alert. It catches wrong credentials, region or model
    # (the 2026-10-10 failure); quota/billing failures surface through real-traffic alerts.
    if provider is None:
        raise NotConfigured("fallback disabled")
    provider.ping()
    return ProbeOutcome(detail=provider.PROVIDER_NAME)


def probe_llm_primary() -> ProbeOutcome:
    from app.services.llm import get_llm_service

    return _probe_llm(get_llm_service().primary_provider)


def probe_llm_fallback() -> ProbeOutcome:
    from app.services.llm import get_llm_service

    return _probe_llm(get_llm_service().fallback_provider)


def probe_email() -> ProbeOutcome:
    key = settings.sendgrid_api_key or ""
    if not key or key == "your_sendgrid_api_key_here":
        raise NotConfigured("no SendGrid key")
    r = httpx.get("https://api.sendgrid.com/v3/scopes", headers={"Authorization": f"Bearer {key}"},
                  timeout=HTTP_TIMEOUT_S)
    if r.status_code != 200:
        raise RuntimeError(f"SendGrid scopes returned {r.status_code}")
    return ProbeOutcome()


def _firebase_app():
    import firebase_admin

    try:
        return firebase_admin.get_app()
    except ValueError as e:
        raise NotConfigured("Firebase not initialized") from e


def probe_firebase_auth() -> ProbeOutcome:
    _firebase_app().credential.get_access_token()
    return ProbeOutcome()


def probe_firebase_messaging() -> ProbeOutcome:
    from firebase_admin import messaging

    _firebase_app()
    messaging.send(messaging.Message(topic="healthcheck", data={"probe": "1"}), dry_run=True)
    return ProbeOutcome()


def probe_revenuecat() -> ProbeOutcome:
    from urllib.parse import quote
    from app.services.revenuecat import API_BASE

    key = settings.revenuecat_secret_api_key or settings.revenuecat_api_key
    if not key:
        raise NotConfigured("no RevenueCat key")
    app_user_id = quote(settings.revenuecat_healthcheck_app_user_id, safe="")
    r = httpx.get(f"{API_BASE}/subscribers/{app_user_id}", headers={"Authorization": f"Bearer {key}"},
                  timeout=HTTP_TIMEOUT_S)
    if r.status_code not in (200, 201):  # 201 the first time RevenueCat creates the probe customer
        raise RuntimeError(f"RevenueCat subscribers returned {r.status_code}")
    return ProbeOutcome()


def probe_shopify() -> ProbeOutcome:
    from app.services import shopify_admin

    if not shopify_admin.is_configured():
        raise NotConfigured("no Shopify admin credentials")
    with httpx.Client(timeout=HTTP_TIMEOUT_S) as client:
        token = shopify_admin._get_access_token(client)
        shopify_admin._graphql(client, token, "{ shop { name } }", {})
    return ProbeOutcome()


# Fixed order of the report.
PROBES: list[tuple[str, Callable[[], ProbeOutcome]]] = [
    ("database", probe_database),
    ("llm_primary", probe_llm_primary),
    ("llm_fallback", probe_llm_fallback),
    ("email", probe_email),
    ("firebase_auth", probe_firebase_auth),
    ("firebase_messaging", probe_firebase_messaging),
    ("revenuecat", probe_revenuecat),
    ("shopify", probe_shopify),
]


async def _run_one(name: str, probe: Callable[[], ProbeOutcome], timeout_s: float) -> IntegrationResult:
    if name in settings.healthcheck_skip:
        return IntegrationResult(name=name, status="skipped")
    start = time.monotonic()
    try:
        outcome = await asyncio.wait_for(asyncio.to_thread(probe), timeout=timeout_s)
        return IntegrationResult(name=name, status="up", detail=outcome.detail,
                                 latency_ms=int((time.monotonic() - start) * 1000))
    except NotConfigured:
        return IntegrationResult(name=name, status="not_configured")
    except asyncio.TimeoutError:
        error = f"timed out after {timeout_s:g}s"
    except Exception as e:  # any failure of the integration is a "down", not a crash
        error = scrub(f"{type(e).__name__}: {e}")
    latency = int((time.monotonic() - start) * 1000)
    logger.warning('integration_down env=%s integration=%s error="%s"',
                   settings.environment, name, error.replace('"', "'"))
    return IntegrationResult(name=name, status="down", latency_ms=latency, error=error)


async def run_all(timeout_s: float = PROBE_TIMEOUT_S) -> IntegrationsReport:
    checked_at = datetime.now(UTC)
    start = time.monotonic()
    results = await asyncio.gather(*(_run_one(name, probe, timeout_s) for name, probe in PROBES))
    return IntegrationsReport(
        environment=settings.environment,
        status="degraded" if any(r.status == "down" for r in results) else "healthy",
        checked_at=checked_at,
        duration_ms=int((time.monotonic() - start) * 1000),
        integrations=list(results),
    )
