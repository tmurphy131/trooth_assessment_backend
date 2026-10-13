"""Spiritual Gifts PDF / HTML report generation (specs/008-pdf-redesign).

The PDF is built on the shared branded kit in ``app.services.pdf``. Sections follow
``specs/008-pdf-redesign/contracts/pdf-reports.md``.
"""
from __future__ import annotations

import html as _html
import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional

from app.data.spiritual_gift_guidance import GIFT_GUIDANCE
from app.services import pdf as kit
from app.services.pdf import theme as t
from app.services.spiritual_gifts_scoring import canonical_slug, display_to_slug

logger = logging.getLogger(__name__)

MAX_SCORE = 12
MAX_DEEP_DIVES = 6
BANDS = [
    ("strongest", "Strongest", "9-12"),
    ("developing", "Developing", "5-8"),
    ("less_evident", "Less evident", "0-4"),
]


def _band(score: int) -> str:
    return "strongest" if score >= 9 else "developing" if score >= 5 else "less_evident"


def _definitions_by_slug(definitions: Dict[str, Dict]) -> Dict[str, Dict]:
    """Definitions are keyed by DB slug (e.g. 'pastor_shepherd'); normalize to MAP slugs."""
    out: Dict[str, Dict] = {}
    for key, d in (definitions or {}).items():
        slug = display_to_slug(key) or display_to_slug(d.get("display_name") or "") or canonical_slug(key)
        out[slug] = d
    return out


def _prepare_gifts(scores: Dict, definitions: Dict[str, Dict]) -> Dict:
    """Ranked rows plus the deep-dive selection (research R8, R10)."""
    defs = _definitions_by_slug(definitions)
    all_scores = scores.get("all_scores") or []
    truncated = scores.get("top_gifts_truncated") or all_scores[:3]
    expanded = scores.get("top_gifts_expanded") or truncated
    top_names = {g.get("gift") for g in truncated}
    expanded_names = {g.get("gift") for g in expanded}

    rows: List[Dict] = []
    for i, g in enumerate(all_scores, start=1):
        name = g.get("gift") or ""
        slug = display_to_slug(name) or canonical_slug(name)
        d = defs.get(slug, {})
        try:
            score = int(g.get("score") or 0)
        except (TypeError, ValueError):
            score = 0
        rows.append({
            "slug": slug,
            "gift": name,
            "score": score,
            "rank": i,
            "band": _band(score),
            "is_top": name in top_names,
            "is_tied_third": name in expanded_names and name not in top_names,
            "summary": (d.get("short_summary") or "").strip(),
            "definition": (d.get("full_definition") or d.get("short_summary") or "").strip(),
            "guidance": GIFT_GUIDANCE.get(slug),
        })

    by_name = {r["gift"]: r for r in rows}
    dive_rows = [by_name[g.get("gift")] for g in expanded if g.get("gift") in by_name]
    if not dive_rows:
        dive_rows = rows[:3]
    return {
        "rows": rows,
        "top": [r for r in rows if r["is_top"]][:3] or rows[:3],
        "tied_third": [r for r in rows if r["is_tied_third"]],
        "deep_dive": dive_rows[:MAX_DEEP_DIVES],
        "also_tied": dive_rows[MAX_DEEP_DIVES:],
    }


def _top_card(r: Dict, width: float) -> list:
    content = [
        kit.para(f"#{r['rank']}", "dark_label"),
        kit.gap(2),
        kit.para(r["gift"], "dark_title"),
        kit.gap(6),
        kit.ScoreBar(r["score"], MAX_SCORE, width=width - 24, height=5, track=t.RULE_DARK),
        kit.gap(4),
        kit.para(f"{r['score']}/{MAX_SCORE}", "dark_gold"),
    ]
    if r["summary"]:
        content += [kit.gap(4), kit.para(r["summary"], "dark_body")]
    return content


def _deep_dive(r: Dict) -> list:
    g = r["guidance"] or {}
    label = "Tied for 3rd" if r["is_tied_third"] else f"#{r['rank']}"
    block = [kit.subheading(f"{label}  ·  {r['gift']}  ·  {r['score']}/{MAX_SCORE}")]
    if r["definition"]:
        block.append(kit.para(r["definition"]))
    if g.get("scriptures"):
        block += [kit.gap(2), kit.callout("In Scripture", "  ·  ".join(g["scriptures"])), kit.gap(6)]
    if g.get("ways_to_serve"):
        block += [kit.para("WAYS TO USE THIS GIFT", "label"), kit.gap(3), kit.bullets(g["ways_to_serve"])]
    if g.get("reflection"):
        block += [kit.gap(4), kit.callout("Reflect", g["reflection"])]
    return [kit.KeepTogether(block), kit.gap(14)]


