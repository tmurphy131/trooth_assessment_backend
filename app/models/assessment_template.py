from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime
import uuid

# models/assessment_template.py
class AssessmentTemplate(Base):
    __tablename__ = "assessment_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_published = Column(Boolean, default=False)
    is_master_assessment = Column(Boolean, default=False)  # True for the main Trooth Assessment
    created_by = Column(String, ForeignKey("users.id"), nullable=True)  # Allow null for existing records
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to User who created the template
    creator = relationship("User", back_populates="created_templates")
    
    # Relationship to template questions
    questions = relationship("AssessmentTemplateQuestion", back_populates="template")
