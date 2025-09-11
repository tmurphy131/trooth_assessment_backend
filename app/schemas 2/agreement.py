from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime

# Enums represented as literals for now; could move to Enum types
AGREEMENT_STATUSES = {"draft", "awaiting_apprentice", "awaiting_parent", "fully_signed", "revoked", "expired"}
TOKEN_TYPES = {"apprentice", "parent"}

class AgreementTemplateCreate(BaseModel):
    markdown_source: str = Field(min_length=10)
    notes: Optional[str] = None
    is_active: bool = True

class AgreementTemplateOut(BaseModel):
    id: str
    version: int
    markdown_source: str
    created_at: datetime
    is_active: bool
    supersedes_version: Optional[int]
    notes: Optional[str]

    model_config = {
        'from_attributes': True
    }

class AgreementFieldValues(BaseModel):
    meeting_location: str
    meeting_duration_minutes: int
    meeting_day: Optional[str] = None
    meeting_time: Optional[str] = None
    meeting_frequency: Optional[str] = None
    start_date: Optional[str] = None
    additional_notes: Optional[str] = None

    @field_validator('meeting_duration_minutes')
    def duration_positive(cls, v):
        if v <= 0:
            raise ValueError('meeting_duration_minutes must be > 0')
        return v

class AgreementCreate(BaseModel):
    template_version: int
    apprentice_email: EmailStr
    apprentice_name: Optional[str] = None
    apprentice_is_minor: bool = False
    parent_required: bool = False
    parent_email: Optional[EmailStr] = None
    fields: AgreementFieldValues

    @field_validator('parent_email')
    def parent_email_required(cls, v, info):
        values = info.data
        if values.get('apprentice_is_minor') and not v:
            raise ValueError('parent_email required for minor apprentice')
        if values.get('parent_required') and not v:
            raise ValueError('parent_email required when parent_required is true')
        return v

class AgreementOut(BaseModel):
    id: str
    template_version: int
    mentor_id: str
    apprentice_id: Optional[str]
    apprentice_email: str
    apprentice_name: Optional[str] = None
    status: str
    apprentice_is_minor: bool
    parent_required: bool
    parent_email: Optional[str]
    fields_json: Dict[str, Any]
    content_rendered: Optional[str]
    content_hash: Optional[str]
    apprentice_signature_name: Optional[str]
    apprentice_signed_at: Optional[datetime]
    parent_signature_name: Optional[str]
    parent_signed_at: Optional[datetime]
    created_at: datetime
    activated_at: Optional[datetime]
    mentor_name: Optional[str] = None

    model_config = {
        'from_attributes': True
    }

class AgreementSubmit(BaseModel):
    pass  # no body; path+auth does transition

class AgreementSign(BaseModel):
    typed_name: str = Field(min_length=2, max_length=120)

class ParentTokenResend(BaseModel):
    reason: Optional[str] = Field(None, max_length=300)

class AgreementFieldsUpdate(BaseModel):
    """Partial update of draft fields for preview regeneration."""
    meeting_location: Optional[str] = None
    meeting_duration_minutes: Optional[int] = None
    meeting_day: Optional[str] = None
    meeting_time: Optional[str] = None
    meeting_frequency: Optional[str] = None
    start_date: Optional[str] = None
    additional_notes: Optional[str] = None

    @field_validator('meeting_duration_minutes')
    def duration_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('meeting_duration_minutes must be > 0')
        return v

class MeetingRescheduleRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)
    proposals: Optional[List[str]] = Field(default=None)

    class RescheduleResponse(BaseModel):
        decision: str  # accepted | declined | proposed
        selected_time: Optional[str] = None
        note: Optional[str] = None

