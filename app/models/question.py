from sqlalchemy import Column, String, ForeignKey, Enum, Text, Integer, Boolean
from sqlalchemy.orm import relationship
from app.db import Base
import uuid
import enum

class QuestionType(enum.Enum):
    open_ended = "open_ended"
    multiple_choice = "multiple_choice"

class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False, default=QuestionType.open_ended)
    category_id = Column(ForeignKey("categories.id"))
    
    # Relationship to question options
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")
    
    # Relationship to template questions
    template_questions = relationship("AssessmentTemplateQuestion", back_populates="question")

class QuestionOption(Base):
    __tablename__ = "question_options"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    
    # Relationship back to question
    question = relationship("Question", back_populates="options")