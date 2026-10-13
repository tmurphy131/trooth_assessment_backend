"""Render tests for the branded PDF reports (specs/008-pdf-redesign)."""
import json
import os
import re

import pytest
from reportlab.platypus import Paragraph

from app.core.spiritual_gifts_map import MAP
from app.data.spiritual_gift_guidance import GIFT_GUIDANCE
from app.services import pdf as kit
from app.services.spiritual_gifts_scoring import display_to_slug, score_answers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿]")


@pytest.fixture(autouse=True)
def no_silent_fallback(request, caplog):
    """A fallback PDF is still valid, so fail any test whose real render fell back (unless it expects to)."""
    yield
    if request.node.name != "test_build_pdf_falls_back_to_valid_pdf_on_failure":
        failures = [r for r in caplog.records if r.name == "app.services.pdf.layout" and "render failed" in r.getMessage()]
        assert not failures, failures[0].getMessage()


def collect_text(story) -> str:
    """Concatenate Paragraph text across a story, descending into tables, lists and groups."""
    out = []

    def walk(node):
        if node is None:
            return
        if isinstance(node, Paragraph):
            out.append(node.text)
        elif isinstance(node, (list, tuple)):
            for n in node:
                walk(n)
        else:
            for attr in ("_cellvalues", "_content", "_flowables"):
                if hasattr(node, attr):
                    walk(getattr(node, attr))
            if hasattr(node, "_flowable"):
                walk(node._flowable)

    walk(story)
    return "\n".join(out)


def assert_pdf(b: bytes):
    assert isinstance(b, (bytes, bytearray))
    assert b.startswith(b"%PDF-")
    assert b"%%EOF" in b[-1024:]


def _definitions():
    with open(os.path.join(ROOT, "scripts", "spiritual_gift_definitions_v1.json")) as f:
        return {d["gift_slug"]: d for d in json.load(f)}


def _answers(fn):
    return {f"Q{i:02d}": fn(i) for i in range(1, 73)}


# ---- Kit ----

def test_safe_escapes_and_strips_emoji():
    assert kit.safe('Prayer & fasting <daily> "now" 🎯📖✅') == "Prayer &amp; fasting &lt;daily&gt; \"now\""
    assert kit.safe(None) == ""


def test_format_date():
    assert kit.format_date("2026-10-13T22:36:48.151441Z") == "October 13, 2026"
    assert kit.format_date("not a date") is None
    assert kit.format_date(None) is None


def test_build_pdf_with_hostile_text_is_valid():
    story = lambda: [kit.para("A & B < C > D 🎯 " * 400), kit.callout("Note", ["<b>not bold</b> & co"])]
    assert_pdf(kit.build_pdf("Report", "Name & Co", "October 13, 2026", story))


def test_build_pdf_falls_back_to_valid_pdf_on_failure():
    def boom():
        raise RuntimeError("render failed")

    b = kit.build_pdf("Report", "Jordan", "October 13, 2026", boom, fallback_lines=["Line one", "Ünïcødé — 🎯"])
    assert_pdf(b)


def test_poppins_registered():
    assert kit.register_fonts().regular == "Poppins-Regular"


# ---- Spiritual Gifts ----

def test_guidance_covers_every_gift():
    assert set(GIFT_GUIDANCE) == set(MAP)
    for slug, g in GIFT_GUIDANCE.items():
        assert 2 <= len(g["scriptures"]) <= 3, slug
        assert len(g["ways_to_serve"]) >= 3 and all(len(w) <= 120 for w in g["ways_to_serve"]), slug
        assert g["reflection"].strip().endswith("?"), slug


@pytest.mark.parametrize("name,slug", [
    ("Pastor/Shepherd", "pastor-shepherd"),
    ("Pastor / Shepherd", "pastor-shepherd"),
    ("Music/Worship", "music-worship"),
    ("Tongues & Interpretation", "tongues-interpretation"),
    ("pastor_shepherd", "pastor-shepherd"),
])
def test_display_to_slug(name, slug):
    assert display_to_slug(name) == slug


