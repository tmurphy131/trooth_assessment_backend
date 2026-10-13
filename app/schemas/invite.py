from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_serializer
from datetime import datetime

from app.services.invite_codes import format_invite_code

class InviteCreate(BaseModel):
    apprentice_email: EmailStr
    apprentice_name: str
    # mentor_id is now obtained from authentication, not from request

class InviteAccept(BaseModel):
    token: str
    # Optional; the apprentice is always the signed-in user. If sent, it must be theirs.
    apprentice_id: str | None = None

class InviteAcceptOut(BaseModel):
    message: str

class InviteCreatedOut(BaseModel):
    message: str
    id: str
    code: str
    expires_at: datetime

class InviteRedeem(BaseModel):
    code: str = Field(min_length=1, max_length=32)

class InviteRedeemOut(BaseModel):
    message: str
    mentor_id: str
    mentor_name: str | None = None
    relationship: Literal["created", "reactivated", "already_active"]

class InviteOut(BaseModel):
    id: str
    mentor_id: str | None = None
    mentor_name: str | None = None
    mentor_email: str | None = None
    apprentice_email: str
    apprentice_name: str
    token: str
    code: str | None = None
    expires_at: datetime
    accepted: bool
    model_config = {'from_attributes': True}

    @field_serializer("code")
    def _display_code(self, code: str | None) -> str | None:
        return format_invite_code(code)
