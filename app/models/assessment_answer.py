from sqlalchemy import Column, String, ForeignKey, Text
from app.db import Base
import uuid

class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, ForeignKey("assessment_drafts.id"), nullable=False)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text, nullable=True)
