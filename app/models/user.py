from sqlalchemy import Column, String, DateTime, Enum
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
    
    # Relationship to templates created by this user
    created_templates = relationship("AssessmentTemplate", back_populates="creator")