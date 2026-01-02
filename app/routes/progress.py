from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import base64, json
import logging

from app.db import get_db
from app.models.assessment import Assessment
from app.models.assessment_template import AssessmentTemplate
from app.models.user import User
from app.models.email_send_event import EmailSendEvent
from app.services.auth import get_current_user
from app.services.ai_scoring_master import _extract_top3 as master_extract_top3
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

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
    base = db.query(Assessment).options(joinedload(Assessment.template)).filter(Assessment.apprentice_id == current_user.id, Assessment.scores.isnot(None))
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
        # Get template info if available
        template_id = a.template_id
        template_name = a.template.name if a.template else None
        
        if cat == "master_trooth":
            assessment_type = "master"
            display_name = template_name or "Master T[root]H Discipleship"
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
            display_name = template_name or "Spiritual Gifts Assessment"
            ver = scores.get("template_version") or scores.get("version") or 1
            try:
                version = f"spiritual_gifts_v{int(ver)}"
            except Exception:
                version = "spiritual_gifts_v1"
            top3 = scores.get("top_gifts_truncated") or scores.get("top_gifts_expanded") or scores.get("all_scores") or []
            summary = {"top_gifts": top3[:3]}
        else:
            assessment_type = "other"
            display_name = template_name or "Assessment"
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
            "template_id": template_id,
            "template_name": template_name,
            "completed_at": a.created_at,
            "version": version,
            "summary": summary,
        })

    next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
    return {"items": items, "next_cursor": next_cursor}


@router.get("/reports/{assessment_id}/simplified", response_model=dict)
def get_apprentice_simplified_report(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """GET /progress/reports/{assessment_id}/simplified
    
    Returns a simplified report for the apprentice's own assessment.
    Same structure as mentor simplified report but for self-service.
    
    Response structure:
    - health_score: int (0-100)
    - health_band: str (e.g., "Maturing", "Growing", "Excellent")
    - strengths: list[str] (top 3)
    - gaps: list[str] (top 3)
    - priority_action: {title, description, scripture}
    - flags: {red: [], yellow: [], green: []}
    - biblical_knowledge: {percent: float, topics: [{topic, correct, total}]}
    - insights: [{category, level, observation, next_step}]
    - conversation_starters: list[str]
    - mc_percent: float
    - assessment_type: str
    - template_name: str
    - completed_at: datetime
    """
    # Fetch assessment with template
    assessment = db.query(Assessment).options(joinedload(Assessment.template)).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
    
    # Verify the assessment belongs to the current user
    if assessment.apprentice_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this assessment")
    
    # Extract mentor_report_v2 blob and scores
    mentor_blob = assessment.mentor_report_v2 or {}
    scores = assessment.scores or {}
    
    # Get template info
    template_name = assessment.template.name if assessment.template else None
    cat = (assessment.category or "other").lower()
    
    if cat == "master_trooth":
        assessment_type = "master"
        display_name = template_name or "Master T[root]H Discipleship"
    elif cat == "spiritual_gifts":
        assessment_type = "spiritual_gifts"
        display_name = template_name or "Spiritual Gifts Assessment"
    else:
        assessment_type = "other"
        display_name = template_name or "Assessment"
    
    # Detect v2.1 format (has health_score at top level) vs legacy format
    is_v21 = 'health_score' in mentor_blob
    
    if is_v21:
        # v2.1 format
        health_score = int(mentor_blob.get('health_score', 0))
        health_band = mentor_blob.get('health_band', 'Unknown')
        strengths = mentor_blob.get('strengths', [])[:3]
        gaps = mentor_blob.get('gaps', [])[:3]
        priority_action = mentor_blob.get('priority_action', {})
        flags = mentor_blob.get('flags', {'red': [], 'yellow': [], 'green': []})
        insights = mentor_blob.get('insights', [])
        conversation_starters = mentor_blob.get('conversation_starters', [])
        trend_note = mentor_blob.get('trend_note')
        
        # Biblical knowledge from MC topics
        mc_topics = mentor_blob.get('mc_topics', [])
        mc_percent = mentor_blob.get('mc_percent', 0.0)
        biblical_knowledge = {
            'percent': mc_percent,
            'topics': mc_topics
        }
        
        # Recommended resources
        resources = mentor_blob.get('resources', [])
    else:
        # Legacy v2.0 format or scores-only
        snapshot = mentor_blob.get('snapshot', {})
        health_score = int(snapshot.get('overall_mc_percent', 0)) if snapshot else 0
        health_band = snapshot.get('knowledge_band', 'Unknown') if snapshot else 'Unknown'
        
        # Extract from category_breakdown if available
        category_breakdown = mentor_blob.get('category_breakdown', {})
        strengths = []
        gaps = []
        for cat_name, cat_data in category_breakdown.items():
            if isinstance(cat_data, dict):
                if cat_data.get('mc_percent', 0) >= 80:
                    strengths.append(cat_name)
                elif cat_data.get('mc_percent', 0) < 50:
                    gaps.append(cat_name)
        strengths = strengths[:3]
        gaps = gaps[:3]
        
        # Priority action from first action if available
        actions = mentor_blob.get('action_items', [])
        priority_action = actions[0] if actions else {}
        
        flags = mentor_blob.get('flags', {'red': [], 'yellow': [], 'green': []})
        insights = mentor_blob.get('open_ended_insights', [])
        conversation_starters = mentor_blob.get('conversation_starters', [])
        trend_note = mentor_blob.get('trend_note')
        
        biblical_knowledge = {
            'percent': snapshot.get('overall_mc_percent', 0) if snapshot else 0,
            'topics': []
        }
        mc_percent = snapshot.get('overall_mc_percent', 0) if snapshot else 0
        resources = []
    
    return {
        "health_score": health_score,
        "health_band": health_band,
        "strengths": strengths,
        "gaps": gaps,
        "priority_action": priority_action,
        "flags": flags,
        "biblical_knowledge": biblical_knowledge,
        "insights": insights,
        "conversation_starters": conversation_starters,
        "trend_note": trend_note,
        "mc_percent": mc_percent,
        "resources": resources if is_v21 else [],
        "assessment_type": assessment_type,
        "template_name": display_name,
        "template_id": assessment.template_id,
        "completed_at": assessment.created_at,
    }


@router.delete("/reports/{assessment_id}", status_code=204)
def delete_assessment_report(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """DELETE /progress/reports/{assessment_id}
    
    Deletes a completed assessment report. Only the apprentice who owns the assessment
    can delete it. This action cannot be undone.
    """
    # Fetch the assessment
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
    
    # Verify the assessment belongs to the current user (apprentice)
    if assessment.apprentice_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this assessment")
    
    # Log for audit purposes
    logger.info(
        f"Apprentice {current_user.id} ({current_user.email}) deleting assessment {assessment_id} "
        f"(category: {assessment.category}, template_id: {assessment.template_id})"
    )
    
    # Clear foreign key references before deleting
    # 1. Set assessment_id to NULL on email_send_events that reference this assessment
    db.query(EmailSendEvent).filter(EmailSendEvent.assessment_id == assessment_id).update(
        {"assessment_id": None}, synchronize_session=False
    )
    
    # 2. Set previous_assessment_id to NULL on assessments that reference this one
    db.query(Assessment).filter(Assessment.previous_assessment_id == assessment_id).update(
        {"previous_assessment_id": None}, synchronize_session=False
    )
    
    # Delete the assessment (cascade will handle score_history and mentor_notes)
    db.delete(assessment)
    db.commit()
    
    return None
