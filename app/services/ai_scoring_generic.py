from __future__ import annotations
from typing import Dict, Any, List
import logging

logger = logging.getLogger("app.ai_scoring_generic")


def _coerce_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def score_generic_assessment(answers: Dict[str, Any], rubric: Dict[str, Any] | None) -> Dict[str, Any]:
    """Score a generic assessment based on a rubric structure.

    Contract:
    - inputs:
      - answers: mapping of question_id -> numeric-ish answer
      - rubric: {
          "categories": [
              {"name": str, "question_ids": [str, ...], "weight": float (optional)}
          ],
          "overall_weights": {"method": "average"|"sum"} (optional)
        }
      If rubric is None or malformed, fall back to averaging all numeric answers into a single category.
    - output:
      {
        "overall_score": float,
        "categories": [{"name": str, "score": float}],
        "scoring_version": "generic_v1",
        "model": "none"
      }
    """
    if not isinstance(answers, dict) or not answers:
        return {"overall_score": 0.0, "categories": [], "scoring_version": "generic_v1", "model": "none"}

    categories_out: List[Dict[str, Any]] = []
    numeric_answers = {k: _coerce_float(v, None) for k, v in answers.items()}
    numeric_answers = {k: v for k, v in numeric_answers.items() if isinstance(v, (int, float))}

    if not rubric or not isinstance(rubric, dict) or not rubric.get("categories"):
        # Fallback: single category averaging all answers
        if numeric_answers:
            avg = sum(numeric_answers.values()) / max(1, len(numeric_answers))
        else:
            avg = 0.0
        categories_out.append({"name": "General", "score": round(avg, 2)})
        overall = avg
    else:
        overall_weights = (rubric.get("overall_weights") or {}).get("method", "average")
        overall_accum = 0.0
        overall_wsum = 0.0
        for cat in rubric.get("categories", []):
            name = cat.get("name") or "Unnamed"
            qids = cat.get("question_ids") or []
            weight = float(cat.get("weight", 1.0) or 1.0)
            vals = [_coerce_float(answers.get(qid), None) for qid in qids]
            vals = [v for v in vals if isinstance(v, (int, float))]
            if vals:
                cat_score = sum(vals) / len(vals)
            else:
                cat_score = 0.0
            cat_score = round(cat_score, 2)
            categories_out.append({"name": name, "score": cat_score})
            if overall_weights == "sum":
                overall_accum += cat_score * weight
                overall_wsum += weight
            else:
                overall_accum += cat_score
                overall_wsum += 1.0
        overall = (overall_accum / overall_wsum) if overall_wsum else 0.0

    out = {
        "overall_score": round(overall, 2),
        "categories": categories_out,
        "scoring_version": "generic_v1",
        "model": "none",
    }
    logger.info("Generic scoring completed: overall=%s categories=%d", out["overall_score"], len(categories_out))
    return out
