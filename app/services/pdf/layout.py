"""Page chrome and document builder for branded PDF reports (research R2, R5)."""
from __future__ import annotations

import io
import logging
import os
from typing import Callable, Iterable
from urllib.parse import urlparse

from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import BaseDocTemplate, Frame, NextPageTemplate, PageTemplate

from . import theme as t
from .fonts import register_fonts
from .text import strip_unsupported

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets"))
LOGO_PATH = os.path.join(ASSETS_DIR, "pdf_logo.png")
_logo: ImageReader | None = None
_logo_loaded = False


def _get_logo() -> ImageReader | None:
    global _logo, _logo_loaded
    if not _logo_loaded:
        _logo_loaded = True
        try:
            _logo = ImageReader(LOGO_PATH)
        except Exception as e:
            logger.warning("PDF logo unavailable: %s", type(e).__name__)
            _logo = None
    return _logo


def site_label() -> str:
    try:
        from app.core.settings import settings

        host = urlparse(settings.app_landing_url).netloc or settings.app_landing_url
    except Exception:
        host = "onlyblv.com"
    return host.removeprefix("www.")


def _draw_wordmark(c, x: float, y: float, size: float, regular: str) -> float:
    """Text fallback for the logo: 'T[root]H' with gold 'root'. Returns width."""
    parts = [("T[", t.WHITE), ("root", t.GOLD), ("]H", t.WHITE)]
    cx = x
    for text, color in parts:
        c.setFillColor(color)
        c.setFont(regular, size)
        c.drawString(cx, y, text)
        cx += c.stringWidth(text, regular, size)
    return cx - x


def _draw_logo(c, x: float, center_y: float, height: float, font: str) -> None:
    logo = _get_logo()
    if logo is not None:
        iw, ih = logo.getSize()
        width = height * iw / ih
        c.drawImage(logo, x, center_y - height / 2, width=width, height=height, mask="auto")
    else:
        _draw_wordmark(c, x, center_y - height / 4, height * 0.6, font)


class _Chrome:
    """onPage callbacks drawing the header band (first page) and strip (later pages)."""

    def __init__(self, title: str, subtitle: str):
        self.title = strip_unsupported(title)
        self.subtitle = strip_unsupported(subtitle)
        self.fonts = register_fonts()

    def first(self, c, doc):
        f = self.fonts
        c.saveState()
        top = t.PAGE_HEIGHT
        c.setFillColor(t.CHARCOAL)
        c.rect(0, top - t.BAND_HEIGHT, t.PAGE_WIDTH, t.BAND_HEIGHT, fill=1, stroke=0)
        c.setFillColor(t.GOLD)
        c.rect(0, top - t.BAND_HEIGHT - 2, t.PAGE_WIDTH, 2, fill=1, stroke=0)
        mid = top - t.BAND_HEIGHT / 2
        _draw_logo(c, t.MARGIN_X, mid, 40, f.bold)
        right = t.PAGE_WIDTH - t.MARGIN_X
        # Shrink long titles so they never run into the logo (logo is ~130 pt wide)
        max_w = t.CONTENT_WIDTH - 150
        size = t.TITLE[0]
        while size > 12 and c.stringWidth(self.title, f.semibold, size) > max_w:
            size -= 1
        c.setFillColor(t.GOLD)
        c.setFont(f.semibold, size)
        c.drawRightString(right, mid + 2, self.title)
        if self.subtitle:
            c.setFillColor(t.ON_DARK)
            c.setFont(f.regular, 9.5)
            c.drawRightString(right, mid - 15, self.subtitle)
        c.restoreState()

    def later(self, c, doc):
        f = self.fonts
        c.saveState()
        top = t.PAGE_HEIGHT
        c.setFillColor(t.CHARCOAL)
        c.rect(0, top - t.STRIP_HEIGHT, t.PAGE_WIDTH, t.STRIP_HEIGHT, fill=1, stroke=0)
        c.setFillColor(t.GOLD)
        c.rect(0, top - t.STRIP_HEIGHT - 1.5, t.PAGE_WIDTH, 1.5, fill=1, stroke=0)
        mid = top - t.STRIP_HEIGHT / 2
        _draw_logo(c, t.MARGIN_X, mid, 16, f.bold)
        c.setFillColor(t.GOLD)
        c.setFont(f.semibold, 9)
        label = self.title + (f"  ·  {self.subtitle}" if self.subtitle else "")
        c.drawRightString(t.PAGE_WIDTH - t.MARGIN_X, mid - 3, label)
        c.restoreState()


