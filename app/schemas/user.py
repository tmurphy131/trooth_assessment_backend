from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum

class RoleEnum(str, Enum):
    apprentice = "apprentice"
    mentor = "mentor"
    admin = "admin"

from datetime import datetime
from app.models.user import UserRole
from app.core.security import SecurityMixin

class UserBase(BaseModel, SecurityMixin):
    name: str
    email: str

class UserCreate(UserBase):
    role: UserRole

    @field_validator('email')
    def validate_email_format(cls, v: str):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()

class UserOut(UserBase):
    id: str
    role: UserRole
    created_at: Optional[datetime]

    # Pydantic v2 style configuration
    model_config = {
        'from_attributes': True
    }

class UserUpdate(BaseModel, SecurityMixin):
    name: Optional[str] = None
    email: Optional[str] = None

    @field_validator('email')
    def validate_email_format(cls, v: str | None):
        if v is not None:
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, v):
                raise ValueError('Invalid email format')
            return v.lower()
        return v

class UserSchema(BaseModel):
    id: str
    name: str
    email: str
    role: str

    model_config = {
        'from_attributes': True
    }
