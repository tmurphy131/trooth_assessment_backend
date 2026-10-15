"""Helpers for keeping personal data out of logs (Principle V)."""


def mask_email(email) -> str:
    """'taylor@example.com' -> 't***@example.com'. Safe on None or malformed values."""
    if not email or "@" not in str(email):
        return "?"
    local, domain = str(email).split("@", 1)
    return f"{local[:1]}***@{domain}"
