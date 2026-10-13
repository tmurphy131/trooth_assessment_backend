"""Text safety and formatting for PDF reports (research R4)."""
from __future__ import annotations

import re
from datetime import date, datetime
from xml.sax.saxutils import escape

# Emoji, pictographs, dingbats, arrows/symbol blocks, flags, variation selector, ZWJ.
_UNSUPPORTED = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U000025A0-\U000025FF"
    "️‍❓❗"
    "]"
)
_SPACES = re.compile(r"[ \t]{2,}")


def strip_unsupported(text: str) -> str:
    return _SPACES.sub(" ", _UNSUPPORTED.sub("", text)).strip()


def safe(value) -> str:
    """Plain text -> Paragraph-safe markup: drop glyphs the fonts can't draw, escape XML."""
    if value is None:
        return ""
    return escape(strip_unsupported(str(value)))


def format_date(value) -> str | None:
    """'October 13, 2026' from a datetime/date/ISO string; None if unparseable."""
    if value is None or value == "":
        return None
    dt = value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(dt, (datetime, date)):
        return None
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
