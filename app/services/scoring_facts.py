"""Numbers for an assessment report, computed in code (specs/004-reliable-ai-reports, US2).

Multiple choice is graded from the questions' ``is_correct`` flags; the AI only interprets
open-ended answers and receives these facts so its narrative can't contradict them.
"""
from __future__ import annotations

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
