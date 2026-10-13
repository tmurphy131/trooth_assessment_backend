"""Invite code helpers (specs/006-invite-codes).

Pure functions only. This module must not import app.models or app.db: the
ApprenticeInvitation model uses generate_invite_code as a column default, so an
import back into the models would be circular.
"""
import secrets

# No 0/O, 1/I/L, so codes survive being read aloud or texted.
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 8


def generate_invite_code() -> str:
    """Random canonical code: 8 characters, uppercase, no dash."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_invite_code(raw: str | None) -> str | None:
    """Canonical form of user input, or None if it can't be a valid code.

    Ignores case, dashes and any whitespace.
    """
    if not raw:
        return None
    code = "".join(raw.split()).replace("-", "").upper()
    if len(code) != CODE_LENGTH or any(c not in CODE_ALPHABET for c in code):
        return None
    return code


def format_invite_code(code: str | None) -> str | None:
    """Display form XXXX-XXXX. Idempotent; returns input unchanged if it isn't a valid code."""
    canonical = normalize_invite_code(code)
    if canonical is None:
        return code
    return f"{canonical[:4]}-{canonical[4:]}"
