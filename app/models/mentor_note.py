from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base
import uuid

class MentorNote(Base):
    __tablename__ = "mentor_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    mentor_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    follow_up_plan = Column(Text, nullable=True)
    is_private = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assessment = relationship("Assessment", back_populates="mentor_notes")
    # link back to the User that authored the note
    mentor = relationship("User", back_populates="mentor_notes")
