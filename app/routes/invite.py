from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.db import get_db
from app.models.user import User
from app.models.mentor_apprentice import MentorApprentice
from app.models.apprentice_invitation import ApprenticeInvitation
from app.schemas.invite import InviteCreate, InviteAccept, InviteOut
from app.services.email import send_invitation_email
from app.exceptions import NotFoundException
from app.exceptions import ValidationException
from app.services.auth import require_mentor, get_current_user


router = APIRouter()

@router.post("/invite-apprentice")
def invite_apprentice(
    invite: InviteCreate, 
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    # Use the authenticated mentor's ID instead of trusting the request
    mentor_id = current_user.id
    
    existing = db.query(ApprenticeInvitation).filter(
        ApprenticeInvitation.apprentice_email == invite.apprentice_email,
        ApprenticeInvitation.mentor_id == mentor_id,
        ApprenticeInvitation.accepted == False,
        ApprenticeInvitation.expires_at > datetime.utcnow()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="An invitation is already pending for this apprentice")

    token = str(uuid.uuid4())
    invitation = ApprenticeInvitation(
        mentor_id=mentor_id,
        apprentice_email=invite.apprentice_email,
        apprentice_name=invite.apprentice_name,
        token=token
    )
    db.add(invitation)
    db.commit()

    # Send invitation email
    try:
        email_sent = send_invitation_email(
            to_email=invite.apprentice_email, 
            apprentice_name=invite.apprentice_name, 
            token=token,
            mentor_name=current_user.name or current_user.email or "Your Mentor"
        )
        if not email_sent:
            # Log the failure but don't fail the invitation creation
            print(f"Warning: Failed to send invitation email to {invite.apprentice_email}")
    except Exception as e:
        # Log the failure but don't fail the invitation creation
        print(f"Error sending invitation email: {e}")
    
    return {"message": "Invitation sent"}

@router.get("/pending-invites", response_model=list[InviteOut])
def get_pending_invites(
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    """Get all pending invitations sent by the current mentor."""
    invitations = db.query(ApprenticeInvitation).filter(
        ApprenticeInvitation.mentor_id == current_user.id,
        ApprenticeInvitation.accepted == False,
        ApprenticeInvitation.expires_at > datetime.utcnow()
    ).all()
    return invitations

@router.delete("/revoke-invite/{invitation_id}")
def revoke_invite(
    invitation_id: str,
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    """Revoke a pending invitation."""
    invitation = db.query(ApprenticeInvitation).filter(
        ApprenticeInvitation.id == invitation_id,
        ApprenticeInvitation.mentor_id == current_user.id,
        ApprenticeInvitation.accepted == False
    ).first()
    
    if not invitation:
        raise NotFoundException("Invitation not found or cannot be revoked")
    
    db.delete(invitation)
    db.commit()
    return {"message": "Invitation revoked"}

@router.get("/validate-token/{token}")
def validate_invitation_token(token: str, db: Session = Depends(get_db)):
    """Validate an invitation token and return invitation details."""
    invitation = db.query(ApprenticeInvitation).filter_by(token=token).first()
    
    if not invitation:
        raise NotFoundException("Invalid invitation token")
    
    if invitation.expires_at < datetime.utcnow():
        raise ValidationException("This invitation has expired")
    
    if invitation.accepted:
        raise ValidationException("This invitation has already been accepted")
    
    # Get mentor details
    mentor = db.query(User).filter_by(id=invitation.mentor_id).first()
    
    return {
        "invitation_id": invitation.id,
        "mentor_name": mentor.name if mentor else "Unknown Mentor",
        "mentor_email": mentor.email if mentor else "Unknown",
        "apprentice_name": invitation.apprentice_name,
        "apprentice_email": invitation.apprentice_email,
        "expires_at": invitation.expires_at
    }


@router.post("/accept-invite")
def accept_invite(data: InviteAccept, db: Session = Depends(get_db)):
    invitation = db.query(ApprenticeInvitation).filter_by(token=data.token).first()
    if not invitation:
        raise HTTPException(status_code=400, detail="Invitation is invalid or expired")
    if invitation.expires_at < datetime.utcnow():
        raise ValidationException("This invitation has expired.")

    if invitation.accepted:
        raise HTTPException(status_code=400, detail="Invitation has already been accepted")

    # Check if apprentice user exists
    apprentice = db.query(User).filter_by(id=data.apprentice_id, role="apprentice").first()
    if not apprentice:
        raise NotFoundException("Apprentice not found")

    # Check if the mentor-apprentice relationship already exists (e.g., from a signed agreement)
    existing_relationship = db.query(MentorApprentice).filter(
        MentorApprentice.mentor_id == invitation.mentor_id,
        MentorApprentice.apprentice_id == data.apprentice_id
    ).first()

    invitation.accepted = True
    
    if existing_relationship:
        # Relationship already exists (likely from agreement signing), just mark invitation as accepted
        db.commit()
        return {"message": "Invitation accepted, relationship already exists"}
    
    # Create new relationship
    relationship = MentorApprentice(
        mentor_id=invitation.mentor_id,
        apprentice_id=data.apprentice_id
    )
    db.add(relationship)
    db.commit()

    return {"message": "Invitation accepted, relationship created"}


@router.get("/apprentice-invites", response_model=list[InviteOut])
def get_apprentice_invites(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all pending invitations for a specific apprentice email."""
    
    # Verify the apprentice is requesting their own invites
    if current_user.email != email:
        raise HTTPException(status_code=403, detail="You can only view your own invitations")
    
    invitations = db.query(ApprenticeInvitation).filter(
        ApprenticeInvitation.apprentice_email == email,
        ApprenticeInvitation.accepted == False,
        ApprenticeInvitation.expires_at > datetime.utcnow()
    ).all()
    
    # Enrich with mentor details
    result = []
    for invitation in invitations:
        mentor = db.query(User).filter_by(id=invitation.mentor_id).first()
        result.append({
            "id": invitation.id,
            "mentor_id": invitation.mentor_id,
            "mentor_name": mentor.name if mentor else "Unknown Mentor",
            "mentor_email": mentor.email if mentor else "Unknown",
            "apprentice_name": invitation.apprentice_name,
            "apprentice_email": invitation.apprentice_email,
            "token": invitation.token,
            "expires_at": invitation.expires_at,
            "accepted": invitation.accepted
        })
    
    return result