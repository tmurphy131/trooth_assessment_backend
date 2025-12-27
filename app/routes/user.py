from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.schemas.user import UserCreate, UserOut
from app.models import user as user_model
from app.db import get_db
from app.services.auth import verify_token, require_roles, get_current_user
from app.services.account_deletion import get_account_deletion_summary, delete_user_account
from firebase_admin import auth
from app.models.mentor_apprentice import MentorApprentice
from app.models.user import User
from app.exceptions import NotFoundException

router = APIRouter()


class DeleteAccountRequest(BaseModel):
    """Request body for account deletion - requires explicit confirmation"""
    confirmation_text: str  # Must be "DELETE" to proceed

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


@router.get("/me/deletion-summary")
def get_deletion_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a summary of what will be deleted when the account is closed.
    Returns counts of all associated data so the user understands the impact.
    """
    return get_account_deletion_summary(db, current_user)


@router.delete("/me/close-account")
def close_account(
    request: DeleteAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Permanently delete the current user's account and all associated data.
    
    This is an IRREVERSIBLE operation that will:
    - For Apprentices: Delete all assessments, drafts, agreements, shared resources, and mentor relationships
    - For Mentors: Delete all agreements, invitations, resources, notes, and apprentice relationships
    
    Requires confirmation_text to be exactly "DELETE" to proceed.
    """
    # Verify confirmation
    if request.confirmation_text != "DELETE":
        raise HTTPException(
            status_code=400,
            detail="Confirmation text must be exactly 'DELETE' to proceed with account deletion"
        )
    
    # Don't allow admins to delete their accounts through this endpoint
    role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin accounts cannot be deleted through this endpoint"
        )
    
    try:
        # Get summary before deletion for logging
        summary = get_account_deletion_summary(db, current_user)
        user_email = current_user.email
        user_id = current_user.id
        
        # Perform the deletion
        result = delete_user_account(db, current_user)
        
        # Try to delete the Firebase user as well (optional - may fail if not exists)
        try:
            auth.delete_user(user_id)
        except Exception as firebase_error:
            # Log but don't fail - the database deletion is the primary concern
            import logging
            logging.warning(f"Could not delete Firebase user {user_id}: {firebase_error}")
        
        return {
            "success": True,
            "message": f"Account {user_email} has been permanently deleted",
            "deleted_summary": summary["items_to_delete"],
            "deleted_counts": result["deleted_counts"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete account: {str(e)}"
        )