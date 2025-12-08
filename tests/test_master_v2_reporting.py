import asyncio
import types


async def _score_with(answers, questions):
    from app.services.ai_scoring import score_assessment_by_category
    return await score_assessment_by_category(answers, questions)


def test_overall_rounding_and_question_ids():
    answers = {"Q1": "short", "Q2": "a bit longer answer words here"}
    questions = [
        {"id": "Q1", "text": "Q1?", "category": "A"},
        {"id": "Q2", "text": "Q2?", "category": "B"},
    ]
    result = asyncio.get_event_loop().run_until_complete(_score_with(answers, questions))
    cats = result.get("category_scores", {})
    # overall should equal round(mean(category_scores))
    if cats:
        from statistics import mean
        assert result["overall_score"] == int(round(mean(cats.values())))
    # question_feedback items should echo question_id
    fbs = result.get("question_feedback", [])
    assert all([fb.get("question_id") for fb in fbs])


def test_templates_render_with_mock_blob():
    from app.services.master_trooth_report import build_report_context, render_email_v2, render_pdf_v2
    scores = {"overall_score": 8, "category_scores": {"A": 8, "B": 7}}
    mentor_blob = {
        "snapshot": {"overall_mc_percent": 75.5, "knowledge_band": "Average", "top_strengths": ["Prayer"], "top_gaps": ["Sabbath"]},
        "biblical_knowledge": {"summary": "", "topic_breakdown": [{"topic": "Gospels", "correct": 3, "total": 5, "note": ""}]},
        "open_ended_insights": [
            {"category": "Prayer", "level": "Developing", "evidence": "prays 2-3x/week", "discernment": "growing", "scripture_anchor": "Phil 4:6", "mentor_moves": ["Set rhythm", "Model prayer"]}
        ],
        "flags": {"red": [], "yellow": [], "green": ["Consistent attendance"]},
        "four_week_plan": {"rhythm": ["Daily prayer"], "checkpoints": ["Week 2 check-in"]},
        "conversation_starters": ["Share a recent answered prayer"],
        "recommended_resources": [{"title": "Prayer Basics", "why": "Foundations", "type": "Book"}],
    }
    context = build_report_context({"apprentice": {"name": "Test"}}, scores, mentor_blob)
    html = render_email_v2(context)
    assert "T[root]H Mentor Report" in html or "Mentor Report" in html
    assert "Biblical Knowledge" in html
    pdf = render_pdf_v2(context)
    assert isinstance(pdf, (bytes, bytearray)) and len(pdf) > 10


def test_llm_invalid_json_fallback(monkeypatch):
    from app.services import ai_scoring

    class _Msg:
        def __init__(self, content):
            self.content = content

    class _Resp:
        def __init__(self, content):
            self.choices = [types.SimpleNamespace(message=_Msg(content))]

    class _FakeClient:
        def __init__(self):
            self._count = 0
            self.chat = types.SimpleNamespace(completions=self)
        def create(self, *args, **kwargs):
            self._count += 1
            # Always return invalid json to force fallback
            return _Resp("not json")

    # Force non-mock path
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setattr(ai_scoring, "get_openai_client", lambda: _FakeClient())

    answers = {"Q1": "Yes"}
    questions = [{"id": "Q1", "text": "Q1?", "category": "A", "question_type": "multiple_choice", "options": [{"text": "Yes", "is_correct": True}]}]
    result = asyncio.get_event_loop().run_until_complete(_score_with(answers, questions))
    blob = result.get("mentor_blob_v2") or {}
    assert blob.get("snapshot") is not None
    assert isinstance(blob.get("biblical_knowledge", {}).get("topic_breakdown"), list)
