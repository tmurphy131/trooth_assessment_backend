"""Spiritual Gifts PDF / email report generation utilities.

If ReportLab (or similar) is unavailable, falls back to a very basic PDF-like bytes payload
constructed manually (not standards-compliant for complex layout but adequate as placeholder).

Design allows swapping in a real engine later.
"""
from __future__ import annotations
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger("app.gifts_report")

try:  # Optional dependency path
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas  # type: ignore
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.utils import ImageReader  # type: ignore
    from reportlab.pdfbase import pdfmetrics  # type: ignore
    from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
    from reportlab.platypus import Table, TableStyle  # type: ignore
    _HAS_REPORTLAB = True
except Exception:  # pragma: no cover
    _HAS_REPORTLAB = False


def _compose_sections(apprentice_name: Optional[str], version: int, scores: Dict, summaries: Optional[Dict[str,str]] = None) -> Dict[str,str]:
    top_trunc = scores.get("top_gifts_truncated", [])
    top_expanded = scores.get("top_gifts_expanded", [])
    all_scores = scores.get("all_scores", [])
    lines = []
    header_name = apprentice_name or "Apprentice"
    lines.append(f"Spiritual Gifts Assessment Report (v{version})")
    lines.append(f"Apprentice: {header_name}")
    lines.append(f"Generated: {datetime.utcnow().isoformat()}Z")
    lines.append("")
    lines.append("Top Gifts (Truncated):")
    for g in top_trunc:
        summ = ''
        if summaries and g['gift'] in summaries:
            summ = f" — {summaries[g['gift']]}".strip()
        lines.append(f"  - {g['gift']}: {g['score']}{summ}")
    lines.append("")
    lines.append("Top Gifts (Expanded Ties):")
    for g in top_expanded:
        lines.append(f"  - {g['gift']}: {g['score']}")
    lines.append("")
    lines.append("All Gifts (Ordered):")
    for g in all_scores:
        lines.append(f"  - {g['gift']}: {g['score']}")
    body_text = "\n".join(lines)
    return {"text": body_text}


