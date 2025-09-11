from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.mentor_resource import MentorResource
from app.models.user import User
from app.schemas.mentor_resource import MentorResourceCreate, MentorResourceUpdate, MentorResourceOut
from app.services.auth import require_mentor

router = APIRouter(prefix="/mentor/resources", tags=["Mentor Resources"])


@router.post("", response_model=MentorResourceOut)
def create_resource(
    payload: MentorResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    mr = MentorResource(
        mentor_id=current_user.id,
        apprentice_id=payload.apprentice_id,
        title=payload.title,
        description=payload.description,
        link_url=str(payload.link_url) if payload.link_url else None,
        is_shared=payload.is_shared,
    )
    db.add(mr)
    db.commit()
    db.refresh(mr)
    return mr


@router.get("", response_model=list[MentorResourceOut])
def list_resources(
    apprentice_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    q = db.query(MentorResource).filter(MentorResource.mentor_id == current_user.id)
    if apprentice_id:
        q = q.filter(MentorResource.apprentice_id == apprentice_id)
    return q.order_by(MentorResource.created_at.desc()).all()


@router.patch("/{resource_id}", response_model=MentorResourceOut)
def update_resource(
    resource_id: str,
    payload: MentorResourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    mr = db.query(MentorResource).filter_by(id=resource_id, mentor_id=current_user.id).first()
    if not mr:
        raise HTTPException(status_code=404, detail="Not found")
    data = payload.model_dump(exclude_unset=True)
    if 'link_url' in data and data['link_url'] is not None:
        data['link_url'] = str(data['link_url'])
    for k, v in data.items():
        setattr(mr, k, v)
    db.add(mr)
    db.commit()
    db.refresh(mr)
    return mr


@router.delete("/{resource_id}")
def delete_resource(
    resource_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    mr = db.query(MentorResource).filter_by(id=resource_id, mentor_id=current_user.id).first()
    if not mr:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(mr)
    db.commit()
    return {"deleted": True}
