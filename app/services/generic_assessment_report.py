"""Generic assessment PDF / HTML report (specs/008-pdf-redesign).

Used when an assessment has no mentor-report data; otherwise routes render the mentor
report PDF (``master_trooth_report.render_pdf_v2``).
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional

from app.services import pdf as kit
from app.services.pdf import theme as t

logger = logging.getLogger(__name__)


def _categories(scores: Dict) -> List[Dict]:
    """Category rows from either ``categories`` (list) or ``category_scores`` (dict)."""
    cats = scores.get("categories")
    if isinstance(cats, list) and cats:
        return [c for c in cats if isinstance(c, dict)]
    return [{"name": k, "score": v} for k, v in (scores.get("category_scores") or {}).items()]


def _num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_generic_story(title: str, scores: Dict) -> list:
    scores = scores or {}
    story: list = []
    overall = scores.get("overall_score")
    if overall is not None:
        story += [kit.stat_card(f"{overall}/10", "Overall score", title or "Assessment"), kit.gap(10)]

    if scores.get("summary_recommendation"):
        story.append(kit.callout("Summary", str(scores["summary_recommendation"])))

    cats = _categories(scores)
    if cats:
        story += kit.section_heading("Category scores")
        story.append(kit.score_table([
            {
                "label": c.get("name"),
                "value": _num(c.get("score")) * 10 / (_num(c.get("max_score")) or 10),
                "note": c.get("level") if c.get("level") not in (None, "", "-") else None,
                "fill": t.status_color(_num(c.get("score")) / (_num(c.get("max_score")) or 10)),
                "value_label": f"{c.get('score', 0)}/{c.get('max_score') or 10}",
            }
            for c in cats
        ], 10))

    recs = scores.get("recommendations") or []
    if isinstance(recs, list) and recs:
        story += kit.section_heading("Recommendations")
        story.append(kit.bullets([r if isinstance(r, str) else (r.get("text") or r.get("title") or "") for r in recs]))

    story += [kit.gap(14), kit.para("Open the T[root]H app for your full report and next steps.", "small")]
    return story


def generate_pdf(title: str, apprentice_name: Optional[str], scores: Dict, *, assessment_date=None) -> bytes:
    title = (title or "").strip() or "Assessment Report"
    scores = scores or {}
    date_label = kit.format_date(assessment_date) or f"Generated {kit.format_date(datetime.now(UTC))}"
    fallback = [f"Overall score: {scores.get('overall_score', '-')}"] + [
        f"{c.get('name')}: {c.get('score')}" for c in _categories(scores)
    ]
    return kit.build_pdf(
        title,
        (apprentice_name or "").strip() or "Apprentice",
        date_label,
        lambda: build_generic_story(title, scores),
        fallback_lines=fallback,
        context_id="generic_assessment",
    )
