"""Write sample report PDFs for visual review (specs/008-pdf-redesign quickstart).

Usage: python scripts/render_pdf_samples.py --out /tmp/pdf-samples
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.services.generic_assessment_report import generate_pdf as generic_pdf  # noqa: E402
from app.services.master_trooth_report import build_report_context, render_pdf_v2  # noqa: E402
from app.services.spiritual_gifts_report import generate_pdf as gifts_pdf  # noqa: E402
from app.services.spiritual_gifts_scoring import score_answers  # noqa: E402

DATE = "2026-10-01T14:00:00Z"

BLOB = {
    "health_score": 72,
    "health_band": "Growing",
    "biblical_knowledge": {"percent": 68, "weak_topics": ["Old Testament history", "Prophets"]},
    "strengths": ["Consistent prayer", "Serving others"],
    "gaps": ["Scripture memory", "Sabbath rest"],
    "insights": [{"category": "Prayer", "level": "Developing", "observation": "Prays 2-3 times a week, mostly in crisis.", "next_step": "Set a daily rhythm"}],
    "priority_action": {"title": "Start a 10-minute morning prayer", "steps": ["Use ACTS each morning", "Text your mentor on Fridays"], "scripture": "Philippians 4:6"},
    "conversation_starters": ["Share a recent answered prayer", "What does rest look like for you?"],
}

PREMIUM = {
    "executive_summary": {"one_liner": "A faithful servant growing in prayer and Scripture.", "trajectory_note": "Over the last quarter Jordan has shown steady growth in service and a new hunger for prayer."},
    "strengths_deep_dive": [{"area": "Service", "summary": "Shows up reliably and notices needs.", "how_to_leverage": "Invite Jordan to co-lead the welcome team."}],
    "gaps_deep_dive": [{"area": "Scripture", "summary": "Reads sporadically.", "biblical_perspective": "Psalm 1:2 - delight in the law of the Lord.", "growth_pathway": {"phase_1_weeks_1_4": {"goal": "Read 5 days a week"}}}],
    "conversation_guide": {"session_1_opening": {"theme": "Listening", "duration_minutes": 45, "key_points_to_cover": [{"point": "Affirm growth", "talking_point": "I see God at work in you."}], "questions_to_ask": ["How is your prayer life?", "Where do you feel stuck?"]}},
    "biblical_knowledge_analysis": {"overall_percent": 68, "mastery_level": "Developing", "by_topic_breakdown": [{"topic": "Gospels", "score_percent": 80, "level": "Strong"}, {"topic": "OT History", "score_percent": 35, "key_gaps": ["Kings", "Exile"], "study_prescription": "Read 1 Kings"}], "recommended_bible_reading_plan": {"name": "Gospels in 30 days", "description": "One chapter a day", "why_this_plan": "Builds a daily habit"}},
    "spiritual_formation_insights": [{"area": "Prayer", "current_level": "Developing", "detailed_observation": "Mostly crisis prayer.", "maturity_markers_present": ["Honesty"], "maturity_markers_missing": ["Consistency"], "custom_development_plan": {"immediate_30_days": "Daily 10 minutes", "quarter_goal": "Keep a prayer journal"}, "mentor_discussion_questions": ["When do you pray best?"]}],
    "progress_tracking": {"previous_assessment_comparison": {"score_change": "+6", "trend": "improving", "areas_improved": ["Service"]}, "milestones_to_track": [{"milestone": "30-day prayer streak", "expected_by": "November"}], "suggested_reassessment": "In 3 months"},
    "mentor_preparation_notes": {"handle_with_care": "Recent loss in the family", "watch_for": "Burnout from over-serving", "prayer_focus_for_this_apprentice": "Peace and rest"},
    "personalized_resources": [{"title": "Praying the Bible", "author": "Donald Whitney", "type": "Book", "why_specifically_for_them": "A simple method for daily prayer", "how_to_use": "One chapter a week together"}],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/pdf-samples")
    out = parser.parse_args().out
    os.makedirs(out, exist_ok=True)

    with open(os.path.join(ROOT, "scripts", "spiritual_gift_definitions_v1.json")) as f:
        defs = {d["gift_slug"]: d for d in json.load(f)}
    rnd = random.Random(3)
    samples = {
        "gifts_typical.pdf": gifts_pdf("Jordan Smith", 1, score_answers({f"Q{i:02d}": rnd.randint(0, 4) for i in range(1, 73)}), defs, assessment_date=DATE),
        "gifts_tie.pdf": gifts_pdf("Jordan Smith", 1, score_answers({f"Q{i:02d}": (4 if i <= 12 else 2) for i in range(1, 73)}), defs, assessment_date=DATE),
        "gifts_all_zero.pdf": gifts_pdf(None, 1, score_answers({f"Q{i:02d}": 0 for i in range(1, 73)}), defs),
    }
    assessment = {"apprentice": {"name": "Jordan Smith"}, "created_at": DATE}
    scores = {"overall_score": 7, "category_scores": {"Prayer": 8, "Scripture": 5, "Community": 3, "Service": 9}}
    samples["mentor_basic.pdf"] = render_pdf_v2(build_report_context(assessment, scores, BLOB))
    premium = build_report_context(assessment, scores, BLOB)
    premium["full_report"] = PREMIUM
    samples["mentor_premium.pdf"] = render_pdf_v2(premium)
    hostile = dict(BLOB, strengths=["Prayer & fasting <daily>", "Serving 🎯 others"])
    samples["mentor_hostile.pdf"] = render_pdf_v2(build_report_context(assessment, scores, hostile))
    samples["generic.pdf"] = generic_pdf("Spiritual Disciplines Check-in", "Jordan Smith", {
        "overall_score": 7,
        "summary_recommendation": "Strong rhythms of service; build consistency in Scripture.",
        "categories": [{"name": "Prayer", "score": 8}, {"name": "Scripture", "score": 5}, {"name": "Rest", "score": 3}],
    }, assessment_date=DATE)

    for name, data in samples.items():
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)
        print(f"{name}: {len(data):,} bytes")


if __name__ == "__main__":
    main()
