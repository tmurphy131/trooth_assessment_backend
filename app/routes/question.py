from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.category import Category
from app.models.question import Question, QuestionOption
from app.schemas.question import (
    CategoryCreate, QuestionCreate, QuestionUpdate, CategoryOut, QuestionOut
)
import logging
import uuid

from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.user import User, UserRole
from app.services.auth import get_current_user, require_admin, require_mentor_or_admin
from app.services.question_access import manage_block_reason, question_out

router = APIRouter()
logger = logging.getLogger(__name__)

_BLOCKED = {
    "not_owner": (403, "You can only {verb} questions you created."),
    "used_elsewhere": (409, "This question is used by other assessments, so it can't be {past}."),
}


def _ensure_can_manage(db: Session, user: User, question: Question, verb: str, past: str) -> None:
    """Mentors change only their own questions used solely by their own templates (spec 010)."""
    reason = manage_block_reason(db, user, question)
    if reason:
        status, detail = _BLOCKED[reason]
        logger.info("question %s refused question=%s user=%s reason=%s", verb, question.id, user.id, reason)
        raise HTTPException(status_code=status, detail=detail.format(verb=verb, past=past))

@router.post("/categories", response_model=CategoryOut, dependencies=[Depends(require_admin)])
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.post("/questions", response_model=QuestionOut)
def create_question(question: QuestionCreate, db: Session = Depends(get_db), user: User = Depends(require_mentor_or_admin)):
    # Mentors own what they write; admin-authored questions are shared (no creator)
    db_question = Question(
        text=question.text,
        question_type=question.question_type,
        category_id=question.category_id,
        created_by=user.id if user.role == UserRole.mentor else None,
        # question_code is NOT NULL + unique in the database (migration 20250915); generate one
        # for custom questions. "QC…" can't collide with seeded Q01..Q72 or QLEGACY codes.
        question_code=f"QC{uuid.uuid4().hex[:12].upper()}",
    )
    db.add(db_question)
    db.flush()  # Get the ID without committing
    
    # Add options if it's a multiple choice question
    if question.options:
        for option_data in question.options:
            db_option = QuestionOption(
                question_id=db_question.id,
                option_text=option_data.option_text,
                is_correct=option_data.is_correct,
                order=option_data.order
            )
            db.add(db_option)
    
    db.commit()
    db.refresh(db_question)
    return db_question

@router.get("/questions", response_model=list[QuestionOut], response_model_exclude_none=True)
def list_questions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [question_out(q, user) for q in db.query(Question).all()]

@router.get("/questions/{question_id}", response_model=QuestionOut, response_model_exclude_none=True)
def get_question(question_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question_out(question, user)

@router.put("/questions/{question_id}", response_model=QuestionOut)
def update_question(question_id: str, question_update: QuestionUpdate, db: Session = Depends(get_db),
                    user: User = Depends(require_mentor_or_admin)):
    db_question = db.query(Question).filter(Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    _ensure_can_manage(db, user, db_question, "edit", "changed")
    
    # Update question fields
    update_data = question_update.dict(exclude_unset=True, exclude={'options'})
    for field, value in update_data.items():
        setattr(db_question, field, value)
    
    # Handle options update
    if question_update.options is not None:
        # Delete existing options
        db.query(QuestionOption).filter(QuestionOption.question_id == question_id).delete()
        
        # Add new options
        for option_data in question_update.options:
            db_option = QuestionOption(
                question_id=question_id,
                option_text=option_data.option_text,
                is_correct=option_data.is_correct,
                order=option_data.order
            )
            db.add(db_option)
    
    db.commit()
    db.refresh(db_question)
    return db_question

@router.delete("/questions/{question_id}")
def delete_question(question_id: str, db: Session = Depends(get_db), user: User = Depends(require_mentor_or_admin)):
    db_question = db.query(Question).filter(Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    _ensure_can_manage(db, user, db_question, "delete", "deleted")

    # Detach from templates first (for a mentor these are all their own, per the check above)
    db.query(AssessmentTemplateQuestion).filter(AssessmentTemplateQuestion.question_id == question_id).delete()
    db.delete(db_question)  # Options will be deleted due to cascade
    db.commit()
    return {"message": "Question deleted successfully"}