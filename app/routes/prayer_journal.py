from datetime import datetime, UTC
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.mentor_apprentice import MentorApprentice
from app.models.prayer_entry import PrayerEntry
from app.models.user import User
from app.schemas.prayer_entry import (
    MarkAnswered,
    PrayerCategory,
    PrayerEntryCreate,
    PrayerEntryOut,
    PrayerEntryUpdate,
)
from app.services.auth import require_apprentice, require_mentor

router = APIRouter(prefix="/prayer-journal", tags=["Prayer Journal"])


def _get_owned_entry(db: Session, entry_id: str, user: User) -> PrayerEntry:
    entry = db.query(PrayerEntry).filter_by(id=entry_id, apprentice_id=user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found or not owned by you")
    return entry


@router.get("/entries", response_model=list[PrayerEntryOut])
def list_entries(
    status: Optional[Literal["active", "answered"]] = None,
    category: Optional[PrayerCategory] = None,
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    query = db.query(PrayerEntry).filter(PrayerEntry.apprentice_id == current_user.id)
    if status == "active":
        query = query.filter(PrayerEntry.answered_at.is_(None))
    elif status == "answered":
        query = query.filter(PrayerEntry.answered_at.isnot(None))
    if category:
        query = query.filter(PrayerEntry.category == category)
    return query.order_by(PrayerEntry.created_at.desc()).all()


@router.post("/entries", response_model=PrayerEntryOut)
def create_entry(
    entry_data: PrayerEntryCreate,
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    entry = PrayerEntry(apprentice_id=current_user.id, **entry_data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/entries/{entry_id}", response_model=PrayerEntryOut)
def update_entry(
    entry_id: str,
    entry_data: PrayerEntryUpdate,
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    """Update an existing entry. Only the owner can edit their own entries."""
    entry = _get_owned_entry(db, entry_id, current_user)
    # exclude_unset lets the client clear optional fields by sending null
    for field, value in entry_data.model_dump(exclude_unset=True).items():
        if field in ("title", "category", "shared_with_mentor") and value is None:
            continue  # required columns can't be nulled
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: str,
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    entry = _get_owned_entry(db, entry_id, current_user)
    db.delete(entry)
    db.commit()
    return


@router.post("/entries/{entry_id}/answered", response_model=PrayerEntryOut)
def mark_answered(
    entry_id: str,
    data: MarkAnswered,
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    entry = _get_owned_entry(db, entry_id, current_user)
    entry.answered_at = datetime.now(UTC)
    entry.answer_note = data.answer_note
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}/answered", response_model=PrayerEntryOut)
def unmark_answered(
    entry_id: str,
    current_user: User = Depends(require_apprentice),
    db: Session = Depends(get_db)
):
    entry = _get_owned_entry(db, entry_id, current_user)
    entry.answered_at = None
    entry.answer_note = None
    db.commit()
    db.refresh(entry)
    return entry


# ============================================================================
# Mentor-facing endpoints (shared entries only)
# ============================================================================

@router.get("/mentor/apprentices/{apprentice_id}/entries", response_model=list[PrayerEntryOut])
def list_shared_entries_for_apprentice(
    apprentice_id: str,
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    """Entries the apprentice chose to share. Only active mentors of the apprentice can read them."""
    mapping = db.query(MentorApprentice).filter_by(
        mentor_id=current_user.id,
        apprentice_id=apprentice_id,
        active=True,
    ).first()
    if not mapping:
        raise HTTPException(status_code=403, detail="Not authorized")

    return db.query(PrayerEntry).filter(
        PrayerEntry.apprentice_id == apprentice_id,
        PrayerEntry.shared_with_mentor.is_(True),
    ).order_by(PrayerEntry.created_at.desc()).all()
