from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import base64, json

from app.db import get_db
from app.models.assessment import Assessment
from app.models.user import User
from app.services.auth import get_current_user
from app.services.ai_scoring_master import _extract_top3 as master_extract_top3

router = APIRouter(prefix="/progress", tags=["Progress"])


def _encode_cursor(created_at: datetime, assessment_id: str) -> str:
    payload = {"ts": created_at.isoformat(), "id": assessment_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(raw)
        return datetime.fromisoformat(data["ts"]), data["id"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cursor")


@router.get("/master/latest", summary="Featured card: latest Master (summary shape)")
def featured_master_latest(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    a = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == current_user.id, Assessment.category == "master_trooth")
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="No Master assessment found")
    scores = a.scores or {}
    # Derive fields according to spec
    overall = scores.get("overall_score")
    if overall is None:
        # fallback mean from category_scores if available
        cat = scores.get("category_scores") or {}
        if cat:
            overall = sum(int(v) for v in cat.values()) / max(len(cat), 1)
        else:
            overall = 0
    try:
        overall_float = float(overall)
    except Exception:
        overall_float = 0.0
    overall_display = int(round(overall_float))
    top3 = scores.get("top3")
    if not top3:
        cat = scores.get("category_scores") or {}
        if isinstance(cat, dict) and cat:
            top3 = master_extract_top3({str(k): int(v) for k, v in cat.items()})
        else:
            top3 = []
    version = scores.get("version") or "master_v1"
    return {
        "overall_score": overall_float,
        "overall_score_display": overall_display,
        "top3": top3,
        "completed_at": a.created_at,
        "version": version,
    }


@router.get("/spiritual-gifts/latest", summary="Featured card: latest Spiritual Gifts (summary shape)")
def featured_spiritual_gifts_latest(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    a = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == current_user.id, Assessment.category == "spiritual_gifts")
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="No spiritual gifts assessment found")
    scores = a.scores or {}
    # Prefer truncated top 3; fallback to expanded or all_scores
    top3 = scores.get("top_gifts_truncated") or scores.get("top_gifts_expanded") or scores.get("all_scores") or []
    # Ensure at most 3
    top3 = top3[:3]
    # Build version tag like spiritual_gifts_v1 if possible
    ver = scores.get("template_version") or scores.get("version") or 1
    try:
        version_tag = f"spiritual_gifts_v{int(ver)}"
    except Exception:
        version_tag = "spiritual_gifts_v1"
    return {
        "top_gifts_truncated": top3,
        "completed_at": a.created_at,
        "version": version_tag,
    }


@router.get("/reports")
def progress_reports(limit: int = 20, cursor: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if limit <= 0 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    base = db.query(Assessment).filter(Assessment.apprentice_id == current_user.id, Assessment.scores.isnot(None))
    if cursor:
        ts, aid = _decode_cursor(cursor)
        base = base.filter((Assessment.created_at < ts) | ((Assessment.created_at == ts) & (Assessment.id < aid)))
    rows = base.order_by(Assessment.created_at.desc(), Assessment.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    items: List[Dict[str, Any]] = []
    for a in rows:
        scores = a.scores or {}
        cat = (a.category or "other").lower()
        if cat == "master_trooth":
            assessment_type = "master"
            display_name = "Master T[root]H Assessment"
            # version is already a string in master scores (e.g., master_v1)
            version = scores.get("version") or "master_v1"
            # summary
            top3 = scores.get("top3")
            if not top3:
                c = scores.get("category_scores") or {}
                top3 = master_extract_top3({str(k): int(v) for k, v in c.items()}) if c else []
            overall = scores.get("overall_score")
            if overall is None:
                c = scores.get("category_scores") or {}
                overall = sum(int(v) for v in c.values()) / max(len(c), 1) if c else 0
            try:
                overall_float = float(overall)
            except Exception:
                overall_float = 0.0
            overall_display = int(round(overall_float))
            summary = {
                "overall_score": overall_display,
                "top3": top3,
            }
        elif cat == "spiritual_gifts":
            assessment_type = "spiritual_gifts"
            display_name = "Spiritual Gifts Assessment"
            ver = scores.get("template_version") or scores.get("version") or 1
            try:
                version = f"spiritual_gifts_v{int(ver)}"
            except Exception:
                version = "spiritual_gifts_v1"
            top3 = scores.get("top_gifts_truncated") or scores.get("top_gifts_expanded") or scores.get("all_scores") or []
            summary = {"top_gifts": top3[:3]}
        else:
            assessment_type = "other"
            display_name = "Assessment"
            version = scores.get("version") or "v1"
            # Attempt to create a minimal summary if known keys present
            if isinstance(scores, dict) and "category_scores" in scores:
                c = scores.get("category_scores") or {}
                top = master_extract_top3({str(k): int(v) for k, v in c.items()}) if c else []
                summary = {"top3": top[:3]}
            else:
                summary = {}

        items.append({
            "id": a.id,
            "assessment_type": assessment_type,
            "display_name": display_name,
            "completed_at": a.created_at,
            "version": version,
            "summary": summary,
        })

    next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
    return {"items": items, "next_cursor": next_cursor}
