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
import re
from app.core.settings import settings

logger = logging.getLogger("app.master_report")

try:  # Optional dependency path
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas  # type: ignore
    from reportlab.lib import colors  # type: ignore
    _HAS_REPORTLAB = True
except Exception:  # pragma: no cover
    _HAS_REPORTLAB = False


def generate_pdf(apprentice_name: Optional[str], scores: Dict) -> bytes:
    version = scores.get('version', 'master_v1')
    overall = scores.get('overall_score', 7)
    cat_scores = scores.get('category_scores') or {}
    top3 = scores.get('top3') or []

    if _HAS_REPORTLAB:
        import io
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter
        c.setFont('Helvetica-Bold', 16)
        c.drawString(40, height-60, "Master T[root]H Discipleship Report")
        c.setFont('Helvetica', 11)
        c.drawString(40, height-80, f"Apprentice: {apprentice_name or 'Apprentice'}")
        c.drawString(40, height-96, f"Version: {version}")
        c.drawString(40, height-112, f"Overall Score: {overall}")
        y = height-140
        c.drawString(40, y, "Top Categories:")
        y -= 18
        for item in top3:
            c.drawString(50, y, f"- {item.get('category')}: {item.get('score')}")
            y -= 16
        y -= 10
        c.drawString(40, y, "All Categories:")
        y -= 18
        for name, sc in cat_scores.items():
            c.drawString(50, y, f"- {name}: {sc}")
            y -= 16
        c.showPage()
        c.save()
        buf.seek(0)
        return buf.read()

    # Fallback
    text = [
        "MASTER REPORT",
        f"Apprentice: {apprentice_name or 'Apprentice'}",
        f"Version: {version}",
        f"Overall: {overall}",
        "Top:",
    ] + [f"- {i.get('category')}: {i.get('score')}" for i in top3] + [
        "",
        "All Categories:",
    ] + [f"- {k}: {v}" for k, v in cat_scores.items()]
    return ("\n".join(text)).encode()


def generate_html(apprentice_name: Optional[str], scores: Dict) -> str:
    version = scores.get('version', 'master_v1')
    overall = scores.get('overall_score', 7)
    cat_scores = scores.get('category_scores') or {}
    top3 = scores.get('top3') or []
    lines = []
    lines.append("<h1>Master T[root]H Discipleship Report</h1>")
    lines.append(f"<p>Apprentice: {apprentice_name or 'Apprentice'}</p>")
    lines.append(f"<p>Version: {version} • Overall: {overall}</p>")
    lines.append("<h3>Top Categories</h3>")
    lines.append("<ul>" + "".join([f"<li>{i.get('category')}: {i.get('score')}</li>" for i in top3]) + "</ul>")
    lines.append("<h3>All Categories</h3>")
    lines.append("<ul>" + "".join([f"<li>{k}: {v}</li>" for k, v in cat_scores.items()]) + "</ul>")
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

    # Include full_report_v1 from scores if available (for premium PDF)
    full_report = scores.get('full_report_v1')

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


