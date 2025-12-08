from sqlalchemy import Column, String, DateTime, Enum, Integer
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.db import Base
import uuid

class UserRole(enum.Enum):
    apprentice = "apprentice"
    mentor = "mentor"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Historical context (Phase 2)
    assessment_count = Column(Integer, nullable=True, default=0)  # Denormalized count for quick access
    
    # Relationship to templates created by this user
    created_templates = relationship("AssessmentTemplate", back_populates="creator")
    # Notifications for this user
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    # Mentor notes authored by this user (when user is a mentor)
    mentor_notes = relationship("MentorNote", back_populates="mentor", cascade="all, delete-orphan")

    # Assessments owned by this user (when user is an apprentice)
    assessments = relationship("Assessment", back_populates="apprentice", cascade="all, delete-orphan")