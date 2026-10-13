"""Reusable branded flowables for PDF reports.

Every function takes plain strings and escapes them via ``safe()``, unless ``markup=True``
(the caller then passes text it already made safe and added kit tags to).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Sequence

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from . import theme as t
from .fonts import register_fonts
from .text import safe


@lru_cache(maxsize=1)
def styles() -> dict[str, ParagraphStyle]:
    f = register_fonts()

    def s(name, font, size_leading, color, **kw):
        size, leading = size_leading
        return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading, textColor=color, **kw)

    return {
        "body": s("kit-body", f.regular, t.BODY_SIZE, t.BODY, spaceAfter=5),
        "lead": s("kit-lead", f.regular, (10.5, 15.5), t.BODY, spaceAfter=6),
        "small": s("kit-small", f.regular, t.SMALL, t.MUTED),
        "label": s("kit-label", f.semibold, (8, 10), t.MUTED, keepWithNext=1),
        "h2": s("kit-h2", f.semibold, t.H2, t.INK, keepWithNext=1),
        "h3": s("kit-h3", f.semibold, t.H3, t.INK, spaceBefore=2, spaceAfter=3, keepWithNext=1),
        "row": s("kit-row", f.medium, (9.5, 12), t.INK),
        "row_note": s("kit-row-note", f.regular, (8, 10.5), t.MUTED),
        "score": s("kit-score", f.semibold, (9.5, 12), t.INK, alignment=TA_RIGHT),
        "rank": s("kit-rank", f.semibold, (9, 12), t.GOLD_DEEP, alignment=TA_CENTER),
        "callout_title": s("kit-callout-title", f.semibold, (8, 10), t.GOLD_DEEP, spaceAfter=3),
        "callout": s("kit-callout", f.regular, (9.5, 13.5), t.BODY),
        "card_title": s("kit-card-title", f.semibold, (9, 11), t.INK, spaceAfter=4),
        # On dark surfaces
        "dark_big": s("kit-dark-big", f.semibold, (28, 32), t.GOLD),
        "dark_title": s("kit-dark-title", f.semibold, (12, 15), t.WHITE),
        "dark_label": s("kit-dark-label", f.medium, (8, 10), t.ON_DARK_MUTED),
        "dark_body": s("kit-dark-body", f.regular, (8.5, 12), t.ON_DARK),
        "dark_gold": s("kit-dark-gold", f.semibold, (10, 13), t.GOLD),
        "center_small": s("kit-center-small", f.regular, t.SMALL, t.MUTED, alignment=TA_CENTER),
    }


def para(text, style: str = "body", markup: bool = False) -> Paragraph:
    return Paragraph(text if markup else safe(text), styles()[style])


def label_value(label, value) -> Paragraph:
    """'Label: value' with a semibold label."""
    return Paragraph(f"<b>{safe(label)}:</b> {safe(value)}", styles()["body"])


class _HeadingRule(Flowable):
    """Hairline across the frame with a short gold accent on the left."""

    def __init__(self, accent: float = 36, space_after: float = 8):
        super().__init__()
        self.accent = accent
        self.height = 6 + space_after
        self.keepWithNext = 1

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return avail_w, self.height

    def draw(self):
        c = self.canv
        y = self.height - 3
        c.setFillColor(t.HAIRLINE)
        c.rect(0, y, self.width, 0.75, fill=1, stroke=0)
        c.setFillColor(t.GOLD)
        c.rect(0, y - 0.75, self.accent, 2.25, fill=1, stroke=0)


def section_heading(text, space_before: float = 14) -> list:
    # Heading and rule carry keepWithNext, so they move to the next page with the content below them.
    return [Spacer(1, space_before), Paragraph(safe(str(text).upper()), styles()["h2"]), _HeadingRule()]


def subheading(text, markup: bool = False) -> Paragraph:
    return para(text, "h3", markup=markup)


class ScoreBar(Flowable):
    """Gold fill on a light track; value is clamped to [0, max]."""

    def __init__(self, value, max_value, width: float = 120, height: float = 6, fill=None, track=None):
        super().__init__()
        try:
            v = float(value or 0)
        except (TypeError, ValueError):
            v = 0.0
        m = float(max_value or 1)
        self.ratio = max(0.0, min(1.0, v / m)) if m > 0 else 0.0
        self.bar_w = width
        self.height = height
        self.fill = fill or t.GOLD
        self.track = track or t.TRACK

    def wrap(self, avail_w, avail_h):
        self.width = min(self.bar_w, avail_w)
        return self.width, self.height

    def draw(self):
        c = self.canv
        r = self.height / 2
        c.setFillColor(self.track)
        c.roundRect(0, 0, self.width, self.height, r, fill=1, stroke=0)
        if self.ratio > 0:
            c.setFillColor(self.fill)
            c.roundRect(0, 0, max(self.height, self.width * self.ratio), self.height, r, fill=1, stroke=0)


def _fmt_num(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return safe(v) or "-"
    return str(int(f)) if f == int(f) else f"{f:.1f}"


def score_table(rows: Sequence[dict], max_value: float, suffix: str | None = None, show_rank: bool = False, bar_width: float = 130) -> Table:
    """Rows of label (+ optional note), bar and 'N/max'. Row keys: label, value, note?, highlight?, rank?, value_label?."""
    st = styles()
    rank_w = 24 if show_rank else 0
    score_w = 46
    label_w = t.CONTENT_WIDTH - rank_w - bar_width - score_w
    data, cmds = [], [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, t.HAIRLINE),
    ]
    for i, r in enumerate(rows):
        label_cell = [Paragraph(safe(r.get("label")), st["row"])]
        if r.get("note"):
            label_cell.append(Paragraph(safe(r["note"]), st["row_note"]))
        value_text = r.get("value_label") or (f"{_fmt_num(r.get('value'))}{suffix}" if suffix else f"{_fmt_num(r.get('value'))}/{_fmt_num(max_value)}")
        row = []
        if show_rank:
            row.append(Paragraph(safe(r.get("rank", "")), st["rank"]))
        row += [label_cell, ScoreBar(r.get("value"), max_value, width=bar_width - 12, fill=r.get("fill")), Paragraph(safe(value_text), st["score"])]
        data.append(row)
        if r.get("highlight"):
            cmds.append(("BACKGROUND", (0, i), (-1, i), t.GOLD_TINT))
    widths = ([rank_w] if show_rank else []) + [label_w, bar_width, score_w]
    tbl = Table(data, colWidths=widths, hAlign="LEFT")
    tbl.setStyle(TableStyle(cmds))
    return tbl


def dark_card(content: list, width: float, padding: float = 12) -> Table:
    tbl = Table([[content]], colWidths=[width])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), t.SURFACE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return tbl


def stat_card(big, label, sub=None) -> Table:
    """Full-width dark card: big gold number left, label and sub-label right."""
    st = styles()
    right = [Paragraph(safe(label), st["dark_title"])]
    if sub:
        right.append(Spacer(1, 2))
        right.append(Paragraph(safe(sub), st["dark_gold"]))
    inner = Table([[Paragraph(safe(big), st["dark_big"]), right]], colWidths=[120, t.CONTENT_WIDTH - 120 - 32])
    inner.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return dark_card([inner], t.CONTENT_WIDTH, padding=16)


def cards_row(cards: Sequence[list], gap: float = 8) -> Table:
    """Equal-width dark cards side by side; each card is a list of flowables."""
    n = max(1, len(cards))
    w = (t.CONTENT_WIDTH - gap * (n - 1)) / n
    row, widths = [], []
    for i, content in enumerate(cards):
        if i:
            row.append("")
            widths.append(gap)
        row.append(dark_card(content, w))
        widths.append(w)
    tbl = Table([row], colWidths=widths, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tbl


def callout(title, body: Iterable | str, markup: bool = False) -> Table:
    """Gold left bar on a tinted fill. ``body`` is a string or a list of lines."""
    st = styles()
    lines = [body] if isinstance(body, str) else list(body)
    content = [Paragraph(safe(str(title).upper()), st["callout_title"])] if title else []
    content += [Paragraph(x if markup else safe(x), st["callout"]) for x in lines if x]
    tbl = Table([["", content]], colWidths=[3, t.CONTENT_WIDTH - 3], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), t.GOLD),
        ("BACKGROUND", (1, 0), (1, 0), t.GOLD_TINT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return tbl


def bullets(items: Iterable, markup: bool = False, style: str = "body") -> ListFlowable | Spacer:
    f = register_fonts()
    st = styles()[style]
    entries = [ListItem(Paragraph(x if markup else safe(x), st), leftIndent=12) for x in items if x]
    if not entries:
        return Spacer(1, 0)
    return ListFlowable(
        entries,
        bulletType="bullet",
        start="•",
        bulletFontName=f.bold,
        bulletFontSize=9,
        bulletColor=t.GOLD,
        leftIndent=12,
        bulletOffsetY=0,
    )


def two_col_cards(left_title, left_items: Sequence, right_title, right_items: Sequence, empty: str = "-") -> Table:
    """Two tinted cards side by side (e.g. strengths / growth areas)."""
    st = styles()
    gap = 8
    w = (t.CONTENT_WIDTH - gap) / 2

    def col(title, items):
        return [Paragraph(safe(str(title).upper()), st["callout_title"]), bullets(items) if items else Paragraph(safe(empty), st["body"])]

    tbl = Table([[col(left_title, left_items), "", col(right_title, right_items)]], colWidths=[w, gap, w], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), t.GOLD_TINT),
        ("BACKGROUND", (2, 0), (2, 0), t.GOLD_TINT),
        ("LINEABOVE", (0, 0), (0, 0), 2, t.GOLD),
        ("LINEABOVE", (2, 0), (2, 0), 2, t.GOLD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def gap(h: float = 8) -> Spacer:
    return Spacer(1, h)


__all__ = [
    "styles", "para", "label_value", "section_heading", "subheading", "ScoreBar", "score_table",
    "dark_card", "stat_card", "cards_row", "callout", "bullets", "two_col_cards", "gap",
    "KeepTogether", "TA_LEFT",
]
