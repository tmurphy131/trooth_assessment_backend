from sqlalchemy.orm import Session
from app.models.assessment_score_history import AssessmentScoreHistory
from app.schemas.user import UserSchema
from datetime import datetime


def save_score_history(
    db: Session,
    assessment_id: str,
    apprentice_id: str,
    score_data: dict,
    triggered_by: str,
    model_used: str = "gpt-4",
    triggered_by_user_id: str = None,
    notes: str = None
) -> AssessmentScoreHistory:
    history = AssessmentScoreHistory(
        assessment_id=assessment_id,
        apprentice_id=apprentice_id,
        score_data=score_data,
        model_used=model_used,
        triggered_by=triggered_by,
        triggered_by_user_id=triggered_by_user_id,
        notes=notes
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history

