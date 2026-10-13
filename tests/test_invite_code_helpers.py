"""Pure invite-code helpers (specs/006-invite-codes)."""
import subprocess
import sys

from app.services.invite_codes import (
    CODE_ALPHABET,
    CODE_LENGTH,
    format_invite_code,
    generate_invite_code,
    normalize_invite_code,
)


def test_generate_uses_alphabet_without_lookalikes():
    for _ in range(200):
        code = generate_invite_code()
        assert len(code) == CODE_LENGTH
        assert all(c in CODE_ALPHABET for c in code)
        assert not set(code) & set("0O1IL")


def test_normalize_ignores_case_dashes_and_whitespace():
    assert normalize_invite_code("K7QM-3XPR") == "K7QM3XPR"
    assert normalize_invite_code("k7qm3xpr") == "K7QM3XPR"
    assert normalize_invite_code("  K7QM-3XPR  ") == "K7QM3XPR"
    assert normalize_invite_code("K7 QM\t3X PR") == "K7QM3XPR"


def test_normalize_rejects_invalid():
    assert normalize_invite_code("") is None
    assert normalize_invite_code(None) is None
    assert normalize_invite_code("ABC") is None
    assert normalize_invite_code("K7QM-3XPRZ") is None
    assert normalize_invite_code("0OIL-0OIL") is None


def test_format_is_display_form_and_idempotent():
    assert format_invite_code("K7QM3XPR") == "K7QM-3XPR"
    assert format_invite_code("k7qm3xpr") == "K7QM-3XPR"
    once = format_invite_code("K7QM3XPR")
    assert format_invite_code(once) == once
    assert format_invite_code(None) is None


def test_helpers_import_no_models():
    """Guards against a circular import: the model imports this module."""
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys, app.services.invite_codes; "
         "print(any(m.startswith('app.models') or m == 'app.db' for m in sys.modules))"],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == "False"
