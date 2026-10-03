from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

PrayerCategory = Literal["praise", "confession", "thanksgiving", "request", "intercession"]


class PrayerEntryBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    body: Optional[str] = Field(None, max_length=5000)
    category: PrayerCategory = "request"
    praying_for: Optional[str] = Field(None, max_length=120)
    scripture_ref: Optional[str] = Field(None, max_length=120)
    shared_with_mentor: bool = False


class PrayerEntryCreate(PrayerEntryBase):
    pass


class PrayerEntryUpdate(BaseModel):
    """Schema for updating an existing entry. All fields optional."""
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    body: Optional[str] = Field(None, max_length=5000)
    category: Optional[PrayerCategory] = None
    praying_for: Optional[str] = Field(None, max_length=120)
    scripture_ref: Optional[str] = Field(None, max_length=120)
    shared_with_mentor: Optional[bool] = None


class MarkAnswered(BaseModel):
    answer_note: Optional[str] = Field(None, max_length=5000)


class PrayerEntryOut(PrayerEntryBase):
    id: str
    apprentice_id: str
    answered_at: Optional[datetime] = None
    answer_note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {'from_attributes': True}
