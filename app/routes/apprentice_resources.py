from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.mentor_resource import MentorResource
from app.models.user import User
from app.schemas.mentor_resource import MentorResourceOut
from app.services.auth import require_apprentice

router = APIRouter(prefix="/apprentice/resources", tags=["Apprentice Resources"])


@router.get("", response_model=list[MentorResourceOut])
def list_shared_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_apprentice)
):
    q = (
        db.query(MentorResource)
        .filter(
            MentorResource.apprentice_id == current_user.id,
            MentorResource.is_shared.is_(True)
        )
        .order_by(MentorResource.created_at.desc())
    )
    return q.all()
