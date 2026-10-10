"""One source of truth for the numbers shown in assessment reports.

The mentor report blob (``Assessment.mentor_report_v2``) is the canonical store for an
assessment's Health Score, band and Biblical Knowledge percent. Every endpoint, email and
Premium report reads them through ``summarize_mentor_blob`` so the apprentice, the mentor and
the Premium report always agree.

New assessments get their Health Score computed here (``apply_canonical_scores``) rather than
by the LLM, using the documented formula: 60% multiple-choice accuracy, 40% open-ended maturity.
"""
from __future__ import annotations

import copy
from typing import Any, Optional

# Insight levels come from the prompt's rubric average (1-5): Flourishing 4.5+, Maturing
# 3.75-4.49, Stable 3-3.74, Developing 2-2.99, Beginning <2. Each maps to its band's midpoint
# expressed as a percent of 5.
LEVEL_PERCENT = {
    "flourishing": 95.0,
    "maturing": 82.0,
    "stable": 67.0,
    "developing": 50.0,
    "beginning": 30.0,
}

MC_WEIGHT = 0.6
OPEN_WEIGHT = 0.4


def health_band(score: int) -> str:
    if score >= 85:
        return "Flourishing"
    if score >= 70:
        return "Maturing"
    if score >= 55:
        return "Stable"
    if score >= 40:
        return "Developing"
    return "Beginning"


def open_level_percent(insights: list[dict] | None) -> Optional[float]:
    """Average maturity of the open-ended insights as a percent, or None if there are none."""
    values = [LEVEL_PERCENT[lvl] for lvl in
              ((i or {}).get("level", "").strip().lower() for i in insights or [])
              if lvl in LEVEL_PERCENT]
    return sum(values) / len(values) if values else None


def compute_health_score(mc_percent: float, insights: list[dict] | None) -> int:
    """round(mc * 0.6 + open * 0.4); falls back to MC accuracy when there are no open insights."""
    open_pct = open_level_percent(insights)
    if open_pct is None:
        return int(round(mc_percent))
    return int(round(mc_percent * MC_WEIGHT + open_pct * OPEN_WEIGHT))


def apply_canonical_scores(blob: dict, mc_percent: float) -> dict:
    """Set the blob's Biblical Knowledge percent and Health Score from deterministic inputs.

    ``mc_percent`` is the graded multiple-choice accuracy (0-100) computed in code from the
    questions' ``is_correct`` flags. Mutates and returns ``blob``.
    """
    mc = round(float(mc_percent or 0.0), 1)
    bk = blob.get("biblical_knowledge")
    if not isinstance(bk, dict):
        bk = {}
        blob["biblical_knowledge"] = bk
    bk["percent"] = mc
    score = compute_health_score(mc, blob.get("insights"))
    blob["health_score"] = score
    blob["health_band"] = health_band(score)
    return blob


def summarize_mentor_blob(blob: dict | None) -> dict[str, Any]:
    """Headline numbers from a stored mentor blob (v2.1 or legacy v2.0 shape)."""
    blob = blob or {}
    if "health_score" in blob:  # v2.1
        bk = blob.get("biblical_knowledge") or {}
        score = int(blob.get("health_score") or 0)
        return {
            "format": "v2.1",
            "health_score": score,
            "health_band": blob.get("health_band") or health_band(score),
            "mc_percent": float(bk.get("percent") or 0.0),
            "weak_topics": list(bk.get("weak_topics") or []),
        }
    snapshot = blob.get("snapshot") or {}  # legacy v2.0: MC percent doubled as the headline
    knowledge = blob.get("biblical_knowledge") or {}
    mc = float(snapshot.get("overall_mc_percent") or knowledge.get("mc_percent") or 0.0)
    return {
        "format": "legacy" if snapshot else "empty",
        "health_score": int(mc),
        "health_band": snapshot.get("knowledge_band") or health_band(int(mc)),
        "mc_percent": mc,
        "weak_topics": [t.get("topic") for t in (knowledge.get("topic_breakdown") or [])
                        if t.get("total") and t.get("correct", 0) / t["total"] < 0.6],
    }


def public_full_report(report: dict | None, mentor_blob: dict | None) -> dict | None:
    """Client-safe copy of a cached Premium report.

    Aligns the executive summary's Health Score/band with the canonical blob and drops
    generation metadata (provider, model, cost, latency) that shouldn't reach the app.
    The stored report is not modified.
    """
    if not isinstance(report, dict):
        return report
    out = copy.deepcopy(report)
    meta = out.get("_meta")
    out["_meta"] = {"generated_at": meta.get("generated_at")} if isinstance(meta, dict) else {}
    if mentor_blob and "health_score" in mentor_blob:
        summary = summarize_mentor_blob(mentor_blob)
        exec_summary = out.get("executive_summary")
        if isinstance(exec_summary, dict):
            exec_summary["health_score"] = summary["health_score"]
            exec_summary["health_band"] = summary["health_band"]
    return out
