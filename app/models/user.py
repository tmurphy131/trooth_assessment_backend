from sqlalchemy import Column, String, DateTime, Enum, Integer
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, UTC
from app.db import Base
import uuid

class UserRole(enum.Enum):
    apprentice = "apprentice"
    mentor = "mentor"
    admin = "admin"


class SubscriptionTier(enum.Enum):
    """User subscription tier for freemium model.
    
    free: Default tier, limited features
    premium: Paid tier, all features including full AI reports
    """
    free = "free"
    premium = "premium"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    # Historical context (Phase 2)
    assessment_count = Column(Integer, nullable=True, default=0)  # Denormalized count for quick access
    
    # Subscription / Premium tier (for freemium model)
    # Default to 'free', upgraded to 'premium' via RevenueCat webhook or admin
    subscription_tier = Column(
        Enum(SubscriptionTier), 
        nullable=False, 
        default=SubscriptionTier.free,
        server_default="free"
    )
    
    # Relationship to templates created by this user
    created_templates = relationship("AssessmentTemplate", back_populates="creator")
    # Notifications for this user
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    # Device tokens for push notifications
    device_tokens = relationship("DeviceToken", back_populates="user", cascade="all, delete-orphan")

    # Mentor notes authored by this user (when user is a mentor)
    mentor_notes = relationship("MentorNote", back_populates="mentor", cascade="all, delete-orphan")

    # Assessments owned by this user (when user is an apprentice)
    assessments = relationship("Assessment", back_populates="apprentice", cascade="all, delete-orphan")