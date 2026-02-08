from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db import Base
import uuid

class AssessmentScoreHistory(Base):
    __tablename__ = "assessment_score_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    apprentice_id = Column(String, ForeignKey("users.id"), nullable=False)
    scored_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    score_data = Column(JSON, nullable=False)
    model_used = Column(String, nullable=False, default="gpt-4")
    triggered_by = Column(String, nullable=False)  # mentor, admin, system
    triggered_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    triggered_by_user = relationship("User", foreign_keys=[triggered_by_user_id])
    notes = Column(Text, nullable=True)

    assessment = relationship("Assessment", back_populates="score_history")
