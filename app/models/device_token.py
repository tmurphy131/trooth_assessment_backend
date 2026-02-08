"""Device token model for push notifications."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db import Base
import uuid
import enum


class DevicePlatform(enum.Enum):
    ios = "ios"
    android = "android"
    web = "web"


class DeviceToken(Base):
    """Stores FCM device tokens for push notifications.
    
    Each user can have multiple devices (phone, tablet, etc.).
    Tokens can expire or be invalidated, so we track last_used.
    """
    __tablename__ = "device_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    fcm_token = Column(String, nullable=False, unique=True, index=True)
    platform = Column(SQLEnum(DevicePlatform), nullable=False)
    device_name = Column(String, nullable=True)  # e.g., "iPhone 15 Pro", "Pixel 8"
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_used = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_active = Column(String, default="true")  # String to avoid SQLite boolean issues

    user = relationship("User", back_populates="device_tokens")

    def __repr__(self):
        return f"<DeviceToken user={self.user_id} platform={self.platform.value}>"
