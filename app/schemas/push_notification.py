"""Pydantic schemas for push notification endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class DevicePlatformEnum(str, Enum):
    ios = "ios"
    android = "android"
    web = "web"


class RegisterDeviceRequest(BaseModel):
    """Request to register a device for push notifications."""
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token")
    platform: DevicePlatformEnum = Field(..., description="Device platform (ios, android, web)")
    device_name: Optional[str] = Field(None, description="Human-readable device name")

    model_config = {
        "json_schema_extra": {
            "example": {
                "fcm_token": "dKzH7v...:APA91b...",
                "platform": "ios",
                "device_name": "iPhone 15 Pro"
            }
        }
    }


class RegisterDeviceResponse(BaseModel):
    """Response after registering a device."""
    id: str
    user_id: str
    platform: str
    device_name: Optional[str]
    created_at: datetime
    message: str = "Device registered successfully"


class UnregisterDeviceRequest(BaseModel):
    """Request to unregister a device (e.g., on logout)."""
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token to remove")


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    weekly_tips: bool = Field(True, description="Receive weekly mentoring tips")
    assessment_updates: bool = Field(True, description="Notified when apprentice submits assessment")
    agreement_updates: bool = Field(True, description="Notified about agreement status changes")
    invitation_updates: bool = Field(True, description="Notified about invitation responses")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "weekly_tips": True,
                "assessment_updates": True,
                "agreement_updates": True,
                "invitation_updates": True
            }
        }
    }


class SendPushRequest(BaseModel):
    """Admin request to send a push notification (for testing/admin use)."""
    user_id: str = Field(..., description="Target user ID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body text")
    data: Optional[dict] = Field(None, description="Additional data payload for deep linking")


class PushNotificationPayload(BaseModel):
    """Internal model for push notification content."""
    title: str
    body: str
    data: Optional[dict] = None
    image_url: Optional[str] = None
    # iOS specific
    badge: Optional[int] = None
    sound: Optional[str] = "default"
    # Android specific
    click_action: Optional[str] = None
    channel_id: Optional[str] = "default"
