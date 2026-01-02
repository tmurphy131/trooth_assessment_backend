from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MentorNoteBase(BaseModel):
    content: str
    follow_up_plan: Optional[str] = None
    is_private: bool = True


class MentorNoteCreate(MentorNoteBase):
    assessment_id: str


class MentorNoteUpdate(BaseModel):
    """Schema for updating an existing note. All fields optional."""
    content: Optional[str] = None
    follow_up_plan: Optional[str] = None
    is_private: Optional[bool] = None


class MentorNoteOut(MentorNoteBase):
    id: str
    assessment_id: str
    mentor_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {'from_attributes': True}
