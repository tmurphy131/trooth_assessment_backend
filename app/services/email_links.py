"""Signed unsubscribe links (specs/005-email-redesign, research R4).

Token: ``v1.<user_id>.<issued_at>.<sig>`` where sig = base64url(HMAC-SHA256(EMAIL_LINK_SECRET,
"v1.<user_id>.<issued_at>")). Verifying needs no database lookup and no sign-in. Without
EMAIL_LINK_SECRET nothing is signed: callers get None/{} and send without an unsubscribe link.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Optional
from urllib.parse import quote

from app.core.settings import settings

VERSION = "v1"
MAX_FUTURE_SKEW_S = 300


def _secret() -> bytes:
    return (settings.email_link_secret or "").encode()


def _sign(payload: str) -> str:
    digest = hmac.new(_secret(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def make_token(user_id: str, now: Optional[float] = None) -> Optional[str]:
    if not _secret() or not user_id:
        return None
    payload = f"{VERSION}.{user_id}.{int(now if now is not None else time.time())}"
    return f"{payload}.{_sign(payload)}"


def verify_token(token: Optional[str], now: Optional[float] = None) -> Optional[str]:
    """The user id the token was issued for, or None if it's invalid, tampered or expired."""
    if not _secret() or not token:
        return None
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != VERSION:
        return None
    version, user_id, issued, sig = parts
    if not issued.isdigit() or not user_id:
        return None
    if not hmac.compare_digest(_sign(f"{version}.{user_id}.{issued}"), sig):
        return None
    current = now if now is not None else time.time()
    age = current - int(issued)
    if age < -MAX_FUTURE_SKEW_S or age > settings.email_link_ttl_days * 86400:
        return None
    return user_id


def unsubscribe_urls(user_id: str) -> Optional[tuple[str, str]]:
    """(confirm page URL, RFC 8058 one-click URL), or None without a secret."""
    token = make_token(user_id)
    if not token:
        return None
    base = settings.backend_api_url.rstrip("/")
    t = quote(token, safe="")
    return f"{base}/email/unsubscribe?t={t}", f"{base}/email/unsubscribe/one-click?t={t}"


def list_unsubscribe_headers(user_id: str) -> dict:
    urls = unsubscribe_urls(user_id)
    if not urls:
        return {}
    return {
        "List-Unsubscribe": f"<{urls[1]}>, <mailto:{settings.support_email}?subject=unsubscribe>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }
