from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import uuid

from app.db import Base


class MentorResource(Base):
    __tablename__ = "mentor_resources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mentor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    apprentice_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    link_url = Column(Text, nullable=True)
    is_shared = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    mentor = relationship("User", foreign_keys=[mentor_id])
    apprentice = relationship("User", foreign_keys=[apprentice_id])
