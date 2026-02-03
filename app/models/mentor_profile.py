from sqlalchemy import Column, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import uuid

from app.db import Base


class MentorProfile(Base):
    __tablename__ = "mentor_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True, unique=True)

    avatar_url = Column(String, nullable=True)
    role_title = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    bio = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('user_id', name='uq_mentor_profile_user_id'),
    )
