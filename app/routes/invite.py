from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, UTC
import uuid
import os

from app.db import get_db
from app.models.user import User
from app.models.mentor_apprentice import MentorApprentice
from app.models.apprentice_invitation import ApprenticeInvitation
from app.schemas.invite import InviteCreate, InviteAccept, InviteOut
from app.services.email import send_invitation_email
from app.exceptions import NotFoundException
from app.exceptions import ValidationException
from app.services.auth import require_mentor, get_current_user
from app.core.settings import settings


router = APIRouter()

# Set up templates
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/accept-invitation", response_class=HTMLResponse)
def accept_invitation_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """Landing page for email invitation links.
    
    Shows invitation details and links to download the app.
    """
    logo_url = getattr(settings, 'logo_url', 'https://onlyblv.com/onlyblv_logo.png')
    ios_app_store_url = getattr(settings, 'ios_app_store_url', 'https://apps.apple.com/app/t-root-h-discipleship/id6757311543')
    play_store_url = "https://play.google.com/store/apps/details?id=com.trooth.flutterTroothAssessment"
    
    # Look up the invitation
    invitation = db.query(ApprenticeInvitation).filter_by(token=token).first()
    
    if not invitation:
        return templates.TemplateResponse(
            "invitations/accept_invitation.html",
            {
                "request": request,
                "error": True,
                "error_title": "Invitation Not Found",
                "error_message": "This invitation link is invalid. Please check the link or contact your mentor for a new invitation.",
                "logo_url": logo_url,
                "ios_app_store_url": ios_app_store_url,
            }
        )
    
    if invitation.expires_at < datetime.now(UTC).replace(tzinfo=None):
        return templates.TemplateResponse(
            "invitations/accept_invitation.html",
            {
                "request": request,
                "error": True,
                "error_title": "Invitation Expired",
                "error_message": "This invitation has expired. Please ask your mentor to send a new invitation.",
                "logo_url": logo_url,
                "ios_app_store_url": ios_app_store_url,
            }
        )
    
    if invitation.accepted:
        return templates.TemplateResponse(
            "invitations/accept_invitation.html",
            {
                "request": request,
                "error": True,
                "error_title": "Already Accepted",
                "error_message": "This invitation has already been accepted. Open the T[root]H app to continue your journey.",
                "logo_url": logo_url,
                "ios_app_store_url": ios_app_store_url,
            }
        )
    
    # Get mentor details
    mentor = db.query(User).filter_by(id=invitation.mentor_id).first()
    mentor_name = mentor.name if mentor and mentor.name else (mentor.email if mentor else "Your Mentor")
    
    return templates.TemplateResponse(
        "invitations/accept_invitation.html",
        {
            "request": request,
            "error": False,
            "apprentice_name": invitation.apprentice_name or "Friend",
            "apprentice_email": invitation.apprentice_email,
            "mentor_name": mentor_name,
            "token": token,
            "logo_url": logo_url,
            "ios_app_store_url": ios_app_store_url,
            "play_store_url": play_store_url,
        }
    )


@router.post("/invite-apprentice")
def invite_apprentice(
    invite: InviteCreate, 
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    # Use the authenticated mentor's ID instead of trusting the request
    mentor_id = current_user.id
    
    # Lowercase email to match Firebase storage
    apprentice_email = invite.apprentice_email.lower().strip()
    
    existing = db.query(ApprenticeInvitation).filter(
        ApprenticeInvitation.apprentice_email == apprentice_email,
        ApprenticeInvitation.mentor_id == mentor_id,
        ApprenticeInvitation.accepted == False,
        ApprenticeInvitation.expires_at > datetime.now(UTC)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="An invitation is already pending for this apprentice")

    token = str(uuid.uuid4())
    invitation = ApprenticeInvitation(
        mentor_id=mentor_id,
        apprentice_email=apprentice_email,
        apprentice_name=invite.apprentice_name,
        token=token
    )
    db.add(invitation)
    db.commit()

    # Send invitation email
    try:
        email_sent = send_invitation_email(
            to_email=apprentice_email, 
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
        ApprenticeInvitation.expires_at > datetime.now(UTC)
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
    
    if invitation.expires_at < datetime.now(UTC).replace(tzinfo=None):
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
    # Compare as naive datetimes (DB stores naive, so strip tz from now())
    if invitation.expires_at < datetime.now(UTC).replace(tzinfo=None):
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
        ApprenticeInvitation.expires_at > datetime.now(UTC)
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