def test_gifts_story_content():
    from app.services.spiritual_gifts_report import _prepare_gifts, build_gifts_story

    scores = score_answers(_answers(lambda i: (i * 7) % 5))
    defs = _definitions()
    rows = _prepare_gifts(scores, defs)["rows"]
    assert len(rows) == 24
    assert all(r["summary"] for r in rows), [r["gift"] for r in rows if not r["summary"]]

    text = collect_text(build_gifts_story("Jordan", scores, defs))
    for needle in ("YOUR TOP GIFTS", "/12", "IN SCRIPTURE", "REFLECT", "NEXT STEPS", "ALL GIFTS RANKED"):
        assert needle in text
    for r in rows:
        assert kit.safe(r["gift"]) in text
    for banned in ("Truncated", "Expanded", "Version"):
        assert banned not in text
    assert not re.search(r"\d{4}-\d{2}-\d{2}T", text)


def test_gifts_tie_at_third_gets_deep_dives():
    from app.services.spiritual_gifts_report import _prepare_gifts, build_gifts_story

    scores = {
        "all_scores": [{"gift": "Teaching", "score": 12}, {"gift": "Wisdom", "score": 11}]
        + [{"gift": g, "score": 9} for g in ("Faith", "Giving", "Helps", "Mercy")]
        + [{"gift": "Service", "score": 3}],
    }
    scores["top_gifts_truncated"] = scores["all_scores"][:3]
    scores["top_gifts_expanded"] = scores["all_scores"][:6]
    prep = _prepare_gifts(scores, _definitions())
    assert len(prep["deep_dive"]) == 6
    assert [r["gift"] for r in prep["tied_third"]] == ["Giving", "Helps", "Mercy"]
    assert "Tied for 3rd" in collect_text(build_gifts_story("Jordan", scores, _definitions()))


def test_gifts_all_zero_caps_deep_dives():
    from app.services.spiritual_gifts_report import build_gifts_story, generate_pdf

    scores = score_answers(_answers(lambda i: 0))
    text = collect_text(build_gifts_story(None, scores, _definitions()))
    assert "Also tied" in text
    assert text.count("IN SCRIPTURE") == 6
    assert_pdf(generate_pdf(None, 1, scores, _definitions()))


def test_gifts_generate_pdf_valid():
    from app.services.spiritual_gifts_report import generate_pdf

    scores = score_answers(_answers(lambda i: (i * 3) % 5))
    assert_pdf(generate_pdf("Jordan & Sam", 1, scores, _definitions(), assessment_date="2026-10-01T12:00:00Z"))


# ---- Mentor report ----

def _mentor_context(full_report=None, hostile=False):
    from app.services.master_trooth_report import build_report_context

    blob = {
        "health_score": 72,
        "health_band": "Growing",
        "biblical_knowledge": {"percent": 68, "weak_topics": ["Old Testament history"]},
        "strengths": ["Prayer & fasting <daily>" if hostile else "Prayer", "Serving others"],
        "gaps": ["Scripture memory"],
        "insights": [{"category": "Prayer", "level": "Developing", "observation": "Crisis prayer 🎯" if hostile else "Crisis prayer", "next_step": "Set a rhythm"}],
        "priority_action": {"title": "Pray daily", "steps": ["Use ACTS"], "scripture": "Philippians 4:6"},
        "conversation_starters": ["Share an answered prayer"],
    }
    ctx = build_report_context({"apprentice": {"name": "Jordan"}, "created_at": "2026-10-01T12:00:00Z"}, {"overall_score": 7, "category_scores": {"Prayer": 8}}, blob)
    if full_report:
        ctx["full_report"] = full_report
    return ctx


