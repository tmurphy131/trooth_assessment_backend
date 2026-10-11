"""Response shapes for the integrations health check (specs/003-integration-health-alerts)."""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

IntegrationName = Literal[
    "database", "llm_primary", "llm_fallback", "email",
    "firebase_auth", "firebase_messaging", "revenuecat", "shopify",
]


class IntegrationResult(BaseModel):
    name: IntegrationName
    status: Literal["up", "down", "not_configured", "skipped"]  # skipped: suppressed by HEALTHCHECK_SKIP
    latency_ms: Optional[int] = None  # null when not_configured or skipped
    detail: Optional[str] = None  # provider name for the LLM probes
    error: Optional[str] = None  # only when down; scrubbed, at most 200 characters


class IntegrationsReport(BaseModel):
    environment: str
    status: Literal["healthy", "degraded"]
    checked_at: datetime
    duration_ms: int
    integrations: List[IntegrationResult]  # always all eight, in a fixed order
