from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.db import get_db
from app.models.user import User
from app.models.mentor_apprentice import MentorApprentice
from app.models.mentor_profile import MentorProfile
from app.schemas.mentor_profile import MentorProfileIn, MentorProfileOut
from app.services.auth import require_mentor, require_apprentice

router = APIRouter(prefix="/mentor-profile", tags=["Mentor Profile"])


@router.get("/me", response_model=MentorProfileOut)
def get_my_profile(current_user: User = Depends(require_mentor), db: Session = Depends(get_db)):
    prof = db.query(MentorProfile).filter_by(user_id=current_user.id).first()
    if not prof:
        # return minimal scaffold using user base info
        return MentorProfileOut(
            user_id=current_user.id,
            name=current_user.name,
            email=current_user.email,
            avatar_url=None,
            role_title=None,
            organization=None,
            phone=None,
            bio=None,
            updated_at=None,
        )
    return MentorProfileOut(
        user_id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        avatar_url=prof.avatar_url,
        role_title=prof.role_title,
        organization=prof.organization,
        phone=prof.phone,
        bio=prof.bio,
        updated_at=prof.updated_at.isoformat() if prof.updated_at else None,
    )


@router.put("/me", response_model=MentorProfileOut)
def update_my_profile(
    payload: MentorProfileIn,
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    prof = db.query(MentorProfile).filter_by(user_id=current_user.id).first()
    if not prof:
        prof = MentorProfile(user_id=current_user.id)
        db.add(prof)

    # Apply patch
    prof.avatar_url = payload.avatar_url if payload.avatar_url is not None else prof.avatar_url
    prof.role_title = payload.role_title if payload.role_title is not None else prof.role_title
    prof.organization = payload.organization if payload.organization is not None else prof.organization
    prof.phone = payload.phone if payload.phone is not None else prof.phone
    prof.bio = payload.bio if payload.bio is not None else prof.bio
    prof.updated_at = datetime.utcnow()

    db.add(prof)
    db.commit()
    db.refresh(prof)

    return MentorProfileOut(
        user_id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        avatar_url=prof.avatar_url,
        role_title=prof.role_title,
        organization=prof.organization,
        phone=prof.phone,
        bio=prof.bio,
        updated_at=prof.updated_at.isoformat() if prof.updated_at else None,
    )


@router.get("/for-apprentice", response_model=MentorProfileOut)
def get_profile_for_apprentice(
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    # Find active mentor link
    link = db.query(MentorApprentice).filter_by(apprentice_id=current_user.id, active=True).first()
    if not link:
        raise HTTPException(status_code=404, detail="No active mentor")
    mentor = db.query(User).filter_by(id=link.mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")
    prof = db.query(MentorProfile).filter_by(user_id=mentor.id).first()
    return MentorProfileOut(
        user_id=mentor.id,
        name=mentor.name,
        email=mentor.email,
        avatar_url=prof.avatar_url if prof else None,
        role_title=prof.role_title if prof else None,
        organization=prof.organization if prof else None,
        phone=prof.phone if prof else None,
        bio=prof.bio if prof else None,
        updated_at=prof.updated_at.isoformat() if prof and prof.updated_at else None,
    )
