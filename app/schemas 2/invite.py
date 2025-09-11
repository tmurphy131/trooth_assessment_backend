from pydantic import BaseModel, EmailStr
from datetime import datetime

class InviteCreate(BaseModel):
    apprentice_email: EmailStr
    apprentice_name: str
    # mentor_id is now obtained from authentication, not from request

class InviteAccept(BaseModel):
    token: str
    apprentice_id: str

class InviteOut(BaseModel):
    id: str
    apprentice_email: str
    apprentice_name: str
    token: str
    expires_at: datetime
    accepted: bool
    model_config = {'from_attributes': True}