def build_gifts_story(apprentice_name: Optional[str], scores: Dict, definitions: Dict[str, Dict]) -> list:
    prep = _prepare_gifts(scores, definitions)
    rows, top = prep["rows"], prep["top"]
    story: list = []

    story.append(kit.para(
        "Spiritual gifts are abilities the Holy Spirit gives every believer to build up the church "
        "and serve others (1 Corinthians 12:4-7; 1 Peter 4:10). Each gift below is scored from 0 to 12 "
        "based on your answers: the higher the score, the more strongly that gift showed up. Scores "
        "describe where you are today, so use them as a starting point for conversation and service.",
        "lead",
    ))

    # Your top gifts
    story += kit.section_heading("Your top gifts", space_before=8)
    if top:
        card_w = (t.CONTENT_WIDTH - 8 * (len(top) - 1)) / len(top)
        story.append(kit.cards_row([_top_card(r, card_w) for r in top]))
        if prep["tied_third"]:
            names = ", ".join(r["gift"] for r in prep["tied_third"])
            story += [kit.gap(6), kit.para(f"Tied for 3rd ({prep['tied_third'][0]['score']}/{MAX_SCORE}): {names}", "small")]
    else:
        story.append(kit.para("No scores were recorded for this assessment."))

    # Deep dives
    if prep["deep_dive"]:
        story += kit.section_heading("Your gifts in depth")
        for r in prep["deep_dive"]:
            story += _deep_dive(r)
        if prep["also_tied"]:
            story.append(kit.para("Also tied: " + ", ".join(r["gift"] for r in prep["also_tied"]), "small"))

    # All gifts ranked, grouped by band
    if rows:
        story += kit.section_heading("All gifts ranked")
        for key, title, rng in BANDS:
            band_rows = [r for r in rows if r["band"] == key]
            if not band_rows:
                continue
            story.append(kit.KeepTogether([
                kit.subheading(f"{title}  <font color='{t.hex_of(t.MUTED)}' size='8.5'>{rng}</font>", markup=True),
                kit.score_table([
                    {
                        "rank": r["rank"],
                        "label": r["gift"],
                        "note": r["summary"],
                        "value": r["score"],
                        "highlight": r["is_top"] or r["is_tied_third"],
                    }
                    for r in band_rows[:1]
                ], MAX_SCORE, show_rank=True),
            ]))
            if len(band_rows) > 1:
                story.append(kit.score_table([
                    {
                        "rank": r["rank"],
                        "label": r["gift"],
                        "note": r["summary"],
                        "value": r["score"],
                        "highlight": r["is_top"] or r["is_tied_third"],
                    }
                    for r in band_rows[1:]
                ], MAX_SCORE, show_rank=True))
            story.append(kit.gap(10))

    # Next steps
    if top:
        first = top[0]
        first_way = ((first["guidance"] or {}).get("ways_to_serve") or [None])[0]
        steps = [f"Talk with your mentor about your {first['gift']} gift and where it could serve right now."]
        if first_way:
            steps.append(f"Try this in the next two weeks: {first_way}")
        steps.append("Ask people who know you well whether they see these gifts in you. Gifts are confirmed in community.")
        steps.append("Retake the assessment in 6 to 12 months to see how your gifts are growing.")
        story += kit.section_heading("Next steps")
        story.append(kit.bullets(steps))
        story += [kit.gap(10), kit.callout(None, "Romans 12:6  ·  We have different gifts, according to the grace given to us. Use yours.")]
    return story


def generate_pdf(
    apprentice_name: Optional[str],
    version: int,
    scores: Dict,
    definitions: Dict[str, Dict],
    *,
    assessment_date=None,
) -> bytes:
    """Branded Spiritual Gifts PDF. ``version`` is accepted for compatibility but not printed."""
    name = (apprentice_name or "").strip() or "Apprentice"
    date_label = kit.format_date(assessment_date) or f"Generated {kit.format_date(datetime.now(UTC))}"
    top = (scores.get("top_gifts_truncated") or (scores.get("all_scores") or [])[:3])
    fallback = ["Your top gifts:"] + [f"{i}. {g.get('gift')} - {g.get('score')}/{MAX_SCORE}" for i, g in enumerate(top, 1)]
    return kit.build_pdf(
        "Spiritual Gifts Report",
        name,
        date_label,
        lambda: build_gifts_story(name, scores, definitions),
        fallback_lines=fallback,
        context_id="spiritual_gifts",
    )


def generate_html(apprentice_name: Optional[str], version: int, scores: Dict, definitions: Dict[str, Dict]) -> str:
    esc = _html.escape
    prep = _prepare_gifts(scores, definitions)
    name = esc(apprentice_name or "Apprentice")
    date = esc(kit.format_date(datetime.now(UTC)) or "")

    def li(r: Dict) -> str:
        summ = f" - {esc(r['summary'])}" if r["summary"] else ""
        return f"<li><strong>{esc(r['gift'])}</strong>: {r['score']}/{MAX_SCORE}{summ}</li>"

    top_html = "".join(li(r) for r in prep["top"])
    tied = ""
    if prep["tied_third"]:
        tied = "<p>Tied for 3rd: " + esc(", ".join(r["gift"] for r in prep["tied_third"])) + "</p>"
    all_html = "".join(li(r) for r in prep["rows"])
    return (
        "<div style='font-family:Arial,sans-serif;'>"
        f"<h1>Spiritual Gifts Report</h1><p>{name} &middot; {date}</p>"
        f"<h2>Top gifts</h2><ul>{top_html}</ul>{tied}"
        f"<h2>All gifts ranked</h2><ul>{all_html}</ul>"
        "</div>"
    )
