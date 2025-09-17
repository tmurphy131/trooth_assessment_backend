"""Master Trooth report generation utilities (PDF/HTML).

Uses ReportLab if available; otherwise produces simple bytes/HTML for tests and emails.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime
import logging

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
