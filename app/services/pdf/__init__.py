"""Branded PDF kit shared by every report PDF (specs/008-pdf-redesign)."""
from .components import (
    KeepTogether,
    ScoreBar,
    bullets,
    callout,
    cards_row,
    dark_card,
    gap,
    label_value,
    para,
    score_table,
    section_heading,
    stat_card,
    styles,
    subheading,
    two_col_cards,
)
from .fonts import register_fonts
from .layout import build_pdf, fallback_pdf, site_label
from .text import format_date, safe, strip_unsupported

__all__ = [
    "KeepTogether", "ScoreBar", "bullets", "callout", "cards_row", "dark_card", "gap", "label_value",
    "para", "score_table", "section_heading", "stat_card", "styles", "subheading", "two_col_cards",
    "register_fonts", "build_pdf", "fallback_pdf", "site_label", "format_date", "safe", "strip_unsupported",
]
