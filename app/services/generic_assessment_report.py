from __future__ import annotations
from typing import Dict, Optional
import logging

logger = logging.getLogger("app.generic_report")

try:  # Optional PDF dependency
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas  # type: ignore
    from reportlab.lib import colors  # type: ignore
    _HAS_REPORTLAB = True
except Exception:  # pragma: no cover
    _HAS_REPORTLAB = False


def generate_html(title: str, apprentice_name: Optional[str], scores: Dict) -> str:
    cats = scores.get("categories", [])
    overall = scores.get("overall_score", 0)
    rows = "".join([f"<tr><td>{c.get('name')}</td><td>{c.get('score')}</td></tr>" for c in cats])
    return (
        f"<div style='font-family:Arial,sans-serif'>"
        f"<h1>{title or 'Assessment Report'}</h1>"
        f"<p>Apprentice: {apprentice_name or 'Apprentice'}</p>"
        f"<h2>Overall: {overall}</h2>"
        f"<table border='1' cellspacing='0' cellpadding='6'><thead><tr><th>Category</th><th>Score</th></tr></thead><tbody>{rows}</tbody></table>"
        f"</div>"
    )


def generate_pdf(title: str, apprentice_name: Optional[str], scores: Dict) -> bytes:
    if not _HAS_REPORTLAB:
        return ("PSEUDO-PDF\n" + generate_html(title, apprentice_name, scores)).encode()
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, title or "Assessment Report")
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 70, f"Apprentice: {apprentice_name or 'Apprentice'}")

    # Body
    y = height - 110
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"Overall: {scores.get('overall_score', 0)}")
    y -= 20
    c.setFont("Helvetica", 11)
    for cat in scores.get("categories", []):
        if y < 60:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)
        c.drawString(50, y, f"- {cat.get('name')}: {cat.get('score')}")
        y -= 16

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
