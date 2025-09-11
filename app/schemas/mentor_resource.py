from pydantic import BaseModel, AnyHttpUrl, Field
from typing import Optional
from datetime import datetime


class MentorResourceCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    apprentice_id: Optional[str] = None
    link_url: Optional[AnyHttpUrl] = None
    is_shared: bool = False


class MentorResourceUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    apprentice_id: Optional[str] = None
    link_url: Optional[AnyHttpUrl] = None
    is_shared: Optional[bool] = None


class MentorResourceOut(BaseModel):
    id: str
    mentor_id: str
    apprentice_id: Optional[str]
    title: str
    description: Optional[str]
    link_url: Optional[str]
    is_shared: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {
        'from_attributes': True
    }
