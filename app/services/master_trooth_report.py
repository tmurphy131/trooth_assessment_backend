"""Master Trooth report generation utilities (PDF/HTML) for v2 mentor report.

Adds a builder that maps mentor_blob_v2 + classic scores into the new email/print templates.
Falls back to simple HTML/PDF if templates are unavailable.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime
import logging
import os
from typing import Any
from app.core.settings import settings
from app.services import pdf as kit
from app.services.pdf import theme as t
from app.services.report_summary import public_full_report, summarize_mentor_blob

logger = logging.getLogger("app.master_report")

def generate_pdf(apprentice_name: Optional[str], scores: Dict) -> bytes:
    """Master assessment PDF when there is no mentor-report data: the branded generic summary."""
    from app.services.generic_assessment_report import generate_pdf as generic_pdf

    return generic_pdf("Master T[root]H Assessment", apprentice_name, scores or {})


def generate_html(apprentice_name: Optional[str], scores: Dict) -> str:
    from html import escape

    version = escape(str(scores.get('version', 'master_v1')))
    overall = escape(str(scores.get('overall_score', 7)))
    cat_scores = scores.get('category_scores') or {}
    top3 = scores.get('top3') or []
    lines = []
    lines.append("<h1>Master T[root]H Discipleship Report</h1>")
    lines.append(f"<p>Apprentice: {escape(apprentice_name or 'Apprentice')}</p>")
    lines.append(f"<p>Version: {version} • Overall: {overall}</p>")
    lines.append("<h3>Top Categories</h3>")
    lines.append("<ul>" + "".join([f"<li>{escape(str(i.get('category')))}: {escape(str(i.get('score')))}</li>" for i in top3]) + "</ul>")
    lines.append("<h3>All Categories</h3>")
    lines.append("<ul>" + "".join([f"<li>{escape(str(k))}: {escape(str(v))}</li>" for k, v in cat_scores.items()]) + "</ul>")
    return "\n".join(lines)


# ------------------------- v2 report rendering -------------------------

def build_report_context(assessment: Dict[str, Any] | None, scores: Dict, mentor_blob: Dict) -> Dict[str, Any]:
    """Map stored structures into template-ready context.

    Supports both v2.0 (snapshot-based) and v2.1 (health_score-based) mentor_blob formats.
    """
    apprentice_name = None
    submitted_date = None
    template_version = None
    try:
        if assessment:
            apprentice_name = (assessment.get('apprentice') or {}).get('name') or None
            submitted_date = assessment.get('created_at') or assessment.get('submitted_at')
            template_version = (assessment.get('template') or {}).get('name') or (assessment.get('template_id') or 'Master v2')
    except Exception:
        pass

    # Detect v2.1 format (has health_score at top level) vs v2.0 (has snapshot)
    is_v21 = 'health_score' in mentor_blob
    
    if is_v21:
        # v2.1 format from ai_prompt_master_assessment_v2_optimized.txt
        overall_mc_percent = mentor_blob.get('biblical_knowledge', {}).get('percent', 0)
        knowledge_band = mentor_blob.get('health_band', '')
        top_strengths = mentor_blob.get('strengths', [])
        top_gaps = mentor_blob.get('gaps', [])
        
        # Map v2.1 insights to open_insights format for template compatibility
        # Note: v2.1 uses 'observation' field instead of 'evidence'
        open_insights = []
        for ins in mentor_blob.get('insights', []):
            obs = ins.get('observation', ins.get('evidence', ''))  # Try observation first, fall back to evidence
            open_insights.append({
                'category': ins.get('category', ''),
                'level': ins.get('level', '-'),
                'evidence': obs,
                'discernment': obs,
                'scripture_anchor': '',  # v2.1 doesn't have this per-insight
                'mentor_moves': [ins.get('next_step', '')] if ins.get('next_step') else []
            })
        
        # v2.1 biblical_knowledge has percent and weak_topics, not topic_breakdown
        knowledge_topics = []
        for topic in mentor_blob.get('biblical_knowledge', {}).get('weak_topics', []):
            knowledge_topics.append({
                'topic': topic,
                'correct': 0,
                'total': 0,
                'percent': 0,
                'note': 'Needs improvement'
            })
        
        # Priority action from v2.1 format
        pa = mentor_blob.get('priority_action')
        priority_action = None
        if pa:
            priority_action = {
                'title': pa.get('title', ''),
                'description': (pa.get('steps') or [''])[0] if pa.get('steps') else '',
                'steps': pa.get('steps', []),
                'scripture': pa.get('scripture', '')
            }
        
        flags = mentor_blob.get('flags', {'red': [], 'yellow': [], 'green': []})
        # v2.1 doesn't have four_week_plan, create empty one
        four_week = {'rhythm': [], 'checkpoints': []}
        starters = mentor_blob.get('conversation_starters', [])
        resources = mentor_blob.get('recommended_resources', [])
        
        overall_open_level = knowledge_band  # Use health_band as overall level
        mc_total = None
        mc_correct = None
        
    else:
        # v2.0 format (legacy)
        snapshot = mentor_blob.get('snapshot') or {}
        overall_mc_percent = snapshot.get('overall_mc_percent') or 0
        knowledge_band = snapshot.get('knowledge_band') or ''
        top_strengths = snapshot.get('top_strengths') or []
        top_gaps = snapshot.get('top_gaps') or []

        knowledge = mentor_blob.get('biblical_knowledge') or {}
        knowledge_topics = []
        for t in knowledge.get('topic_breakdown', []) or []:
            try:
                correct = int(t.get('correct', 0))
                total = int(t.get('total', 0))
                percent = round((correct / total * 100.0), 1) if total else 0.0
            except Exception:
                correct, total, percent = 0, 0, 0.0
            knowledge_topics.append({
                'topic': t.get('topic'),
                'correct': correct,
                'total': total,
                'percent': percent,
                'note': t.get('note') or ''
            })

        open_insights = mentor_blob.get('open_ended_insights') or []
        flags = mentor_blob.get('flags') or {'red': [], 'yellow': [], 'green': []}
        four_week = mentor_blob.get('four_week_plan') or {'rhythm': [], 'checkpoints': []}
        starters = mentor_blob.get('conversation_starters') or []
        resources = mentor_blob.get('recommended_resources') or []

        overall_open_level = '-'
        levels = [i.get('level') for i in open_insights if i.get('level')]
        if levels:
            from collections import Counter
            overall_open_level = Counter(levels).most_common(1)[0][0]

        # Derive MC totals/correct from mentor_blob if present
        mc_total = None
        mc_correct = None
        try:
            mc_total = (mentor_blob.get('biblical_knowledge') or {}).get('total_questions')
            mc_correct = (mentor_blob.get('biblical_knowledge') or {}).get('correct_count')
            if mc_total is None or mc_correct is None:
                mc_total = sum([int(t.get('total', 0)) for t in knowledge_topics])
                mc_correct = sum([int(t.get('correct', 0)) for t in knowledge_topics])
        except Exception:
            pass
        
        # Extract priority action from open_ended_insights (first with mentor_moves)
        priority_action = None
        for insight in open_insights:
            if insight.get('mentor_moves'):
                priority_action = {
                    'title': f"Focus on {insight.get('category', 'growth')}",
                    'description': insight.get('mentor_moves', [])[0] if insight.get('mentor_moves') else '',
                    'steps': insight.get('mentor_moves', []),
                    'scripture': insight.get('scripture_anchor', '')
                }
                break

    # Category Scores: map from classic category_scores to rows with levels if available
    cat_scores = scores.get('category_scores') or {}
    categories = []
    for name, val in cat_scores.items():
        level = None
        # try to infer from open_insights entries
        for ins in open_insights:
            if str(ins.get('category')).lower() == str(name).lower():
                level = ins.get('level')
                break
        categories.append({
            'name': name,
            'score': int(val),
            'score_percent': max(0, min(100, int(round((int(val) / 10.0) * 100)))),
            'level': level or '-',
        })

    # Calculate trend notes from historical data (Phase 2)
    trend_note = None
    try:
        if assessment and assessment.get('previous_assessment_id'):
            hist_summary = assessment.get('historical_summary') or {}
            if hist_summary.get('trend'):
                trend_note = hist_summary['trend']
            else:
                prev_score = hist_summary.get('previous_overall_score')
                curr_score = scores.get('overall_score')
                if prev_score is not None and curr_score is not None:
                    diff = curr_score - prev_score
                    if diff > 5:
                        trend_note = f"📈 Significant improvement (+{diff} points)"
                    elif diff > 0:
                        trend_note = f"📈 Steady growth (+{diff} points)"
                    elif diff == 0:
                        trend_note = "➡️ Consistent performance"
                    elif diff > -5:
                        trend_note = f"📉 Slight decline ({diff} points)"
                    else:
                        trend_note = f"📉 Needs attention ({diff} points)"
    except Exception as e:
        logger.warning(f"Failed to calculate trend: {e}")

    # Include full_report_v1 from scores if available (for premium PDF), aligned to the canonical scores
    full_report = public_full_report(scores.get('full_report_v1'), mentor_blob)
    summary = summarize_mentor_blob(mentor_blob)

    ctx = {
        'apprentice_name': apprentice_name or 'Apprentice',
        'submitted_date': submitted_date or '',
        'template_version': template_version or 'Master v2',
        'overall_score': scores.get('overall_score', 7),
        'category_scores': cat_scores,
        'top3': scores.get('top3', []),
        'version': scores.get('version', 'master_v1'),
        'summary_recommendation': scores.get('summary_recommendation', ''),
        'overall_mc_percent': overall_mc_percent,
        'knowledge_band': knowledge_band,
        'health_score': summary['health_score'],
        'health_band': summary['health_band'],
        'overall_level': scores.get('overall_score', 7),
        'overall_open_level': overall_open_level,
        'categories': categories,
        'top_strengths': top_strengths,
        'top_gaps': top_gaps,
        'mc': {
            'total_questions': mc_total,
            'correct_count': mc_correct,
        },
        'knowledge_topics': knowledge_topics,
        'open_insights': open_insights,
        'flags': flags,
        'four_week': four_week,
        'starters': starters,
        'resources': resources,
        'mentor_blob_v2': mentor_blob,  # Pass entire blob for template access
        'full_report': full_report,  # Premium full report data (if available)
        'priority_action': priority_action,
        'trend_note': trend_note,
        'app_url': getattr(settings, 'ios_app_store_url', settings.app_url),  # Use App Store URL for mobile app link
    }
    return ctx


def render_email_v2(context: Dict[str, Any]) -> str:
    """Mentor report email HTML (also served by the HTML preview route). Uses the shared report
    email so the preview, the email and the app show the same numbers (specs/005-email-redesign)."""
    from app.services.email import render_mentor_report_v2_email

    html, _ = render_mentor_report_v2_email(context)
    return html

def render_markdown_print_v2(context: Dict[str, Any]) -> str:
    try:
        from jinja2 import Environment, FileSystemLoader
    except Exception:
        # very small fallback
        return f"# T[root]H Mentor Report\n\nApprentice: {context.get('apprentice_name')}\n"
    # Search both app/templates/print and backend root where v2 print template may live
    print_dir = os.path.join(os.path.dirname(__file__), '../templates/print')
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    env = Environment(loader=FileSystemLoader([os.path.abspath(print_dir), backend_root]))
    try:
        template = env.get_template('mentor_report_print_template.md')
        return template.render(**context)
    except Exception as e:
        logger.error(f"Failed to render mentor_report_print_template.md: {e}")
        return f"# T[root]H Mentor Report\n\nApprentice: {context.get('apprentice_name')}\n"


def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _items(value, limit: int | None = None) -> list:
    """List of non-empty strings from a list (dict items use their first text-like field)."""
    out = []
    for v in value or []:
        if isinstance(v, dict):
            v = v.get("point") or v.get("title") or v.get("text") or v.get("area") or ""
        v = _text(v)
        if v:
            out.append(v)
    return out[:limit] if limit else out


def _premium_sections(full_report: Dict[str, Any]) -> list:
    """Premium analysis (executive summary through spiritual formation), same data as before 008."""
    story: list = []
    story += kit.section_heading("Premium detailed analysis")

    exec_summary = full_report.get("executive_summary") or {}
    if exec_summary:
        story.append(kit.subheading("Executive summary"))
        if exec_summary.get("one_liner"):
            story.append(kit.para(exec_summary["one_liner"], "lead"))
        if exec_summary.get("trajectory_note"):
            story.append(kit.para(exec_summary["trajectory_note"]))
        story.append(kit.gap(6))

    strengths_deep = full_report.get("strengths_deep_dive") or []
    if strengths_deep:
        for i, s in enumerate(strengths_deep[:3]):
            block = ([kit.subheading("Strengths deep dive")] if i == 0 else []) + [kit.para(s.get("area"), "row")]
            if s.get("summary"):
                block.append(kit.para(s["summary"]))
            if s.get("how_to_leverage"):
                block.append(kit.label_value("How to leverage", s["how_to_leverage"]))
            story += [kit.KeepTogether(block), kit.gap(6)]

    gaps_deep = full_report.get("gaps_deep_dive") or []
    if gaps_deep:
        for i, g in enumerate(gaps_deep[:3]):
            block = ([kit.subheading("Growth areas deep dive")] if i == 0 else []) + [kit.para(g.get("area"), "row")]
            if g.get("summary"):
                block.append(kit.para(g["summary"]))
            if g.get("biblical_perspective"):
                block.append(kit.callout("Biblical perspective", g["biblical_perspective"]))
            goal = ((g.get("growth_pathway") or {}).get("phase_1_weeks_1_4") or {}).get("goal")
            if goal:
                block += [kit.gap(4), kit.label_value("Weeks 1-4 goal", goal)]
            story += [kit.KeepTogether(block), kit.gap(8)]

    conv_guide = full_report.get("conversation_guide") or {}
    if conv_guide:
        guide_heading = [kit.subheading("Mentor conversation guide")]
        sessions = [
            ("session_1_opening", "Session 1: Opening"),
            ("session_2_growth_areas", "Session 2: Growth areas"),
            ("session_3_check_in", "Session 3: Check-in"),
        ]
        has_ai_sessions = False
        for key, title in sessions:
            session = conv_guide.get(key) or {}
            if not session:
                continue
            has_ai_sessions = True
            header = title
            if session.get("theme"):
                header += f" - {_text(session['theme'])}"
            if session.get("duration_minutes"):
                header += f" ({_text(session['duration_minutes'])} min)"
            block = guide_heading + [kit.para(header, "row"), kit.gap(2)]
            guide_heading = []
            points = []
            for kp in (session.get("key_points_to_cover") or [])[:3]:
                point = kp.get("point", "") if isinstance(kp, dict) else _text(kp)
                talking = kp.get("talking_point", "") if isinstance(kp, dict) else ""
                if point:
                    points.append(f"<b>{kit.safe(point)}</b>" + (f"<br/>“{kit.safe(talking)}”" if talking else ""))
            if points:
                block.append(kit.bullets(points, markup=True))
            questions = _items(session.get("questions_to_ask"), 3)
            if questions:
                block.append(kit.callout("Questions to ask", questions))
            story += [kit.KeepTogether(block), kit.gap(8)]
        if not has_ai_sessions:
            story += guide_heading
            opening = _items(conv_guide.get("opening_questions"), 3)
            if opening:
                story += [kit.para("Opening questions", "row"), kit.bullets(opening)]
            for i, sess in enumerate((conv_guide.get("sessions") or [])[:3], 1):
                if sess.get("focus"):
                    story.append(kit.label_value(f"Session {i}", sess["focus"]))
                    if sess.get("goal"):
                        story.append(kit.para(f"Goal: {_text(sess['goal'])}", "small"))
            story.append(kit.gap(6))

    bk = full_report.get("biblical_knowledge_analysis") or {}
    if bk:
        story.append(kit.subheading("Biblical knowledge analysis"))
        overall_percent = bk.get("overall_percent")
        mastery = _text(bk.get("mastery_level"))
        if overall_percent or mastery:
            parts = [f"{_text(overall_percent)}%" if overall_percent else "", mastery]
            story.append(kit.para(" - ".join(p for p in parts if p), "row"))
        if bk.get("summary"):
            story.append(kit.para(bk["summary"]))
        topics = (bk.get("by_topic_breakdown") or bk.get("topics") or [])[:6]
        if topics:
            rows = []
            for topic in topics:
                pct = _num(topic.get("score_percent") or topic.get("percent") or topic.get("score"))
                note_parts = [_text(topic.get("level"))]
                if topic.get("affirmation"):
                    note_parts.append(f"Strength: {_text(topic['affirmation'])}")
                if topic.get("key_gaps"):
                    note_parts.append("Gaps: " + ", ".join(_items(topic["key_gaps"], 3)))
                if topic.get("study_prescription"):
                    note_parts.append(f"Study: {_text(topic['study_prescription'])}")
                rows.append({
                    "label": topic.get("topic") or topic.get("name"),
                    "value": pct,
                    "value_label": f"{int(pct)}%",
                    "note": "  ·  ".join(p for p in note_parts if p),
                    "fill": t.status_color(pct / 100.0),
                })
            story += [kit.gap(4), kit.score_table(rows, 100, suffix="%")]
        theological = bk.get("theological_health_check") or {}
        if theological:
            lines = []
            if theological.get("core_doctrines_solid"):
                lines.append(f"<b>Solid:</b> {kit.safe(', '.join(_items(theological['core_doctrines_solid'])))}")
            if theological.get("areas_needing_clarification"):
                lines.append(f"<b>Needs clarification:</b> {kit.safe(', '.join(_items(theological['areas_needing_clarification'])))}")
            if theological.get("potential_concerns"):
                lines.append(f"<b>Concerns:</b> {kit.safe(', '.join(_items(theological['potential_concerns'])))}")
            if lines:
                story += [kit.gap(6), kit.para("Theological health check", "row"), kit.bullets(lines, markup=True)]
        plan = bk.get("recommended_bible_reading_plan") or {}
        if plan:
            body = [f"<b>{kit.safe(plan.get('name') or 'Bible reading plan')}</b>"]
            if plan.get("description"):
                body.append(kit.safe(plan["description"]))
            if plan.get("why_this_plan"):
                body.append(f"Why: {kit.safe(plan['why_this_plan'])}")
            story += [kit.gap(6), kit.callout("Recommended reading plan", body, markup=True)]
        story.append(kit.gap(8))

    sf = full_report.get("spiritual_formation_insights") or []
    if sf:
        for i, insight in enumerate(sf[:5]):
            area = _text(insight.get("area") or insight.get("category"))
            level = _text(insight.get("current_level") or insight.get("level"))
            observation = insight.get("detailed_observation") or insight.get("summary") or insight.get("observation") or insight.get("insight")
            block = ([kit.subheading("Spiritual formation insights")] if i == 0 else []) + [_level_heading(area, level)]
            if observation:
                block.append(kit.para(observation))
            markers = []
            if insight.get("maturity_markers_present"):
                markers.append(f"<b>Present:</b> {kit.safe(', '.join(_items(insight['maturity_markers_present'], 4)))}")
            if insight.get("maturity_markers_missing"):
                markers.append(f"<b>Missing:</b> {kit.safe(', '.join(_items(insight['maturity_markers_missing'], 4)))}")
            if markers:
                block.append(kit.bullets(markers, markup=True))
            plan = insight.get("custom_development_plan") or {}
            plan_lines = [
                f"<b>{label}:</b> {kit.safe(plan[key])}"
                for key, label in (("immediate_30_days", "30 days"), ("quarter_goal", "Quarter"), ("year_vision", "Year"))
                if plan.get(key)
            ]
            if plan_lines:
                block.append(kit.callout("Development plan", plan_lines, markup=True))
            questions = _items(insight.get("mentor_discussion_questions"), 3)
            if questions:
                block += [kit.gap(4), kit.para("Questions to ask", "label"), kit.bullets(questions)]
            else:
                recs = _items(insight.get("recommendations") or insight.get("mentor_moves"), 2)
                if recs:
                    block.append(kit.bullets(recs))
            story += [kit.KeepTogether(block), kit.gap(10)]
    return story


def _level_heading(title: str, level: str):
    """'Title  Level' with the level in its muted status color."""
    markup = kit.safe(title)
    if level:
        markup += f"  <font color='{t.hex_of(t.status_color(level))}' size='9.5'>{kit.safe(level)}</font>"
    return kit.subheading(markup, markup=True)


def build_mentor_story(context: Dict[str, Any]) -> list:
    """Mentor / Master report sections with the same data as before 008 (priority action moved up, as in the emails)."""
    story: list = []

    # Headline: matches the report emails and the app (canonical summary, specs/005)
    health_score = context.get("health_score")
    band = _text(context.get("health_band") or context.get("knowledge_band"))
    mc_percent = _num(context.get("overall_mc_percent"))
    if health_score is not None:
        sub = band
        if mc_percent:
            sub = f"{band}  ·  Biblical Knowledge {mc_percent:.0f}%" if band else f"Biblical Knowledge {mc_percent:.0f}%"
        story.append(kit.stat_card(_text(health_score), "Health Score", sub))
    else:
        story.append(kit.stat_card(f"{mc_percent:.0f}%", "Biblical Knowledge", band))
    trend = _text(context.get("trend_note"))
    if trend:
        story += [kit.gap(4), kit.para(trend, "small")]
    story.append(kit.gap(12))

    strengths = _items(context.get("top_strengths"), 3)
    gaps = _items(context.get("top_gaps"), 3)
    if strengths or gaps:
        story += [kit.two_col_cards("Top strengths", strengths, "Growth areas", gaps), kit.gap(4)]

    # Priority action is the first thing a mentor acts on
    pa = context.get("priority_action") or {}
    if pa and (pa.get("title") or pa.get("description")):
        body = []
        if pa.get("title"):
            body.append(f"<b>{kit.safe(pa['title'])}</b>")
        steps = _items(pa.get("steps"), 3)
        if pa.get("description") and _text(pa["description"]) not in steps:
            body.append(kit.safe(pa["description"]))
        body += [f"\u2022 {kit.safe(s)}" for s in steps]
        if pa.get("scripture"):
            body.append(f"<font color='{t.hex_of(t.GOLD_DEEP)}'>{kit.safe(pa['scripture'])}</font>")
        story += kit.section_heading("Priority action this week")
        story.append(kit.callout(None, body, markup=True))

    categories = context.get("categories") or []
    if categories:
        story += kit.section_heading("Category scores")
        story.append(kit.score_table([
            {
                "label": c.get("name"),
                "value": c.get("score", 0),
                "note": c.get("level") if c.get("level") not in (None, "", "-") else None,
                "fill": t.status_color(_num(c.get("score")) / 10.0),
            }
            for c in categories
        ], 10))

    topics = context.get("knowledge_topics") or []
    scored = [tp for tp in topics if _num(tp.get("total"))]
    to_study = [_text(tp.get("topic")) for tp in topics if not _num(tp.get("total")) and tp.get("topic")]
    if scored or to_study:
        story += kit.section_heading("Biblical knowledge breakdown")
    if scored:
        rows = []
        for topic in scored:
            pct = _num(topic.get("percent"))
            status = "Strong" if pct >= 70 else "Developing" if pct >= 40 else "Needs focus"
            note = _text(topic.get("note"))
            rows.append({
                "label": topic.get("topic"),
                "value": pct,
                "value_label": f"{pct:.0f}%",
                "note": f"{status}  ·  {note}" if note and note != status else status,
                "fill": t.status_color(pct / 100.0),
            })
        story.append(kit.score_table(rows, 100, suffix="%"))
    if to_study:
        # v2.1 reports list weak topics without per-topic scores
        story += [kit.gap(4), kit.callout("Topics to study", ", ".join(to_study))]

    insights = context.get("open_insights") or []
    if insights:
        story += kit.section_heading("Spiritual life insights")
        for insight in insights[:5]:
            block = [_level_heading(_text(insight.get("category")), _text(insight.get("level")) if insight.get("level") != "-" else "")]
            evidence = insight.get("evidence") or insight.get("discernment")
            if evidence:
                block.append(kit.para(evidence))
            moves = _items(insight.get("mentor_moves"), 3)
            if moves:
                block += [kit.para("MENTOR ACTIONS", "label"), kit.gap(2), kit.bullets(moves)]
            if insight.get("scripture_anchor"):
                block.append(kit.para(insight["scripture_anchor"], "small"))
            story += [kit.KeepTogether(block), kit.gap(8)]

    full_report = context.get("full_report") or (context.get("mentor_blob_v2") or {}).get("full_report_v1")
    if full_report and isinstance(full_report, dict):
        story += _premium_sections(full_report)

    starters = _items(context.get("starters"), 4)
    if starters:
        story += kit.section_heading("Conversation starters")
        story.append(kit.bullets(starters))

    four_week = context.get("four_week") or {}
    rhythm = _items(four_week.get("rhythm"), 4)
    checkpoints = _items(four_week.get("checkpoints"), 4)
    if rhythm or checkpoints:
        story += kit.section_heading("Four-week plan")
        story.append(kit.two_col_cards("Weekly rhythm", rhythm, "Checkpoints", checkpoints))

    resources = context.get("resources") or []
    if resources:
        story += kit.section_heading("Recommended resources")
        for res in resources[:5]:
            if isinstance(res, dict):
                title = _text(res.get("title"))
                if res.get("type"):
                    title += f" ({_text(res['type'])})"
                block = [kit.para(title, "row")]
                why = res.get("why") or res.get("why_specifically_for_them")
                if why:
                    block.append(kit.para(why))
                if res.get("how_to_use"):
                    block.append(kit.label_value("How to use", res["how_to_use"]))
                story += [kit.KeepTogether(block), kit.gap(6)]
            else:
                story.append(kit.bullets([res]))

    if full_report and isinstance(full_report, dict):
        progress = full_report.get("progress_tracking") or {}
        if progress:
            story += kit.section_heading("Progress tracking")
            prev = progress.get("previous_assessment_comparison") or {}
            change, trend_word = _text(prev.get("score_change")), _text(prev.get("trend"))
            if change or trend_word:
                story.append(kit.label_value("Score change", " ".join(p for p in [change, f"({trend_word})" if trend_word else ""] if p)))
            improved = _items(prev.get("areas_improved"), 3)
            if improved:
                story += [kit.para("Areas improved", "row"), kit.bullets(improved)]
            milestones = []
            for m in (progress.get("milestones_to_track") or [])[:4]:
                text = _text(m.get("milestone")) if isinstance(m, dict) else _text(m)
                if text:
                    by = _text(m.get("expected_by")) if isinstance(m, dict) else ""
                    milestones.append(f"{text} (by {by})" if by else text)
            if milestones:
                story += [kit.para("Milestones to track", "row"), kit.bullets(milestones)]
            if progress.get("suggested_reassessment"):
                story.append(kit.label_value("Suggested reassessment", progress["suggested_reassessment"]))

        notes = full_report.get("mentor_preparation_notes") or {}
        if notes:
            story += kit.section_heading("Mentor preparation notes")
            for key, label in (("handle_with_care", "Handle with care"), ("watch_for", "Watch for"), ("cultural_considerations", "Cultural considerations")):
                if notes.get(key):
                    story.append(kit.label_value(label, notes[key]))
            if notes.get("prayer_focus_for_this_apprentice"):
                story += [kit.gap(4), kit.callout("Prayer focus", notes["prayer_focus_for_this_apprentice"])]

        personalized = full_report.get("personalized_resources") or []
        if personalized:
            story += kit.section_heading("Personalized resources")
            for res in personalized[:4]:
                title = _text(res.get("title"))
                if res.get("author"):
                    title += f" by {_text(res['author'])}"
                if res.get("type"):
                    title += f" ({_text(res['type'])})"
                block = [kit.para(title, "row")]
                if res.get("why_specifically_for_them"):
                    block.append(kit.para(res["why_specifically_for_them"]))
                if res.get("how_to_use"):
                    block.append(kit.label_value("How to use", res["how_to_use"]))
                if res.get("conversation_starter_from_book"):
                    block.append(kit.label_value("Discussion", res["conversation_starter_from_book"]))
                story += [kit.KeepTogether(block), kit.gap(8)]
    return story


def render_pdf_v2(context: Dict[str, Any]) -> bytes:
    """Branded Mentor Report PDF (specs/008-pdf-redesign). Always returns a valid PDF.

    Includes full premium report content if available in context.
    """
    name = _text(context.get("apprentice_name")) or "Apprentice"
    mc = _num(context.get("overall_mc_percent"))
    fallback = [
        f"Health Score: {_text(context.get('health_score'))} ({_text(context.get('health_band'))})",
        f"Biblical Knowledge: {mc:.0f}% ({_text(context.get('knowledge_band'))})",
        "Top strengths: " + ", ".join(_items(context.get("top_strengths"), 3)),
        "Growth areas: " + ", ".join(_items(context.get("top_gaps"), 3)),
        "Open the T[root]H app for the full report.",
    ]
    return kit.build_pdf(
        "Mentor Report",
        name,
        kit.format_date(context.get("submitted_date")) or f"Generated {kit.format_date(datetime.now())}",
        lambda: build_mentor_story(context),
        fallback_lines=fallback,
        context_id="mentor_report_v2",
    )
