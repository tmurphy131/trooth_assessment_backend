from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut
from app.models import user as user_model
from app.db import get_db
from app.services.auth import verify_token, require_roles, get_current_user
from firebase_admin import auth
from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User
from app.exceptions import NotFoundException

router = APIRouter()

@router.post("/assign-apprentice")
def assign_apprentice(mentor_id: str, apprentice_id: str, db: Session = Depends(get_db)):
    mentor = db.query(User).filter_by(id=mentor_id, role="mentor").first()
    if not mentor:
        raise NotFoundException("Mentor not found")

    apprentice = db.query(User).filter_by(id=apprentice_id, role="apprentice").first()
    if not apprentice:
        raise NotFoundException("Apprentice not found")

    relationship = MentorApprentice(mentor_id=mentor_id, apprentice_id=apprentice_id)
    db.add(relationship)
    db.commit()
    return {"message": "Apprentice assigned successfully"}

@router.post("/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db), decoded_token=Depends(verify_token)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        return existing_user

    db_user = user_model.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    try:
        # user is the input schema (UserCreate) and doesn't have an id yet.
        # Use the persisted db_user's id and role when assigning Firebase claims.
        auth.set_custom_user_claims(db_user.id, {"role": db_user.role})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning Firebase role: {str(e)}")

    return db_user

@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(user_id: str, db: Session = Depends(get_db), decoded_token=Depends(verify_token)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    # get_current_user handles token verification & user retrieval
    return current_user

@router.get("/admin-only")
def test_admin_only(decoded_token=Depends(require_roles(["admin"]))):
    return {"message": f"Access granted for admin: {decoded_token.get('email')}"}