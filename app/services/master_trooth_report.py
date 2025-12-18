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
        c.drawString(40, height-60, "Master T[root]H Assessment Report")
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
    lines.append("<h1>Master T[root]H Assessment Report</h1>")
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
        'priority_action': priority_action,
        'trend_note': trend_note,
        'app_url': getattr(settings, 'app_url', ''),
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
    """Convert Markdown to PDF via ReportLab fallback by first building a simple PDF.

    NOTE: We keep ReportLab fallback; if you prefer Pandoc/wkhtmltopdf, wire here.
    """
    md_text = render_markdown_print_v2(context)
    # Render a more polished PDF using ReportLab Platypus with simple Markdown parsing
    if _HAS_REPORTLAB:
        try:
            import io
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER

            buf = io.BytesIO()
            doc = SimpleDocTemplate(
                buf,
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=60,
                bottomMargin=60,
            )

            styles = getSampleStyleSheet()
            # Customize a few styles for headings and body
            h1 = ParagraphStyle(
                name="Heading1Custom",
                parent=styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=18,
                leading=22,
                spaceBefore=6,
                spaceAfter=8,
                alignment=TA_CENTER,
            )
            h2 = ParagraphStyle(
                name="Heading2Custom",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=18,
                spaceBefore=10,
                spaceAfter=6,
            )
            h3 = ParagraphStyle(
                name="Heading3Custom",
                parent=styles["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=16,
                spaceBefore=8,
                spaceAfter=4,
            )
            body = ParagraphStyle(
                name="BodyCustom",
                parent=styles["BodyText"],
                fontName="Helvetica",
                fontSize=10.5,
                leading=14,
                spaceBefore=2,
                spaceAfter=6,
            )

            story = []

            # Title
            title_text = f"T[root]H Mentor Report — {context.get('apprentice_name') or ''}"
            story.append(Paragraph(title_text, h1))
            story.append(Spacer(1, 8))

            # Minimal Markdown-to-Flowables: support headings, paragraphs, and lists
            lines = md_text.splitlines()
            buffer_para: list[str] = []
            list_buffer: list[tuple[str, str]] = []  # (type, text) where type in {"bullet","number"}

            def flush_paragraph():
                nonlocal buffer_para
                if buffer_para:
                    para_text = " ".join([l.strip() for l in buffer_para]).strip()
                    if para_text:
                        story.append(Paragraph(para_text, body))
                        story.append(Spacer(1, 4))
                buffer_para = []

            def flush_list():
                nonlocal list_buffer
                if list_buffer:
                    # Group into a single list flowable
                    li = []
                    bulletType = "bullet" if any(t == "bullet" for t, _ in list_buffer) else "1"
                    for t, txt in list_buffer:
                        li.append(ListItem(Paragraph(txt.strip(), body)))
                    story.append(ListFlowable(li, bulletType=bulletType, start='1'))
                    story.append(Spacer(1, 6))
                list_buffer = []

            import re as _re
            bullet_re = _re.compile(r"^\s*[-\*\+]\s+")
            number_re = _re.compile(r"^\s*\d+[\.)]\s+")

            for raw in lines:
                line = raw.rstrip("\n")
                if not line.strip():
                    flush_paragraph()
                    flush_list()
                    continue

                # Headings
                if line.startswith("### "):
                    flush_paragraph(); flush_list()
                    story.append(Paragraph(line[4:].strip(), h3))
                    continue
                if line.startswith("## "):
                    flush_paragraph(); flush_list()
                    story.append(Paragraph(line[3:].strip(), h2))
                    continue
                if line.startswith("# "):
                    flush_paragraph(); flush_list()
                    story.append(Paragraph(line[2:].strip(), h1))
                    continue

                # Lists
                if bullet_re.match(line):
                    flush_paragraph()
                    text = bullet_re.sub("", line)
                    list_buffer.append(("bullet", text))
                    continue
                if number_re.match(line):
                    flush_paragraph()
                    text = number_re.sub("", line)
                    list_buffer.append(("number", text))
                    continue

                # Otherwise accumulate in paragraph buffer
                buffer_para.append(line)

            # Flush any remaining buffers
            flush_paragraph()
            flush_list()

            doc.build(story)
            buf.seek(0)
            return buf.read()
        except Exception as e:
            logger.error(f"Failed to render PDF via Platypus: {e}")
            # fall back to very simple canvas drawing if Platypus fails
            try:
                import io
                buf = io.BytesIO()
                c = canvas.Canvas(buf, pagesize=letter)
                width, height = letter
                c.setFont('Helvetica-Bold', 16)
                c.drawString(40, height-60, f"T[root]H Mentor Report - {context.get('apprentice_name')}")
                c.setFont('Helvetica', 10)
                y = height - 90
                for line in md_text.splitlines():
                    if not line.strip():
                        y -= 8
                        continue
                    # strip common markdown markers for readability
                    clean = line.lstrip('#').lstrip(' ').lstrip('-*+ ').strip()
                    c.drawString(40, y, clean[:120])
                    y -= 14
                    if y < 80:
                        c.showPage()
                        c.setFont('Helvetica', 10)
                        y = height - 60
                c.showPage()
                c.save()
                buf.seek(0)
                return buf.read()
            except Exception:
                pass

    # Basic bytes fallback when ReportLab is not available
    return md_text.encode('utf-8')
