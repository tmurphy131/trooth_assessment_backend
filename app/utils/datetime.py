from __future__ import annotations
from datetime import datetime, UTC, tzinfo
from typing import Optional

__all__ = ["utc_now", "ensure_aware_utc", "to_naive_utc"]

def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(UTC)

def ensure_aware_utc(dt: datetime | None) -> Optional[datetime]:
    """Ensure a datetime is timezone-aware in UTC (assumes naive input already in UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)

def to_naive_utc(dt: datetime | None) -> Optional[datetime]:
    """Convert aware datetime to naive UTC for legacy storage/compare; pass through naive assumed UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)
