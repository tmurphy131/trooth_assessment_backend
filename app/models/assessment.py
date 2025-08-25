from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime
import uuid

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    apprentice_id = Column(String, ForeignKey("users.id"), nullable=False)
    # optional link to the template used to generate this assessment
    template_id = Column(String, ForeignKey("assessment_templates.id"), nullable=True)
    # answers can be empty for tests; default to empty JSON object
    answers = Column(JSON, nullable=True, default={})
    scores = Column(JSON, nullable=True)
    recommendation = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Relationship for score history entries
    score_history = relationship("AssessmentScoreHistory", back_populates="assessment", cascade="all, delete-orphan")
    # Relationship for mentor notes
    mentor_notes = relationship("MentorNote", back_populates="assessment", cascade="all, delete-orphan")
    # relationship to the owning apprentice user
    apprentice = relationship("User", back_populates="assessments")
    # optional relationship to its template
    template = relationship("AssessmentTemplate")
