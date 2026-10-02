"""
Server-side lookups against RevenueCat, so purchase state never comes from
the client.

Uses GET /v1/subscribers/{app_user_id}. A secret API key is preferred
(REVENUECAT_SECRET_API_KEY); a public SDK key (REVENUECAT_API_KEY) also works
for this read-only endpoint. Either way the data comes from RevenueCat, not
the app, so a modified client can't forge it.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote
import logging

import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.revenuecat.com/v1"
PREMIUM_ENTITLEMENT = "premium"
GIFT_SEAT_MARKER = "gift_seat"


class RevenueCatUnavailable(Exception):
    """RevenueCat isn't configured or couldn't be reached."""


@dataclass
class VerifiedEntitlement:
    product_id: str
    expires_at: Optional[datetime]  # None = lifetime
    store: Optional[str]


@dataclass
class VerifiedCustomer:
    premium: Optional[VerifiedEntitlement]
    # Count of currently valid gift-seat purchases (active subscriptions plus
    # one-time purchases).
    gift_seat_purchases: int = 0
    raw: dict = field(default_factory=dict, repr=False)


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_active(expires_at: Optional[datetime], now: datetime) -> bool:
    return expires_at is None or expires_at > now


def parse_subscriber(payload: dict, now: Optional[datetime] = None) -> VerifiedCustomer:
    """Turn a /v1/subscribers response into what the backend needs."""
    now = now or datetime.now(timezone.utc)
    subscriber = payload.get("subscriber") or {}
    subscriptions = subscriber.get("subscriptions") or {}

    premium = None
    ent = (subscriber.get("entitlements") or {}).get(PREMIUM_ENTITLEMENT)
    if ent:
        expires_at = _parse_date(ent.get("expires_date"))
        if _is_active(expires_at, now):
            product_id = ent.get("product_identifier") or ""
            store = (subscriptions.get(product_id) or {}).get("store")
            premium = VerifiedEntitlement(product_id=product_id, expires_at=expires_at, store=store)

    gift_seats = 0
    for product_id, sub in subscriptions.items():
        if GIFT_SEAT_MARKER in product_id.lower() and _is_active(_parse_date(sub.get("expires_date")), now):
            gift_seats += 1
    for product_id, purchases in (subscriber.get("non_subscriptions") or {}).items():
        if GIFT_SEAT_MARKER in product_id.lower():
            gift_seats += len(purchases or [])

    return VerifiedCustomer(premium=premium, gift_seat_purchases=gift_seats, raw=payload)


def _api_key() -> str:
    return settings.revenuecat_secret_api_key or settings.revenuecat_api_key


def fetch_customer(app_user_id: str) -> VerifiedCustomer:
    """Fetch a customer's purchases from RevenueCat.

    Raises RevenueCatUnavailable when no key is configured or the request
    fails, so callers can refuse to grant anything rather than trust the client.
    """
    key = _api_key()
    if not key:
        raise RevenueCatUnavailable("RevenueCat API key not configured")
    try:
        r = httpx.get(
            f"{API_BASE}/subscribers/{quote(app_user_id, safe='')}",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            timeout=10.0,
        )
    except httpx.HTTPError as e:
        raise RevenueCatUnavailable(f"RevenueCat request failed: {e}") from e
    if r.status_code != 200:
        raise RevenueCatUnavailable(f"RevenueCat returned {r.status_code}")
    return parse_subscriber(r.json())