def _load_email_template_text() -> str | None:
    """Load mentor_report_email_template.html from common locations.

    This template uses a simple placeholder syntax with {var} and {#each list}...{/each}.
    """
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    candidates = [
        os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates/email')), 'mentor_report_email_template.html'),
        os.path.join(backend_root, 'mentor_report_email_template.html'),
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            continue
    return None


def _render_template_simple(tpl: str, context: Dict[str, Any]) -> str:
    """Very small, non-Jinja renderer for the provided email template.

    Supports:
    - {var} variable replacement from context
    - {#each list} ... {/each} loops, where inside the block {this} refers to the item
      and {key} pulls from dict item keys. Nested {#each} is supported for one level.
    """
    def replace_vars(s: str, scope: dict) -> str:
        def _sub(m: re.Match):
            key = m.group(1)
            return str(scope.get(key, context.get(key, '')))
        return re.sub(r"\{([a-zA-Z0-9_\.]+)\}", _sub, s)

    # Handle {#each path} blocks
    def render_block(text: str, scope: dict) -> str:
        pattern = re.compile(r"\{#each\s+([a-zA-Z0-9_\.]+)\}(.*?)\{/each\}", re.DOTALL)
        while True:
            m = pattern.search(text)
            if not m:
                break
            path, block = m.group(1), m.group(2)
            # Resolve list from scope or root context
            parts = path.split('.')
            arr = scope
            for p in parts:
                arr = arr.get(p) if isinstance(arr, dict) else None
                if arr is None:
                    break
            if arr is None:
                arr = context
                for p in parts:
                    arr = arr.get(p) if isinstance(arr, dict) else None
                    if arr is None:
                        break
            rendered = ''
            if isinstance(arr, list):
                for item in arr:
                    if isinstance(item, dict):
                        local = {**scope, **item, 'this': item}
                    else:
                        local = {**scope, 'this': item}
                    seg = replace_vars(block, local)
                    # Recurse to support nested each
                    seg = render_block(seg, local)
                    rendered += seg
            text = text[:m.start()] + rendered + text[m.end():]
        return replace_vars(text, scope)

    return render_block(tpl, {})


def render_email_v2(context: Dict[str, Any]) -> str:
    """Render the mentor report email using Jinja2 template."""
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        logger.error("Jinja2 not available for email rendering")
        return f"<div><h1>T[root]H Mentor Report</h1><p>Apprentice: {context.get('apprentice_name')}</p></div>"
    
    # Load template from email templates directory
    email_dir = os.path.join(os.path.dirname(__file__), '../templates/email')
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    env = Environment(loader=FileSystemLoader([os.path.abspath(email_dir), backend_root]))
    
    # Add custom filters
    from datetime import datetime
    def strftime_filter(value, format_string='%Y'):
        """Custom strftime filter for Jinja2."""
        if value == 'now':
            return datetime.now().strftime(format_string)
        elif isinstance(value, datetime):
            return value.strftime(format_string)
        elif isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime(format_string)
            except Exception:
                return value
        return str(value)
    
    env.filters['strftime'] = strftime_filter
    
    try:
        template = env.get_template('mentor_report_email_template.html')
        return template.render(**context)
    except Exception as e:
        logger.error(f"Failed to render Jinja2 email template: {e}")
        # Fallback minimal HTML
        return f"""<div style="font-family: sans-serif; padding: 20px;">
            <h1>T[root]H Mentor Report</h1>
            <p><strong>Apprentice:</strong> {context.get('apprentice_name', 'Unknown')}</p>
            <p><strong>Biblical Knowledge:</strong> {context.get('overall_mc_percent', 0)}% ({context.get('knowledge_band', 'N/A')})</p>
            <p><strong>Overall Score:</strong> {context.get('overall_score', 'N/A')}</p>
        </div>"""


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


def render_pdf_v2(context: Dict[str, Any]) -> bytes:
    """Generate a beautifully styled PDF report with colors and proper formatting.
    
    Includes full premium report content if available in context.
    """
    if not _HAS_REPORTLAB:
        md_text = render_markdown_print_v2(context)
        return md_text.encode('utf-8')
    
    try:
        import io
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
            ListFlowable, ListItem, HRFlowable, KeepTogether, PageBreak
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        
        # Define brand colors
        GOLD = HexColor('#D4AF37')
        DARK_GOLD = HexColor('#B8960C')
        BLACK = HexColor('#1A1A1A')
        DARK_GREY = HexColor('#333333')
        GREY = HexColor('#666666')
        LIGHT_GREY = HexColor('#E5E5E5')
        GREEN = HexColor('#28A745')
        BLUE = HexColor('#007BFF')
        ORANGE = HexColor('#FD7E14')
        RED = HexColor('#DC3545')
        PURPLE = HexColor('#6F42C1')
        
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=50,
            rightMargin=50,
            topMargin=50,
            bottomMargin=50,
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'TitleCustom',
            parent=styles['Title'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=BLACK,
            alignment=TA_CENTER,
            spaceAfter=4,
        )
        
        subtitle_style = ParagraphStyle(
            'SubtitleCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=12,
            leading=14,
            textColor=GREY,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        
        section_header = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=GOLD,
            spaceBefore=16,
            spaceAfter=8,
            borderPadding=(0, 0, 4, 0),
        )
        
        subsection_header = ParagraphStyle(
            'SubsectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=DARK_GREY,
            spaceBefore=12,
            spaceAfter=6,
        )
        
        body_style = ParagraphStyle(
            'BodyCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=DARK_GREY,
            spaceAfter=6,
        )
        
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            textColor=GREY,
        )
        
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            textColor=DARK_GREY,
        )
        
        score_large = ParagraphStyle(
            'ScoreLarge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=36,
            leading=40,
            textColor=GOLD,
            alignment=TA_CENTER,
        )
        
        story = []
        
        # ===== HEADER =====
        story.append(Paragraph("T[root]H Mentor Report", title_style))
        apprentice_name = context.get('apprentice_name', 'Apprentice')
        submitted_date = context.get('submitted_date', '')
        if submitted_date:
            try:
                from datetime import datetime
                if isinstance(submitted_date, str):
                    dt = datetime.fromisoformat(submitted_date.replace('Z', '+00:00'))
                    submitted_date = dt.strftime('%B %d, %Y')
                elif isinstance(submitted_date, datetime):
                    submitted_date = submitted_date.strftime('%B %d, %Y')
            except:
                pass
        story.append(Paragraph(f"{apprentice_name} • {submitted_date}", subtitle_style))
        
        # Gold divider line
        story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=16))
        
        # ===== HEALTH SCORE BOX =====
        health_score = context.get('overall_score', 0)
        health_band = context.get('knowledge_band', 'Developing')
        mc_percent = context.get('overall_mc_percent', 0)
        
        # Determine band color
        band_color = GREEN if health_band.lower() in ['excellent', 'flourishing'] else \
                     BLUE if health_band.lower() in ['good', 'maturing'] else \
                     ORANGE if health_band.lower() in ['developing', 'growing'] else \
                     RED
        
        score_table_data = [
            [Paragraph(f"<font color='#{GOLD.hexval()[2:]}'>{mc_percent}%</font>", score_large),
             Paragraph(f"<b>Biblical Knowledge</b><br/><font color='#{band_color.hexval()[2:]}'>{health_band}</font>", body_style)],
        ]
        score_table = Table(score_table_data, colWidths=[1.5*inch, 4*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GREY),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 16))
        
        # ===== STRENGTHS & GAPS =====
        top_strengths = context.get('top_strengths', [])
        top_gaps = context.get('top_gaps', [])
        
        if top_strengths or top_gaps:
            sg_data = [[
                Paragraph(f"<font color='#{GREEN.hexval()[2:]}'><b>✓ Top Strengths</b></font>", body_style),
                Paragraph(f"<font color='#{ORANGE.hexval()[2:]}'><b>↑ Growth Areas</b></font>", body_style)
            ]]
            strengths_text = "<br/>".join([f"• {s}" for s in top_strengths[:3]]) if top_strengths else "—"
            gaps_text = "<br/>".join([f"• {g}" for g in top_gaps[:3]]) if top_gaps else "—"
            sg_data.append([
                Paragraph(strengths_text, body_style),
                Paragraph(gaps_text, body_style)
            ])
            sg_table = Table(sg_data, colWidths=[2.75*inch, 2.75*inch])
            sg_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), HexColor('#E8F5E9')),
                ('BACKGROUND', (1, 0), (1, -1), HexColor('#FFF3E0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 10),
                ('LINEBELOW', (0, 0), (-1, 0), 1, LIGHT_GREY),
            ]))
            story.append(sg_table)
            story.append(Spacer(1, 16))
        
        # ===== CATEGORY SCORES =====
        categories = context.get('categories', [])
        if categories:
            story.append(Paragraph("Category Scores", section_header))
            
            cat_data = [["Category", "Score", "Level"]]
            for cat in categories:
                score = cat.get('score', 0)
                level = cat.get('level', '-')
                score_color = GREEN if score >= 7 else BLUE if score >= 5 else ORANGE if score >= 3 else RED
                cat_data.append([
                    Paragraph(cat.get('name', ''), body_style),
                    Paragraph(f"<font color='#{score_color.hexval()[2:]}'><b>{score}/10</b></font>", body_style),
                    Paragraph(level, body_style)
                ])
            
            cat_table = Table(cat_data, colWidths=[3*inch, 1.2*inch, 1.3*inch])
            cat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), DARK_GREY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, LIGHT_GREY),
            ]))
            story.append(cat_table)
            story.append(Spacer(1, 16))
        
        # ===== BIBLICAL KNOWLEDGE BREAKDOWN =====
        knowledge_topics = context.get('knowledge_topics', [])
        if knowledge_topics:
            story.append(Paragraph("Biblical Knowledge Breakdown", section_header))
            
            kn_data = [["Topic", "Score", "Status"]]
            for topic in knowledge_topics:
                percent = topic.get('percent', 0)
                score_color = GREEN if percent >= 70 else ORANGE if percent >= 40 else RED
                status = "Strong" if percent >= 70 else "Developing" if percent >= 40 else "Needs Focus"
                kn_data.append([
                    Paragraph(topic.get('topic', ''), body_style),
                    Paragraph(f"<font color='#{score_color.hexval()[2:]}'><b>{percent}%</b></font>", body_style),
                    Paragraph(status, body_style)
                ])
            
            kn_table = Table(kn_data, colWidths=[3*inch, 1.2*inch, 1.3*inch])
            kn_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), DARK_GREY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ]))
            story.append(kn_table)
            story.append(Spacer(1, 16))
        
        # ===== OPEN-ENDED INSIGHTS =====
        open_insights = context.get('open_insights', [])
        if open_insights:
            story.append(Paragraph("Spiritual Life Insights", section_header))
            
            for insight in open_insights[:5]:  # Limit to top 5
                category = insight.get('category', '')
                level = insight.get('level', '-')
                level_color = GREEN if level.lower() in ['mature', 'flourishing', 'excellent'] else \
                              BLUE if level.lower() in ['developing', 'growing', 'good'] else \
                              ORANGE
                
                insight_box = []
                insight_box.append(Paragraph(
                    f"<font color='#{DARK_GREY.hexval()[2:]}'><b>{category}</b></font> — "
                    f"<font color='#{level_color.hexval()[2:]}'>{level}</font>",
                    subsection_header
                ))
                
                evidence = insight.get('evidence', '') or insight.get('discernment', '')
                if evidence:
                    insight_box.append(Paragraph(evidence, body_style))
                
                mentor_moves = insight.get('mentor_moves', [])
                if mentor_moves:
                    moves_text = "<br/>".join([f"• {m}" for m in mentor_moves[:3]])
                    insight_box.append(Paragraph(f"<b>Mentor Actions:</b><br/>{moves_text}", body_style))
                
                story.append(KeepTogether(insight_box))
                story.append(Spacer(1, 8))
        
        # ===== FULL PREMIUM REPORT (if available) =====
        full_report = context.get('full_report') or context.get('mentor_blob_v2', {}).get('full_report_v1')
        if full_report and isinstance(full_report, dict):
            story.append(PageBreak())
            story.append(Paragraph("✦ Premium Detailed Analysis", section_header))
            story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=12))
            
            # Executive Summary
            exec_summary = full_report.get('executive_summary', {})
            if exec_summary:
                story.append(Paragraph("Executive Summary", subsection_header))
                one_liner = exec_summary.get('one_liner', '')
                if one_liner:
                    story.append(Paragraph(f"<i>{one_liner}</i>", body_style))
                trajectory_note = exec_summary.get('trajectory_note', '')
                if trajectory_note:
                    story.append(Paragraph(trajectory_note, body_style))
                story.append(Spacer(1, 12))
            
            # Strengths Deep Dive
            strengths_deep = full_report.get('strengths_deep_dive', [])
            if strengths_deep:
                story.append(Paragraph(f"<font color='#{GREEN.hexval()[2:]}'>Strengths Deep Dive</font>", subsection_header))
                for s in strengths_deep[:3]:
                    area = s.get('area', '')
                    summary = s.get('summary', '')
                    leverage = s.get('how_to_leverage', '')
                    content = f"<b>{area}</b><br/>{summary}"
                    if leverage:
                        content += f"<br/><i>How to leverage: {leverage}</i>"
                    story.append(Paragraph(content, body_style))
                    story.append(Spacer(1, 6))
            
            # Gaps Deep Dive
            gaps_deep = full_report.get('gaps_deep_dive', [])
            if gaps_deep:
                story.append(Paragraph(f"<font color='#{ORANGE.hexval()[2:]}'>Growth Areas Deep Dive</font>", subsection_header))
                for g in gaps_deep[:3]:
                    area = g.get('area', '')
                    summary = g.get('summary', '')
                    biblical = g.get('biblical_perspective', '')
                    content = f"<b>{area}</b><br/>{summary}"
                    if biblical:
                        content += f"<br/><font color='#{BLUE.hexval()[2:]}'><i>📖 {biblical}</i></font>"
                    story.append(Paragraph(content, body_style))
                    
                    # Growth pathway
                    pathway = g.get('growth_pathway', {})
                    if pathway:
                        phase1 = pathway.get('phase_1_weeks_1_4', {})
                        if phase1:
                            goal = phase1.get('goal', '')
                            if goal:
                                story.append(Paragraph(f"<b>Weeks 1-4 Goal:</b> {goal}", body_style))
                    story.append(Spacer(1, 8))
            
            # Conversation Guide
            conv_guide = full_report.get('conversation_guide', {})
            if conv_guide:
                story.append(Paragraph(f"<font color='#{PURPLE.hexval()[2:]}'>Mentor Conversation Guide</font>", subsection_header))
                
                # AI format sessions (session_1_opening, session_2_growth_areas, session_3_check_in)
                session_keys = [
                    ('session_1_opening', 'Session 1: Opening'),
                    ('session_2_growth_areas', 'Session 2: Growth Areas'),
                    ('session_3_check_in', 'Session 3: Check-In')
                ]
                has_ai_sessions = False
                for key, title in session_keys:
                    session = conv_guide.get(key, {})
                    if session:
                        has_ai_sessions = True
                        theme = session.get('theme', '')
                        duration = session.get('duration_minutes', '')
                        header = f"<b>{title}</b>"
                        if theme:
                            header += f" — {theme}"
                        if duration:
                            header += f" <font color='#{GREY.hexval()[2:]}'>({duration} min)</font>"
                        story.append(Paragraph(header, body_style))
                        
                        # Key points
                        key_points = session.get('key_points_to_cover', [])
                        if key_points:
                            for kp in key_points[:3]:
                                point = kp.get('point', '') if isinstance(kp, dict) else str(kp)
                                talking = kp.get('talking_point', '') if isinstance(kp, dict) else ''
                                if point:
                                    story.append(Paragraph(f"  • <b>{point}</b>", body_style))
                                    if talking:
                                        story.append(Paragraph(f"    <i>\"{talking}\"</i>", body_style))
                        
                        # Questions
                        questions = session.get('questions_to_ask', [])
                        if questions:
                            q_text = "<br/>".join([f"  ? {q}" for q in questions[:3]])
                            story.append(Paragraph(q_text, body_style))
                        
                        story.append(Spacer(1, 6))
                
                # Legacy format fallback
                if not has_ai_sessions:
                    opening_q = conv_guide.get('opening_questions', [])
                    if opening_q:
                        q_text = "<br/>".join([f"• {q}" for q in opening_q[:3]])
                        story.append(Paragraph(f"<b>Opening Questions:</b><br/>{q_text}", body_style))
                    
                    sessions = conv_guide.get('sessions', [])
                    if sessions:
                        for i, sess in enumerate(sessions[:3], 1):
                            focus = sess.get('focus', '')
                            goal = sess.get('goal', '')
                            if focus:
                                story.append(Paragraph(f"<b>Session {i}:</b> {focus}", body_style))
                                if goal:
                                    story.append(Paragraph(f"<i>Goal: {goal}</i>", body_style))
                story.append(Spacer(1, 8))
            
            # Biblical Knowledge Analysis
            bk_analysis = full_report.get('biblical_knowledge_analysis', {})
            if bk_analysis:
                story.append(Paragraph(f"<font color='#{BLUE.hexval()[2:]}'>Biblical Knowledge Analysis</font>", subsection_header))
                
                # Overall score and mastery level
                overall_percent = bk_analysis.get('overall_percent')
                mastery_level = bk_analysis.get('mastery_level', '')
                if overall_percent or mastery_level:
                    score_text = ""
                    if overall_percent:
                        score_color = GREEN if overall_percent >= 70 else ORANGE if overall_percent >= 50 else RED
                        score_text = f"<font color='#{score_color.hexval()[2:]}'><b>{overall_percent}%</b></font>"
                    if mastery_level:
                        score_text += f" — {mastery_level}"
                    story.append(Paragraph(score_text, body_style))
                    story.append(Spacer(1, 6))
                
                # Summary (legacy format)
                bk_summary = bk_analysis.get('summary', '')
                if bk_summary:
                    story.append(Paragraph(bk_summary, body_style))
                
                # Topic breakdown (AI format: by_topic_breakdown or legacy: topics)
                bk_topics = bk_analysis.get('by_topic_breakdown', []) or bk_analysis.get('topics', [])
                if bk_topics:
                    story.append(Paragraph("<b>Topic Performance:</b>", body_style))
                    for topic in bk_topics[:6]:
                        topic_name = topic.get('topic', '') or topic.get('name', '')
                        # Support both AI format (score_percent) and legacy (percent, score)
                        percent = topic.get('score_percent') or topic.get('percent') or topic.get('score', 0)
                        level = topic.get('level', '')
                        affirmation = topic.get('affirmation', '')
                        key_gaps = topic.get('key_gaps', [])
                        study_prescription = topic.get('study_prescription', '')
                        
                        score_color = GREEN if percent >= 70 else ORANGE if percent >= 50 else RED
                        level_text = f" ({level})" if level else ""
                        story.append(Paragraph(
                            f"  • <b>{topic_name}</b>: <font color='#{score_color.hexval()[2:]}'>{percent}%</font>{level_text}",
                            body_style
                        ))
                        if affirmation:
                            story.append(Paragraph(f"    <font color='#{GREEN.hexval()[2:]}'>✓ {affirmation}</font>", body_style))
                        if key_gaps:
                            gaps_text = ", ".join(key_gaps[:3])
                            story.append(Paragraph(f"    <font color='#{RED.hexval()[2:]}'>Gaps: {gaps_text}</font>", body_style))
                        if study_prescription:
                            story.append(Paragraph(f"    <font color='#{BLUE.hexval()[2:]}'>📚 {study_prescription}</font>", body_style))
                
                # Theological health check
                theological = bk_analysis.get('theological_health_check', {})
                if theological:
                    story.append(Spacer(1, 6))
                    story.append(Paragraph("<b>Theological Health Check:</b>", body_style))
                    solid = theological.get('core_doctrines_solid', [])
                    if solid:
                        story.append(Paragraph(
                            f"  <font color='#{GREEN.hexval()[2:]}'>✓ Solid: {', '.join(solid)}</font>",
                            body_style
                        ))
                    needing = theological.get('areas_needing_clarification', [])
                    if needing:
                        story.append(Paragraph(
                            f"  <font color='#{ORANGE.hexval()[2:]}'>⚠ Needs clarification: {', '.join(needing)}</font>",
                            body_style
                        ))
                    concerns = theological.get('potential_concerns', [])
                    if concerns:
                        story.append(Paragraph(
                            f"  <font color='#{RED.hexval()[2:]}'>⚠ Concerns: {', '.join(concerns)}</font>",
                            body_style
                        ))
                
                # Bible reading plan
                reading_plan = bk_analysis.get('recommended_bible_reading_plan', {})
                if reading_plan:
                    story.append(Spacer(1, 6))
                    plan_name = reading_plan.get('name', 'Bible Reading Plan')
                    plan_desc = reading_plan.get('description', '')
                    plan_why = reading_plan.get('why_this_plan', '')
                    story.append(Paragraph(
                        f"<b>📖 Recommended: {plan_name}</b>",
                        body_style
                    ))
                    if plan_desc:
                        story.append(Paragraph(plan_desc, body_style))
                    if plan_why:
                        story.append(Paragraph(f"<i>Why: {plan_why}</i>", body_style))
                
                story.append(Spacer(1, 8))
            
            # Spiritual Formation Insights
            sf_insights = full_report.get('spiritual_formation_insights', [])
            if sf_insights:
                story.append(Paragraph(f"<font color='#{PURPLE.hexval()[2:]}'>Spiritual Formation Insights</font>", subsection_header))
                for insight in sf_insights[:5]:
                    area = insight.get('area', '') or insight.get('category', '')
                    # Support both AI format (current_level, detailed_observation) and legacy (level, summary/insight)
                    level = insight.get('current_level', '') or insight.get('level', '')
                    observation = insight.get('detailed_observation', '') or insight.get('summary', '') or insight.get('observation', '') or insight.get('insight', '')
                    
                    level_color = GREEN if level.lower() in ['mature', 'flourishing', 'maturing'] else \
                                  BLUE if level.lower() in ['stable', 'good'] else \
                                  ORANGE if level.lower() in ['developing', 'growing'] else \
                                  RED
                    content = f"<b>{area}</b>"
                    if level:
                        content += f" — <font color='#{level_color.hexval()[2:]}'>{level}</font>"
                    story.append(Paragraph(content, body_style))
                    
                    if observation:
                        story.append(Paragraph(observation, body_style))
                    
                    # Maturity markers (AI format)
                    markers_present = insight.get('maturity_markers_present', [])
                    markers_missing = insight.get('maturity_markers_missing', [])
                    if markers_present or markers_missing:
                        markers_content = ""
                        if markers_present:
                            markers_content += f"<font color='#{GREEN.hexval()[2:]}'>✓ Present: {', '.join(markers_present[:4])}</font>"
                        if markers_missing:
                            if markers_content:
                                markers_content += "<br/>"
                            markers_content += f"<font color='#{ORANGE.hexval()[2:]}'>○ Missing: {', '.join(markers_missing[:4])}</font>"
                        story.append(Paragraph(markers_content, body_style))
                    
                    # Custom development plan (AI format)
                    custom_plan = insight.get('custom_development_plan', {})
                    if custom_plan:
                        plan_text = "<b>Development Plan:</b><br/>"
                        if custom_plan.get('immediate_30_days'):
                            plan_text += f"  📅 30 days: {custom_plan['immediate_30_days']}<br/>"
                        if custom_plan.get('quarter_goal'):
                            plan_text += f"  📅 Quarter: {custom_plan['quarter_goal']}<br/>"
                        if custom_plan.get('year_vision'):
                            plan_text += f"  📅 Year: {custom_plan['year_vision']}"
                        story.append(Paragraph(plan_text, body_style))
                    
                    # Mentor discussion questions (AI format)
                    mentor_questions = insight.get('mentor_discussion_questions', [])
                    if mentor_questions:
                        q_text = "<b>Questions to Ask:</b><br/>" + "<br/>".join([f"  ❓ {q}" for q in mentor_questions[:3]])
                        story.append(Paragraph(q_text, body_style))
                    
                    # Legacy recommendations/mentor_moves
                    recs = insight.get('recommendations', []) or insight.get('mentor_moves', [])
                    if recs and not mentor_questions:  # Only show if no mentor_questions
                        recs_text = "<br/>".join([f"  • {r}" for r in recs[:2]])
                        story.append(Paragraph(f"<i>{recs_text}</i>", body_style))
                    
                    story.append(Spacer(1, 8))
                story.append(Spacer(1, 8))
        
        # ===== PRIORITY ACTION =====
        priority_action = context.get('priority_action')
        if priority_action:
            story.append(Paragraph("🎯 Priority Action This Week", section_header))
            pa_title = priority_action.get('title', '')
            pa_desc = priority_action.get('description', '')
            pa_scripture = priority_action.get('scripture', '')
            
            if pa_title:
                story.append(Paragraph(f"<b>{pa_title}</b>", body_style))
            if pa_desc:
                story.append(Paragraph(pa_desc, body_style))
            if pa_scripture:
                story.append(Paragraph(f"<font color='#{BLUE.hexval()[2:]}'><i>📖 {pa_scripture}</i></font>", body_style))
            story.append(Spacer(1, 12))
        
        # ===== CONVERSATION STARTERS =====
        starters = context.get('starters', [])
        if starters:
            story.append(Paragraph("💬 Conversation Starters", section_header))
            for s in starters[:4]:
                story.append(Paragraph(f"• {s}", body_style))
            story.append(Spacer(1, 12))
        
        # ===== FOUR WEEK PLAN =====
        four_week = context.get('four_week', {})
        rhythm = four_week.get('rhythm', [])
        checkpoints = four_week.get('checkpoints', [])
        if rhythm or checkpoints:
            story.append(Paragraph("📅 Four-Week Plan", section_header))
            if rhythm:
                story.append(Paragraph("<b>Weekly Rhythm:</b>", body_style))
                for r in rhythm[:4]:
                    story.append(Paragraph(f"• {r}", body_style))
            if checkpoints:
                story.append(Paragraph("<b>Checkpoints:</b>", body_style))
                for cp in checkpoints[:4]:
                    story.append(Paragraph(f"• {cp}", body_style))
            story.append(Spacer(1, 12))
        
        # ===== RESOURCES =====
        resources = context.get('resources', [])
        if resources:
            story.append(Paragraph("📚 Recommended Resources", section_header))
            for res in resources[:5]:
                if isinstance(res, dict):
                    title = res.get('title', '')
                    why = res.get('why', '') or res.get('why_specifically_for_them', '')
                    res_type = res.get('type', '')
                    how_to_use = res.get('how_to_use', '')
                    content = f"<b>{title}</b>"
                    if res_type:
                        content += f" ({res_type})"
                    if why:
                        content += f"<br/>{why}"
                    if how_to_use:
                        content += f"<br/><i>How to use: {how_to_use}</i>"
                    story.append(Paragraph(content, body_style))
                    story.append(Spacer(1, 6))
                else:
                    story.append(Paragraph(f"• {res}", body_style))
            story.append(Spacer(1, 12))
        
        # ===== PREMIUM: PROGRESS TRACKING =====
        if full_report and isinstance(full_report, dict):
            progress_tracking = full_report.get('progress_tracking', {})
            if progress_tracking:
                story.append(Paragraph(f"<font color='#{BLUE.hexval()[2:]}'>📈 Progress Tracking</font>", section_header))
                
                # Previous assessment comparison
                prev_comparison = progress_tracking.get('previous_assessment_comparison', {})
                if prev_comparison:
                    score_change = prev_comparison.get('score_change', '')
                    trend = prev_comparison.get('trend', '')
                    if score_change or trend:
                        trend_color = GREEN if 'improv' in trend.lower() or '+' in str(score_change) else ORANGE
                        story.append(Paragraph(
                            f"<b>Score Change:</b> <font color='#{trend_color.hexval()[2:]}'>{score_change}</font> ({trend})",
                            body_style
                        ))
                    areas_improved = prev_comparison.get('areas_improved', [])
                    if areas_improved:
                        story.append(Paragraph("<b>Areas Improved:</b>", body_style))
                        for area in areas_improved[:3]:
                            story.append(Paragraph(f"  ✓ {area}", body_style))
                
                # Milestones
                milestones = progress_tracking.get('milestones_to_track', [])
                if milestones:
                    story.append(Paragraph("<b>Milestones to Track:</b>", body_style))
                    for m in milestones[:4]:
                        milestone_text = m.get('milestone', '')
                        expected = m.get('expected_by', '')
                        if milestone_text:
                            content = f"  • {milestone_text}"
                            if expected:
                                content += f" <i>(by {expected})</i>"
                            story.append(Paragraph(content, body_style))
                
                reassess = progress_tracking.get('suggested_reassessment', '')
                if reassess:
                    story.append(Paragraph(f"<b>Suggested Reassessment:</b> {reassess}", body_style))
                story.append(Spacer(1, 12))
            
            # ===== PREMIUM: MENTOR PREPARATION NOTES =====
            mentor_notes = full_report.get('mentor_preparation_notes', {})
            if mentor_notes:
                story.append(Paragraph(f"<font color='#{PURPLE.hexval()[2:]}'>📝 Mentor Preparation Notes</font>", section_header))
                
                handle_care = mentor_notes.get('handle_with_care', '')
                if handle_care:
                    story.append(Paragraph(f"<b>Handle with Care:</b> {handle_care}", body_style))
                
                watch_for = mentor_notes.get('watch_for', '')
                if watch_for:
                    story.append(Paragraph(f"<b>Watch For:</b> {watch_for}", body_style))
                
                cultural = mentor_notes.get('cultural_considerations', '')
                if cultural:
                    story.append(Paragraph(f"<b>Cultural Considerations:</b> {cultural}", body_style))
                
                prayer_focus = mentor_notes.get('prayer_focus_for_this_apprentice', '')
                if prayer_focus:
                    story.append(Paragraph(
                        f"<font color='#{BLUE.hexval()[2:]}'><b>🙏 Prayer Focus:</b> <i>{prayer_focus}</i></font>",
                        body_style
                    ))
                story.append(Spacer(1, 12))
            
            # ===== PREMIUM: PERSONALIZED RESOURCES =====
            personalized_resources = full_report.get('personalized_resources', [])
            if personalized_resources:
                story.append(Paragraph(f"<font color='#{GOLD.hexval()[2:]}'>✦ Personalized Resources</font>", section_header))
                for res in personalized_resources[:4]:
                    title = res.get('title', '')
                    author = res.get('author', '')
                    res_type = res.get('type', '')
                    why = res.get('why_specifically_for_them', '')
                    how_to_use = res.get('how_to_use', '')
                    convo_starter = res.get('conversation_starter_from_book', '')
                    
                    content = f"<b>{title}</b>"
                    if author:
                        content += f" by {author}"
                    if res_type:
                        content += f" ({res_type})"
                    story.append(Paragraph(content, body_style))
                    
                    if why:
                        story.append(Paragraph(f"<i>Why for you: {why}</i>", body_style))
                    if how_to_use:
                        story.append(Paragraph(f"<b>How to use:</b> {how_to_use}", body_style))
                    if convo_starter:
                        story.append(Paragraph(
                            f"<font color='#{PURPLE.hexval()[2:]}'><b>Discussion:</b> {convo_starter}</font>",
                            body_style
                        ))
                    story.append(Spacer(1, 8))
                story.append(Spacer(1, 12))
        
        # ===== FOOTER =====
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=GOLD))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=GREY,
            alignment=TA_CENTER,
        )
        story.append(Paragraph(
            "Generated by T[root]H Discipleship • www.troothapp.com",
            footer_style
        ))
        
        doc.build(story)
        buf.seek(0)
        return buf.read()
        
    except Exception as e:
        logger.error(f"Failed to render styled PDF: {e}", exc_info=True)
        # Fallback to simple text
        md_text = render_markdown_print_v2(context)
        return md_text.encode('utf-8')
