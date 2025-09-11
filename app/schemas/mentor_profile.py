from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional


class MentorProfileIn(BaseModel):
    avatar_url: Optional[str] = None
    role_title: Optional[str] = None
    organization: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None

    @field_validator('avatar_url')
    def validate_url(cls, v: str | None):
        if v is None or v.strip() == "":
            return None
        # basic sanity; avoid strict HttpUrl due to data URIs or gs://
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('avatar_url must start with http(s)://')
        return v


class MentorProfileOut(BaseModel):
    user_id: str
    name: str | None = None
    email: str | None = None
    avatar_url: Optional[str] = None
    role_title: Optional[str] = None
    organization: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    updated_at: Optional[str] = None
