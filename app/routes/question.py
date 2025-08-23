from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.category import Category
from app.models.question import Question, QuestionOption
from app.schemas.question import (
    CategoryCreate, QuestionCreate, QuestionUpdate, CategoryOut, QuestionOut
)
from app.services.auth import require_mentor_or_admin

router = APIRouter()

@router.post("/categories", response_model=CategoryOut)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.post("/questions", response_model=QuestionOut, dependencies=[Depends(require_mentor_or_admin)])
def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    # Create the question
    db_question = Question(
        text=question.text,
        question_type=question.question_type,
        category_id=question.category_id
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

@router.get("/questions", response_model=list[QuestionOut])
def list_questions(db: Session = Depends(get_db)):
    return db.query(Question).all()

@router.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(question_id: str, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.put("/questions/{question_id}", response_model=QuestionOut, dependencies=[Depends(require_mentor_or_admin)])
def update_question(question_id: str, question_update: QuestionUpdate, db: Session = Depends(get_db)):
    db_question = db.query(Question).filter(Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    
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

@router.delete("/questions/{question_id}", dependencies=[Depends(require_mentor_or_admin)])
def delete_question(question_id: str, db: Session = Depends(get_db)):
    db_question = db.query(Question).filter(Question.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    db.delete(db_question)  # Options will be deleted due to cascade
    db.commit()
    return {"message": "Question deleted successfully"}