class NumberedCanvas(rl_canvas.Canvas):
    """Defers pages so the footer can say 'Page X of Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages: list[dict] = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int):
        f = register_fonts()
        y = t.FOOTER_HEIGHT - 12
        self.saveState()
        self.setStrokeColor(t.GOLD)
        self.setLineWidth(0.75)
        self.line(t.MARGIN_X, y + 12, t.PAGE_WIDTH - t.MARGIN_X, y + 12)
        self.setFillColor(t.MUTED)
        self.setFont(f.regular, 8)
        self.drawString(t.MARGIN_X, y, f"T[root]H Discipleship  ·  {site_label()}")
        self.drawRightString(t.PAGE_WIDTH - t.MARGIN_X, y, f"Page {self._pageNumber} of {total}")
        self.restoreState()


def _doc(buf, title: str, subtitle: str) -> BaseDocTemplate:
    chrome = _Chrome(title, subtitle)
    bottom = t.FOOTER_HEIGHT + 12
    first_top = t.PAGE_HEIGHT - t.BAND_HEIGHT - 22
    later_top = t.PAGE_HEIGHT - t.STRIP_HEIGHT - 20
    doc = BaseDocTemplate(
        buf,
        pagesize=t.PAGE_SIZE,
        leftMargin=t.MARGIN_X,
        rightMargin=t.MARGIN_X,
        topMargin=t.PAGE_HEIGHT - first_top,
        bottomMargin=bottom,
        title=f"{title} - {subtitle}" if subtitle else title,
        author="T[root]H Discipleship",
    )
    first = Frame(t.MARGIN_X, bottom, t.CONTENT_WIDTH, first_top - bottom, id="first", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    later = Frame(t.MARGIN_X, bottom, t.CONTENT_WIDTH, later_top - bottom, id="later", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="first", frames=[first], onPage=chrome.first, autoNextPageTemplate="later"),
        PageTemplate(id="later", frames=[later], onPage=chrome.later),
    ])
    return doc


def subtitle_for(subject: str | None, date_label: str | None) -> str:
    return "  ·  ".join(p for p in [(subject or "").strip(), (date_label or "").strip()] if p)


def build_pdf(
    title: str,
    subject: str | None,
    date_label: str | None,
    story_fn: Callable[[], list],
    fallback_lines: Iterable[str] = (),
    context_id: str | None = None,
) -> bytes:
    """Render a branded PDF. Never returns non-PDF bytes: on failure, a simple branded fallback."""
    subtitle = subtitle_for(subject, date_label)
    try:
        buf = io.BytesIO()
        doc = _doc(buf, title, subtitle)
        story = [NextPageTemplate("later")] + list(story_fn())
        doc.build(story, canvasmaker=NumberedCanvas)
        return buf.getvalue()
    except Exception as e:
        logger.error("PDF render failed (%s) for %s; sending fallback", type(e).__name__, context_id or title)
        return fallback_pdf(title, subtitle, list(fallback_lines))


def fallback_pdf(title: str, subtitle: str, lines: list[str]) -> bytes:
    """Minimal branded PDF drawn with built-in fonts only, so it cannot fail on fonts or markup."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=t.PAGE_SIZE)
    c.setTitle(title)

    def band():
        c.setFillColor(t.CHARCOAL)
        c.rect(0, t.PAGE_HEIGHT - 72, t.PAGE_WIDTH, 72, fill=1, stroke=0)
        _draw_wordmark(c, t.MARGIN_X, t.PAGE_HEIGHT - 44, 18, "Helvetica-Bold")
        c.setFillColor(t.GOLD)
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(t.PAGE_WIDTH - t.MARGIN_X, t.PAGE_HEIGHT - 38, _latin1(title))
        c.setFillColor(t.ON_DARK)
        c.setFont("Helvetica", 9)
        c.drawRightString(t.PAGE_WIDTH - t.MARGIN_X, t.PAGE_HEIGHT - 54, _latin1(subtitle))

    band()
    y = t.PAGE_HEIGHT - 100
    c.setFont("Helvetica", 10)
    c.setFillColor(t.BODY)
    for raw in lines:
        for line in simpleSplit(_latin1(raw), "Helvetica", 10, t.CONTENT_WIDTH) or [""]:
            if y < 60:
                c.showPage()
                band()
                y = t.PAGE_HEIGHT - 100
                c.setFont("Helvetica", 10)
                c.setFillColor(t.BODY)
            c.drawString(t.MARGIN_X, y, line)
            y -= 14
        y -= 4
    c.setFillColor(t.MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(t.MARGIN_X, 30, f"T[root]H Discipleship  -  {site_label()}")
    c.save()
    return buf.getvalue()


def _latin1(text) -> str:
    """Built-in fonts are Latin-1; replace anything else."""
    s = strip_unsupported(str(text or ""))
    s = s.replace("—", "-").replace("–", "-").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("•", "-").replace("·", "-")
    return s.encode("latin-1", "replace").decode("latin-1")