PREMIUM = {
    "executive_summary": {"one_liner": "Growing in prayer.", "trajectory_note": "x " * 3000},
    "strengths_deep_dive": [{"area": "Service", "summary": "Reliable."}],
    "gaps_deep_dive": [{"area": "Scripture", "summary": "Sporadic.", "biblical_perspective": "Psalm 1:2"}],
    "conversation_guide": {"session_1_opening": {"theme": "Listening", "questions_to_ask": ["How are you?"]}},
    "biblical_knowledge_analysis": {"overall_percent": 68, "by_topic_breakdown": [{"topic": "Gospels", "score_percent": 80}]},
    "spiritual_formation_insights": [{"area": "Prayer", "current_level": "Developing", "detailed_observation": "Crisis prayer."}],
    "progress_tracking": {"suggested_reassessment": "3 months"},
    "mentor_preparation_notes": {"prayer_focus_for_this_apprentice": "Rest"},
    "personalized_resources": [{"title": "Praying the Bible", "author": "Donald Whitney"}],
}


def test_mentor_pdf_basic_and_legacy_blob():
    from app.services.master_trooth_report import build_report_context, render_pdf_v2

    assert_pdf(render_pdf_v2(_mentor_context()))
    legacy = build_report_context({"apprentice": {"name": "Test"}}, {"overall_score": 8, "category_scores": {"A": 8}}, {
        "snapshot": {"overall_mc_percent": 75.5, "knowledge_band": "Average", "top_strengths": ["Prayer"], "top_gaps": ["Sabbath"]},
        "biblical_knowledge": {"topic_breakdown": [{"topic": "Gospels", "correct": 3, "total": 5}]},
        "open_ended_insights": [{"category": "Prayer", "level": "Developing", "evidence": "2-3x/week", "mentor_moves": ["Set rhythm"]}],
        "four_week_plan": {"rhythm": ["Daily prayer"], "checkpoints": ["Week 2"]},
        "recommended_resources": [{"title": "Prayer Basics", "why": "Foundations", "type": "Book"}],
    })
    assert_pdf(render_pdf_v2(legacy))


def test_mentor_pdf_premium_sections_present():
    from app.services.master_trooth_report import build_mentor_story, render_pdf_v2

    ctx = _mentor_context(PREMIUM)
    text = collect_text(build_mentor_story(ctx))
    for title in ("Executive summary", "Strengths deep dive", "Growth areas deep dive", "Mentor conversation guide",
                  "Biblical knowledge analysis", "Spiritual formation insights", "PROGRESS TRACKING",
                  "MENTOR PREPARATION NOTES", "PERSONALIZED RESOURCES"):
        assert title in text, title
    assert_pdf(render_pdf_v2(ctx))


def test_mentor_pdf_hostile_text():
    from app.services.master_trooth_report import build_mentor_story, render_pdf_v2

    ctx = _mentor_context(hostile=True)
    text = collect_text(build_mentor_story(ctx))
    assert "&amp;" in text and "&lt;daily&gt;" in text
    assert not EMOJI.search(text)
    assert_pdf(render_pdf_v2(ctx))


# ---- Generic ----

def test_generic_story_and_pdf():
    from app.services.generic_assessment_report import build_generic_story, generate_pdf

    scores = {"overall_score": 7, "categories": [{"name": "Prayer", "score": 8}, {"name": "Scripture & Study", "score": 6}]}
    text = collect_text(build_generic_story("Sample", scores))
    assert "7/10" in text and "Prayer" in text and "8/10" in text and "Scripture &amp; Study" in text
    assert_pdf(generate_pdf("Sample", "Jordan", scores))
    assert_pdf(generate_pdf("Sample", None, {"category_scores": {"A": 5}}))


def test_master_legacy_generate_pdf_is_branded_pdf():
    from app.services.master_trooth_report import generate_pdf

    assert_pdf(generate_pdf("Jordan", {"overall_score": 7, "category_scores": {"Prayer": 8}}))
