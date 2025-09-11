from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MentorNoteBase(BaseModel):
    content: str
    follow_up_plan: Optional[str] = None
    is_private: bool = True


class MentorNoteCreate(MentorNoteBase):
    assessment_id: str


class MentorNoteOut(MentorNoteBase):
    id: str
    mentor_id: str
    created_at: datetime
    model_config = {'from_attributes': True}
