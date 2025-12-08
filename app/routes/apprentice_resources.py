from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.mentor_resource import MentorResource
from app.models.user import User
from app.schemas.mentor_resource import MentorResourceOut
from app.services.auth import require_apprentice
from app.models.mentor_apprentice import MentorApprentice

router = APIRouter(prefix="/apprentice/resources", tags=["Apprentice Resources"])


@router.get("", response_model=list[MentorResourceOut])
def list_shared_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_apprentice)
):
    # Find mentors linked to this apprentice
    mentor_ids = [row.mentor_id for row in db.query(MentorApprentice).filter_by(apprentice_id=current_user.id, active=True).all()]
    q = (
        db.query(MentorResource)
        .filter(
            MentorResource.is_shared.is_(True),
            (
                # Resources explicitly targeted to this apprentice
                (MentorResource.apprentice_id == current_user.id)
            ) | (
                # Or mentor-global resources (apprentice_id is NULL) from my mentors
                ((MentorResource.apprentice_id.is_(None)) & (MentorResource.mentor_id.in_(mentor_ids) if mentor_ids else False))
            )
        )
        .order_by(MentorResource.created_at.desc())
    )
    return q.all()
