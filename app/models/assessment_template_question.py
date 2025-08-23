from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Float, Integer
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime
import uuid


# models/assessment_template_question.py
class AssessmentTemplateQuestion(Base):
    __tablename__ = "assessment_template_questions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String, ForeignKey("assessment_templates.id"))
    question_id = Column(String, ForeignKey("questions.id"))
    order = Column(Integer, nullable=False)
    
    # Relationships
    question = relationship("Question", back_populates="template_questions")
    template = relationship("AssessmentTemplate", back_populates="questions")
