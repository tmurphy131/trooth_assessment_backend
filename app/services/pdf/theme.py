"""Brand tokens for PDF reports (specs/008-pdf-redesign, research R9).

Matches the app (`kPrimaryGold`, `kCharcoal`) and the spec 005 email layout.
"""
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

# Dark surfaces (header band, highlight cards)
CHARCOAL = HexColor("#1A1A1A")
SURFACE = HexColor("#222222")
RULE_DARK = HexColor("#2E2E2E")
ON_DARK = HexColor("#E6E6E6")
ON_DARK_MUTED = HexColor("#A3A3A3")

# Gold
GOLD = HexColor("#D4AF37")
GOLD_DEEP = HexColor("#B8960C")  # gold text on white (contrast)
GOLD_TINT = HexColor("#FAF4E1")

# Neutrals on white
INK = HexColor("#1A1A1A")
BODY = HexColor("#333333")
MUTED = HexColor("#6B6B6B")
HAIRLINE = HexColor("#E6E6E6")
TRACK = HexColor("#EFEFEF")
WHITE = HexColor("#FFFFFF")

# Muted status set: only for status cues
SAGE = HexColor("#6B8F71")
AMBER = HexColor("#C9A227")
CLAY = HexColor("#B5654A")

PAGE_SIZE = letter
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN_X = 0.6 * inch
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

BAND_HEIGHT = 96  # first-page header band
STRIP_HEIGHT = 30  # later-page header strip
FOOTER_HEIGHT = 40

# Type scale: (size, leading)
TITLE = (20, 24)
H2 = (12, 16)
H3 = (11.5, 15)
BODY_SIZE = (9.5, 14)
SMALL = (8, 11)

_STRONG = {"strong", "excellent", "flourishing", "mature", "maturing", "strongest"}
_DEVELOPING = {"developing", "growing", "good", "stable", "average", "moderate"}


def status_color(kind) -> HexColor:
    """Map a level/band word or a 0..1 ratio to the muted status palette."""
    if isinstance(kind, (int, float)):
        return SAGE if kind >= 0.7 else AMBER if kind >= 0.4 else CLAY
    k = (kind or "").strip().lower()
    if k in _STRONG:
        return SAGE
    if k in _DEVELOPING:
        return AMBER
    return CLAY if k else MUTED


def hex_of(color) -> str:
    """'#RRGGBB' for use in Paragraph <font color=...> markup."""
    return "#" + color.hexval()[2:]
