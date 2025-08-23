from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app.models.user import User
from app.models.assessment import Assessment
from app.schemas.assessment import AssessmentOut
from app.services.auth import require_apprentice
from app.schemas.user import UserSchema

router = APIRouter(prefix="/apprentice", tags=["Apprentice"])


@router.get("/me", response_model=UserSchema)
def get_my_profile(current_user: User = Depends(require_apprentice)):
    return current_user


@router.get("/my-submitted-assessments", response_model=list[AssessmentOut])
def get_my_assessments(
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    assessments = (
        db.query(Assessment)
        .filter(Assessment.apprentice_id == current_user.id)
        .options(joinedload(Assessment.score_history))
        .order_by(Assessment.created_at.desc())
        .all()
    )
    return assessments


@router.get("/my-assessment/{assessment_id}", response_model=AssessmentOut)
def get_my_assessment_detail(
    assessment_id: str,
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    assessment = (
        db.query(Assessment)
        .filter_by(id=assessment_id, apprentice_id=current_user.id)
        .options(joinedload(Assessment.score_history))
        .first()
    )

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return assessment
