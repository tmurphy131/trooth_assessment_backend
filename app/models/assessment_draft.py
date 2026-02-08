from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime, UTC
import uuid

class AssessmentDraft(Base):
    __tablename__ = "assessment_drafts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    apprentice_id = Column(String, ForeignKey("users.id"), nullable=False)
    template_id = Column(String, ForeignKey("assessment_templates.id"), nullable=False)
    answers = Column(JSON, nullable=True)  # Store answers as JSON
    last_question_id = Column(String, ForeignKey("questions.id"), nullable=True)
    is_submitted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    score = Column(JSON, nullable=True)  # Stores scoring data as JSON dict
    answers_rel = relationship("AssessmentAnswer", cascade="all, delete-orphan", backref="draft")
