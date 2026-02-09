from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
from app.schemas.user import UserCreate, UserOut
from app.models import user as user_model
from app.db import get_db
from app.services.auth import verify_token, require_roles, get_current_user
from app.services.account_deletion import get_account_deletion_summary, delete_user_account
from firebase_admin import auth, firestore
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
    # Get Firebase UID from the verified token (NOT from request body)
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(status_code=400, detail="Could not extract user ID from Firebase token")
    
    # Check if user already exists by email OR by Firebase UID
    existing_user = db.query(User).filter(
        (User.email == user.email) | (User.id == firebase_uid)
    ).first()
    if existing_user:
        # Update existing user to ensure consistency
        needs_update = False
        if existing_user.id != firebase_uid:
            existing_user.id = firebase_uid
            needs_update = True
        # Also update role if it was incorrectly set (e.g., by old auto-create code)
        if existing_user.role != user.role:
            existing_user.role = user.role
            needs_update = True
        if existing_user.name != user.name:
            existing_user.name = user.name
            needs_update = True
        if needs_update:
            db.commit()
            db.refresh(existing_user)
            # Update Firebase custom claims with correct role
            try:
                auth.set_custom_user_claims(firebase_uid, {"role": existing_user.role.value})
            except Exception:
                pass  # Non-critical, claims will be set eventually
        return existing_user

    # Create user with Firebase UID as the primary key
    db_user = user_model.User(
        id=firebase_uid,  # Use Firebase UID, not auto-generated UUID
        name=user.name,
        email=user.email,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    try:
        # Set Firebase custom claims with the correct Firebase UID
        auth.set_custom_user_claims(firebase_uid, {"role": db_user.role.value})
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
        
        # Perform the database deletion
        result = delete_user_account(db, current_user)
        
        # Delete the Firebase Authentication user
        firebase_auth_deleted = False
        firebase_auth_error = None
        try:
            auth.delete_user(user_id)
            firebase_auth_deleted = True
            logging.info(f"Successfully deleted Firebase Auth user {user_id}")
        except auth.UserNotFoundError:
            # User doesn't exist in Firebase Auth - this is fine
            firebase_auth_deleted = True
            logging.info(f"Firebase Auth user {user_id} already does not exist")
        except Exception as firebase_error:
            firebase_auth_error = str(firebase_error)
            logging.warning(f"Could not delete Firebase Auth user {user_id}: {firebase_error}")
        
        # Delete the Firestore user document (contains role, onboarded flag, etc.)
        firestore_deleted = False
        firestore_error = None
        try:
            db_firestore = firestore.client()
            # Delete from 'users' collection
            db_firestore.collection('users').document(user_id).delete()
            firestore_deleted = True
            logging.info(f"Successfully deleted Firestore user document {user_id}")
        except Exception as firestore_err:
            firestore_error = str(firestore_err)
            logging.warning(f"Could not delete Firestore user document {user_id}: {firestore_err}")
        
        return {
            "success": True,
            "message": f"Account {user_email} has been permanently deleted",
            "deleted_summary": summary["items_to_delete"],
            "deleted_counts": result["deleted_counts"],
            "firebase_auth_deleted": firebase_auth_deleted,
            "firebase_auth_error": firebase_auth_error,
            "firestore_deleted": firestore_deleted,
            "firestore_error": firestore_error
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete account: {str(e)}"
        )