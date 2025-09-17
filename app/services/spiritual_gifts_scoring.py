"""Spiritual Gifts scoring logic (v1).

Single source of truth: imports MAP (gift_slug -> codes) and QUESTION_ITEMS
from ``app.core.spiritual_gifts_map`` to avoid drift. Scores are computed
purely from submitted answer dict keyed by question_code (Q01..Q72).
"""
from typing import Dict, List, Tuple
from app.core.spiritual_gifts_map import MAP as CORE_MAP, QUESTION_ITEMS

# Build canonical friendly display gift names by title-casing slug variants
# (retain original mixed forms where applicable). We'll map slugs to display
# names by inspecting QUESTION_ITEMS first occurrence.
_slug_display: Dict[str, str] = {}
for code, gift_slug, _text in QUESTION_ITEMS:
    if gift_slug not in _slug_display:
        # Convert slug to display heuristically (replace hyphen with space & title case)
        disp = gift_slug.replace('-', ' ').title()
        # Special case: pastor-shepherd -> Pastor/Shepherd
        if gift_slug == 'pastor-shepherd':
            disp = 'Pastor/Shepherd'
        if gift_slug == 'music-worship':
            disp = 'Music/Worship'
        if gift_slug == 'tongues-interpretation':
            disp = 'Tongues & Interpretation'
        _slug_display[gift_slug] = disp

# Create gift->codes mapping with display names as keys to maintain backward
# compatibility with existing API responses that use display names.
GIFT_ITEM_MAP: Dict[str, List[str]] = { _slug_display[slug]: codes for slug, codes in CORE_MAP.items() }

ALL_ITEMS = {item for codes in CORE_MAP.values() for item in codes}

def validate_answers(answers: Dict[str, int]) -> List[str]:
    """Return list of validation error messages (empty if valid)."""
    errors: List[str] = []
    # Check presence
    missing = [q for q in sorted(ALL_ITEMS) if q not in answers]
    if missing:
        errors.append(f"Missing items: {', '.join(missing)}")
    # Check extraneous
    extraneous = [k for k in answers.keys() if k not in ALL_ITEMS]
    if extraneous:
        errors.append(f"Unexpected items: {', '.join(extraneous)}")
    # Range check
    out_of_range = [k for k,v in answers.items() if k in ALL_ITEMS and not isinstance(v,int) or (isinstance(v,int) and (v < 0 or v > 4))]
    if out_of_range:
        errors.append(f"Out-of-range (0-4) values: {', '.join(sorted(out_of_range))}")
    return errors

def score_answers(answers: Dict[str, int]) -> Dict:
    """Compute per-gift scores and ranking structures.

    Returns structure:
    {
      "version": 1,
      "scoring_algorithm": "simple_sum_v1",
      "all_scores": [{"gift": name, "score": int}],
      "top_gifts_truncated": [... up to 3 ...],
      "top_gifts_expanded": [... ties at 3rd ...],
      "rank_meta": {"third_place_score": int|None}
    }
    """
    # Per-gift sum
    per_gift: List[Tuple[str,int]] = []
    for gift_display, codes in GIFT_ITEM_MAP.items():
        s = sum(answers.get(code, 0) for code in codes)
        per_gift.append((gift_display, s))
    # Sort deterministic: score desc, gift name asc
    per_gift.sort(key=lambda x: (-x[1], x[0].lower()))
    all_scores = [{"gift": g, "score": s} for g,s in per_gift]
    # Truncated top 3
    top_truncated = all_scores[:3]
    # Expanded ties at rank 3
    if len(all_scores) >= 3:
        third_score = all_scores[2]['score']
        expanded = [entry for entry in all_scores if entry['score'] >= third_score]
    else:
        third_score = None if not all_scores else all_scores[-1]['score']
        expanded = all_scores[:]
    return {
        "version": 1,
        "scoring_algorithm": "simple_sum_v1",
        "all_scores": all_scores,
        "top_gifts_truncated": top_truncated,
        "top_gifts_expanded": expanded,
        "rank_meta": {"third_place_score": third_score}
    }

def score_spiritual_gifts(answers: Dict[str,int]) -> Dict:
    errors = validate_answers(answers)
    if errors:
        raise ValueError("; ".join(errors))
    return score_answers(answers)
