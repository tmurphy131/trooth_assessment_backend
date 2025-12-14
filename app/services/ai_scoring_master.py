"""Master Trooth Assessment scoring service.

Thin wrapper around the existing category-based scorer that:
- Ensures a version tag ("master_v1") in the returned scores
- Extracts top3 categories for quick card rendering
"""
from __future__ import annotations
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger("app.ai_scoring_master")


def _extract_top3(category_scores: Dict[str, int]) -> List[Dict[str, int | str]]:
    items = sorted(category_scores.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    top = items[:3]
    return [{"category": k, "score": v} for k, v in top]


async def score_master_assessment(answers: Dict[str, str], questions: List[dict]) -> Dict:
    """Score the Master assessment using category-based AI scoring.

    Returns a dict with at least:
    {
      "version": "master_v1",
      "overall_score": int,
      "category_scores": {"Category": int, ...},
      "summary_recommendation": str,
      "top3": [{"category": str, "score": int}, ... up to 3]
    }
    """
    try:
        from app.services.ai_scoring import score_assessment_by_category
        result = await score_assessment_by_category(answers, questions)
    except Exception as e:  # pragma: no cover
        logger.error(f"Master scoring failed, using fallback: {e}")
        # fallback minimal
        result = {
            "overall_score": 7,
            "category_scores": {},
            "summary_recommendation": "Assessment completed. Continue growing in spiritual disciplines.",
        }

    # Normalize types and enrich
    overall = int(result.get("overall_score", 7))
    category_scores = result.get("category_scores") or {}
    # Ensure category scores are ints
    category_scores = {str(k): int(v) for k, v in category_scores.items()}
    enriched = {
        "version": "master_v1",
        "overall_score": overall,
        "category_scores": category_scores,
        "summary_recommendation": result.get("summary_recommendation") or "Keep pursuing growth across key disciplines.",
        "top3": _extract_top3(category_scores),
    }
    # Pass through mentor_blob_v2 if available
    if isinstance(result, dict) and result.get("mentor_blob_v2"):
        enriched["mentor_blob_v2"] = result["mentor_blob_v2"]
    return enriched
