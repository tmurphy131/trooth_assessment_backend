from sqlalchemy import Column, String, DateTime, Enum, Integer, Boolean
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
    mentor_premium: Mentor's own subscription (unlocks multiple apprentices + template creation)
    apprentice_premium: Apprentice's own subscription (unlocks all assessments)
    mentor_gifted: Apprentice premium paid for by mentor (code redemption)
    """
    free = "free"
    mentor_premium = "mentor_premium"
    apprentice_premium = "apprentice_premium"
    mentor_gifted = "mentor_gifted"


class SubscriptionPlatform(enum.Enum):
    """Platform where subscription was purchased."""
    apple = "apple"
    google = "google"
    gifted = "gifted"  # Mentor gifted seat
    admin_granted = "admin_granted"  # Manually granted by admin


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
    # Default to 'free', upgraded via RevenueCat webhook, gift code, or admin
    subscription_tier = Column(
        Enum(SubscriptionTier), 
        nullable=False, 
        default=SubscriptionTier.free,
        server_default="free"
    )
    
    # Subscription metadata
    subscription_expires_at = Column(DateTime, nullable=True)  # NULL = never expires (lifetime/admin grant)
    subscription_platform = Column(Enum(SubscriptionPlatform), nullable=True)  # How they got premium
    revenuecat_customer_id = Column(String(255), nullable=True, index=True)  # RevenueCat customer ID
    subscription_auto_renew = Column(Boolean, nullable=False, default=False, server_default="false")
    
    # Grandfathering flag for existing mentors with >1 apprentice at freemium launch
    is_grandfathered_mentor = Column(Boolean, nullable=False, default=False, server_default="false")
    
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