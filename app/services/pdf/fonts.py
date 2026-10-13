"""Poppins registration for PDF reports, with a Helvetica fallback (research R3)."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "fonts"))


@dataclass(frozen=True)
class FontSet:
    regular: str
    medium: str
    semibold: str
    bold: str


_FALLBACK = FontSet("Helvetica", "Helvetica", "Helvetica-Bold", "Helvetica-Bold")
_cached: FontSet | None = None


def register_fonts() -> FontSet:
    global _cached
    if _cached is not None:
        return _cached
    weights = {"regular": "Regular", "medium": "Medium", "semibold": "SemiBold", "bold": "Bold"}
    names = {}
    try:
        for key, weight in weights.items():
            name = f"Poppins-{weight}"
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS_DIR, f"Poppins-{weight}.ttf")))
            names[key] = name
        # Paragraph <b>/<i> resolve through the family mapping; Poppins has no italic here.
        addMapping("Poppins-Regular", 0, 0, "Poppins-Regular")
        addMapping("Poppins-Regular", 1, 0, "Poppins-Bold")
        addMapping("Poppins-Regular", 0, 1, "Poppins-Regular")
        addMapping("Poppins-Regular", 1, 1, "Poppins-Bold")
        _cached = FontSet(**names)
    except Exception as e:  # missing/corrupt font file
        logger.warning("Poppins unavailable for PDFs, using Helvetica: %s", type(e).__name__)
        _cached = _FALLBACK
    return _cached
