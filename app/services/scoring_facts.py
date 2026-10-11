"""Numbers for an assessment report, computed in code (specs/004-reliable-ai-reports, US2).

Multiple choice is graded from the questions' ``is_correct`` flags; the AI only interprets
open-ended answers and receives these facts so its narrative can't contradict them.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Optional

from app.services.report_summary import summarize_mentor_blob

WEAK_TOPIC_BELOW = 65.0
MC_WEIGHT = 0.6
OPEN_WEIGHT = 0.4

# Open-ended maturity level -> 0-10 category score
LEVEL_SCORE = {
    "flourishing": 9.5,
    "maturing": 8.0,
    "stable": 6.5,
    "developing": 5.0,
    "beginning": 3.0,
}


@dataclass
class ComputedFacts:
    biblical_knowledge_percent: float
    mc_by_category: list[dict] = field(default_factory=list)
    mc_by_topic: list[dict] = field(default_factory=list)
    weak_topics: list[str] = field(default_factory=list)
    previous_health_score: Optional[int] = None
    open_ended_count: int = 0
    health_score: Optional[int] = None  # set once the AI has returned open-ended levels
    health_band: Optional[str] = None
    # Not sent to the AI or stored: per-question grading and the open-ended items
    mc_results: list[dict] = field(default_factory=list, repr=False)
    open_items: list[dict] = field(default_factory=list, repr=False)

    def for_ai(self) -> dict:
        """What the AI sees: no health score (the formula needs its levels) and no per-question data."""
        d = self.stored()
        d.pop("health_score", None)
        d.pop("health_band", None)
        return d

    def stored(self) -> dict:
        d = asdict(self)
        d.pop("mc_results", None)
        d.pop("open_items", None)
        return d


def is_multiple_choice(question: dict) -> bool:
    return (question.get("question_type") or "").lower() in ("multiple_choice", "mc")


def _match_option(question: dict, answer) -> Optional[dict]:
    ans = str(answer or "").strip()
    for opt in question.get("options") or []:
        opt_id = str(opt.get("id") or "").strip()
        if opt_id and opt_id == ans:
            return opt
    for opt in question.get("options") or []:  # legacy drafts stored the option text
        if str(opt.get("text") or "").strip().lower() == ans.lower() and ans:
            return opt
    return None


def _percent(correct: int, total: int) -> float:
    return round(correct / total * 100.0, 1) if total else 0.0


def _rollup(results: list[dict], key: str, label: str) -> list[dict]:
    acc: dict[str, dict] = {}
    for r in results:
        row = acc.setdefault(r[key], {label: r[key], "correct": 0, "total": 0})
        row["total"] += 1
        row["correct"] += int(r["correct"])
    for row in acc.values():
        row["percent"] = _percent(row["correct"], row["total"])
    return list(acc.values())


def compute(answers: dict, questions: list[dict], previous: list[dict] | None = None) -> ComputedFacts:
    """Grade multiple choice and collect open-ended items. Answers to unknown question ids are ignored."""
    qmap = {str(q.get("id")): q for q in questions}
    mc_results, open_items = [], []
    for qid, ans in (answers or {}).items():
        q = qmap.get(str(qid))
        if not q:
            continue
        category = q.get("category") or "General Assessment"
        if is_multiple_choice(q):
            chosen = _match_option(q, ans)
            correct_opt = next((o for o in q.get("options") or [] if o.get("is_correct")), None)
            mc_results.append({
                "question_id": str(qid),
                "question": q.get("text"),
                "answer": (chosen or {}).get("text") or ans,
                "correct_answer": (correct_opt or {}).get("text"),
                "correct": bool(chosen and chosen.get("is_correct")),
                "category": category,
                "topic": q.get("topic") or category,
            })
        elif str(ans or "").strip():
            open_items.append({"question_id": str(qid), "category": category,
                               "question": q.get("text"), "answer": str(ans)})

    by_topic = _rollup(mc_results, "topic", "topic")
    previous_health = None
    for prev in previous or []:
        blob = prev.get("mentor_report_v2") or (prev.get("scores") or {}).get("mentor_blob_v2")
        if blob and "health_score" in blob:
            previous_health = summarize_mentor_blob(blob)["health_score"]
            break
    return ComputedFacts(
        biblical_knowledge_percent=_percent(sum(r["correct"] for r in mc_results), len(mc_results)),
        mc_by_category=_rollup(mc_results, "category", "category"),
        mc_by_topic=by_topic,
        weak_topics=[t["topic"] for t in by_topic if t["percent"] < WEAK_TOPIC_BELOW],
        previous_health_score=previous_health,
        open_ended_count=len(open_items),
        mc_results=mc_results,
        open_items=open_items,
    )


def category_scores(facts: ComputedFacts, levels: dict[str, str]) -> dict[str, int]:
    """0-10 per category: MC accuracy x 10 and the open-ended level, 60/40 when both exist."""
    mc = {row["category"]: row["percent"] / 10.0 for row in facts.mc_by_category}
    open_ = {cat: LEVEL_SCORE[lvl.strip().lower()] for cat, lvl in (levels or {}).items()
             if (lvl or "").strip().lower() in LEVEL_SCORE}
    out = {}
    for cat in list(mc) + [c for c in open_ if c not in mc]:
        if cat in mc and cat in open_:
            value = mc[cat] * MC_WEIGHT + open_[cat] * OPEN_WEIGHT
        else:
            value = mc.get(cat, open_.get(cat))
        out[cat] = int(round(value))
    return out


# ---------------------------------------------------------------------------
# Narrative check (US3): the AI may restate numbers from the facts but not invent them
# ---------------------------------------------------------------------------
_PERCENT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent\b)", re.I)
_POINTS = re.compile(r"\b(\d{1,3})[- ]points?\b", re.I)
# Comparisons with an earlier assessment, not advice like "to improve your prayer life"
_CHANGE = re.compile(
    r"\b(?:up from|down from|improved from|increased from|decreased from|declined from|"
    r"improvement (?:of|from)|increase (?:of|from)|decline (?:of|from)|drop (?:of|from)|"
    r"(?:has|have|had) (?:improved|increased|declined|decreased|dropped)|"
    r"since (?:your|the) (?:last|previous)|compared (?:to|with) (?:your|the) (?:last|previous))\b",
    re.I,
)


def _texts(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for v in value.values() for t in _texts(v)]
    if isinstance(value, (list, tuple)):
        return [t for v in value for t in _texts(v)]
    return []


def _allowed_numbers(facts: ComputedFacts) -> set[float]:
    values = [facts.biblical_knowledge_percent]
    values += [row["percent"] for row in facts.mc_by_category + facts.mc_by_topic]
    for score in (facts.previous_health_score, facts.health_score):
        if score is not None:
            values.append(float(score))
    allowed = set()
    for v in values:  # accept the value as given and its whole-number roundings
        allowed.update({round(float(v), 1), float(int(v)), float(round(v))})
    return allowed


def narrative_numbers_ok(report, facts: ComputedFacts) -> list[str]:
    """Problems with the numbers in an AI narrative; an empty list means it's consistent.

    Flags percentages not in ``facts``, any "N-point" change (the AI isn't given deltas), and
    change-over-time comparisons when there is no previous assessment.
    """
    allowed = _allowed_numbers(facts)
    problems = []
    for text in _texts(report):
        for m in _PERCENT.finditer(text):
            if round(float(m.group(1)), 1) not in allowed:
                problems.append(f"invented percentage '{m.group(0)}'")
        for m in _POINTS.finditer(text):
            problems.append(f"invented change '{m.group(0)}'")
        if facts.previous_health_score is None:
            for m in _CHANGE.finditer(text):
                problems.append(f"change over time without a previous assessment '{m.group(0)}'")
    return problems