def generate_pdf(apprentice_name: Optional[str], version: int, scores: Dict, definitions: Dict[str, Dict]) -> bytes:
    # Build map of display_name -> short summary for quick lookup
    summaries = {d.get('display_name'): d.get('short_summary') for d in definitions.values() if d.get('short_summary')}
    sections = _compose_sections(apprentice_name, version, scores, summaries)
    # Add definitions for all gifts (full definitions requested)
    defs_lines = ["", "Definitions:"]
    # definitions: slug keyed; we may not have slug-case matching display gift names; attempt name match fallback
    for slug, d in definitions.items():
        defs_lines.append(f"-- {d.get('display_name') or slug} --")
        defs_lines.append(d.get('full_definition','').strip())
        defs_lines.append("")
    full_text = sections["text"] + "\n" + "\n".join(defs_lines)

    if _HAS_REPORTLAB:
        import io, os, textwrap

        def register_fonts():
            # Attempt to register a nicer font if a TTF exists in assets/fonts; fallback to built-ins silently.
            fonts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'fonts')
            candidates = [
                ('OpenSans-Regular.ttf', 'OpenSans'),
                ('Roboto-Regular.ttf', 'Roboto'),
            ]
            for filename, name in candidates:
                path = os.path.join(fonts_dir, filename)
                if os.path.exists(path):
                    try:
                        pdfmetrics.registerFont(TTFont(name, path))
                        return name
                    except Exception:  # pragma: no cover
                        continue
            return None

        primary_font = register_fonts() or 'Helvetica'
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter

        # --- Header with logo & title bar ---
        logo_path_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'logo.png'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'logoSmall.png'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'logoBnG.png'),
        ]
        logo_reader = None
        for lp in logo_path_candidates:
            if os.path.exists(lp):
                try:
                    logo_reader = ImageReader(lp)
                    break
                except Exception:  # pragma: no cover
                    pass

        accent_color = colors.HexColor('#2F4B7C')  # Chosen deep blue
        light_accent = colors.HexColor('#D9E2F1')

        def draw_header(page_title: str):
            c.setFillColor(accent_color)
            c.rect(0, height - 60, width, 60, fill=1, stroke=0)
            if logo_reader:
                try:
                    c.drawImage(logo_reader, 40, height - 55, width=50, height=50, preserveAspectRatio=True, mask='auto')
                except Exception:  # pragma: no cover
                    pass
            c.setFillColor(colors.white)
            c.setFont(primary_font, 18)
            c.drawString(110 if logo_reader else 40, height - 30, page_title)
            c.setFillColor(colors.black)

        def draw_footer(page_num: int):
            c.setFont(primary_font, 8)
            c.setFillColor(colors.grey)
            c.drawRightString(width - 40, 30, f"Page {page_num}")
            c.setFillColor(colors.black)

        page_num = 1
        draw_header("Spiritual Gifts Assessment Report")
        y = height - 80

        def new_page():
            nonlocal page_num, y
            draw_footer(page_num)
            c.showPage()
            page_num += 1
            draw_header("Spiritual Gifts Assessment Report (cont.)")
            y = height - 80

        def write_wrapped(text: str, font_size=11, leading=14, max_width=90):
            nonlocal y
            c.setFont(primary_font, font_size)
            wrapper = textwrap.TextWrapper(width=max_width)
            for para in text.split('\n'):
                if not para.strip():
                    y -= leading
                    if y < 60:
                        new_page()
                    continue
                for line in wrapper.wrap(para):
                    if y < 60:
                        new_page()
                    c.drawString(40, y, line)
                    y -= leading
            y -= 4
            if y < 60:
                new_page()

        # Metadata block
        meta_lines = [
            f"Apprentice: {apprentice_name or 'Apprentice'}",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            f"Version: {version}",
        ]
        c.setFillColor(light_accent)
        c.rect(30, y - 10, width - 60, (len(meta_lines) * 14) + 16, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont(primary_font, 11)
        my = y + (len(meta_lines) * 14) + 4
        for ml in meta_lines:
            my -= 14
            c.drawString(40, my, ml)
        y -= (len(meta_lines) * 14) + 36

        # Scores Table
        all_scores = scores.get('all_scores', [])
        table_data = [["Gift", "Score"]] + [[g['gift'], str(g['score'])] for g in all_scores]
        table = Table(table_data, colWidths=[width * 0.6, width * 0.25])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), accent_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), primary_font),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#F3F6FA')]),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        tw, th = table.wrapOn(c, width - 80, y - 60)
        if y - th < 60:
            new_page()
        table.drawOn(c, 40, y - th)
        y -= th + 30

        # Top Gifts sections with summaries
        top_trunc = scores.get('top_gifts_truncated', [])
        summaries = {d.get('display_name'): d.get('short_summary') for d in definitions.values() if d.get('short_summary')}
        if top_trunc:
            c.setFont(primary_font, 14)
            if y < 100:
                new_page()
            c.drawString(40, y, 'Top Gifts (Truncated)')
            y -= 20
            for g in top_trunc:
                line = f"{g['gift']} – {g['score']}"
                c.setFont(primary_font, 12)
                if y < 70:
                    new_page()
                c.drawString(50, y, line)
                y -= 16
                summ = summaries.get(g['gift'])
                if summ:
                    write_wrapped(summ, font_size=10, leading=12, max_width=85)

        # Definitions
        c.setFont(primary_font, 14)
        if y < 100:
            new_page()
        c.drawString(40, y, 'Definitions')
        y -= 24
        for slug, d in definitions.items():
            name = d.get('display_name') or slug
            full_def = (d.get('full_definition','') or '').strip()
            c.setFont(primary_font, 12)
            if y < 70:
                new_page()
            c.setFillColor(accent_color)
            c.drawString(40, y, name)
            c.setFillColor(colors.black)
            y -= 16
            if full_def:
                write_wrapped(full_def, font_size=10, leading=12, max_width=90)

        draw_footer(page_num)
        c.save()
        buf.seek(0)
        return buf.read()
    # Fallback minimal PDF header (very naive) - NOT a fully valid PDF for complex viewers but works for simple tests / storage.
    pseudo = f"PSEUDO-PDF\n{full_text}".encode()
    return pseudo


def generate_html(apprentice_name: Optional[str], version: int, scores: Dict, definitions: Dict[str, Dict]) -> str:
    def esc(s: str) -> str:
        return (s or '').replace('<','&lt;').replace('>','&gt;')
    top_trunc = scores.get("top_gifts_truncated", [])
    top_expanded = scores.get("top_gifts_expanded", [])
    all_scores = scores.get("all_scores", [])
    head = f"<h1>Spiritual Gifts Assessment Report (v{version})</h1>"
    meta = f"<p>Apprentice: {esc(apprentice_name or 'Apprentice')}</p><p>Generated: {esc(datetime.utcnow().isoformat())}Z</p>"
    # Summaries map
    summaries = {d.get('display_name'): d.get('short_summary') for d in definitions.values() if d.get('short_summary')}
    def ul(items, include_summary=False):
        lis = []
        for i in items:
            summ = ''
            if include_summary and i['gift'] in summaries:
                summ = f" — {esc(summaries[i['gift']])}"
            lis.append(f"<li><strong>{esc(i['gift'])}</strong>: {i['score']}{summ}</li>")
        return '<ul>' + ''.join(lis) + '</ul>'
    defs_html = '<h2>Definitions</h2>' + ''.join([
        f"<h3>{esc(d.get('display_name') or slug)}</h3><p>{esc(d.get('full_definition',''))}</p>" for slug, d in definitions.items()
    ])
    html = f"<div style='font-family:Arial,sans-serif;'>{head}{meta}<h2>Top Gifts (Truncated)</h2>{ul(top_trunc, include_summary=True)}<h2>Top Gifts (Expanded)</h2>{ul(top_expanded)}<h2>All Gifts</h2>{ul(all_scores)}{defs_html}</div>"
    return html
