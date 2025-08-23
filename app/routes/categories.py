from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.category import Category
from app.models.user import User
from app.services.auth import get_current_user, require_mentor
from typing import List
import uuid

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("/", response_model=List[dict])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available assessment categories."""
    categories = db.query(Category).order_by(Category.name).all()
    return [{"id": cat.id, "name": cat.name} for cat in categories]

@router.post("/", response_model=dict)
def create_category(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    """Create a new assessment category (mentor only)."""
    # Check if category already exists
    existing = db.query(Category).filter_by(name=name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    category = Category(
        id=str(uuid.uuid4()),
        name=name
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return {"id": category.id, "name": category.name}

@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    """Delete a category (mentor only). Cannot delete if questions are using it."""
    category = db.query(Category).filter_by(id=category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if any questions use this category
    from app.models.question import Question
    questions_using = db.query(Question).filter_by(category_id=category_id).count()
    if questions_using > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete category. {questions_using} questions are using this category."
        )
    
    db.delete(category)
    db.commit()
    
    return {"message": "Category deleted successfully"}
