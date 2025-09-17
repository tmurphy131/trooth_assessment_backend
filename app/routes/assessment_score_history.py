from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.models.assessment_score_history import AssessmentScoreHistory
from app.schemas.assessment_score_history import AssessmentScoreHistoryOut
from app.services.auth import get_current_user, require_mentor
from app.schemas.user import UserSchema
from app.services.auth import require_mentor_or_admin

router = APIRouter()


@router.get("/assessments/{assessment_id}/history", response_model=List[AssessmentScoreHistoryOut])
def get_assessment_score_history(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(get_current_user)
):
    history = (
        db.query(AssessmentScoreHistory)
        .filter(AssessmentScoreHistory.assessment_id == str(assessment_id))
        .order_by(AssessmentScoreHistory.scored_at.desc())
        .all()
    )

    if not history:
        raise HTTPException(status_code=404, detail="No score history found")

    return history

@router.get("/users/{apprentice_id}/score-history", response_model=List[AssessmentScoreHistoryOut])
def get_score_history_for_apprentice(
    apprentice_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(require_mentor_or_admin)
):
    history = (
        db.query(AssessmentScoreHistory)
        .filter(AssessmentScoreHistory.apprentice_id == str(apprentice_id))
        .order_by(AssessmentScoreHistory.scored_at.desc())
        .all()
    )

    if not history:
        raise HTTPException(status_code=404, detail="No score history found for this apprentice.")

    return history
