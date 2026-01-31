"""Push notification API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.db import get_db
from app.services.auth import get_current_user, require_admin
from app.models.user import User
from app.models.device_token import DeviceToken, DevicePlatform
from app.schemas.push_notification import (
    RegisterDeviceRequest,
    RegisterDeviceResponse,
    UnregisterDeviceRequest,
    SendPushRequest,
    PushNotificationPayload
)
from app.services.push_notification import PushNotificationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register-device", response_model=RegisterDeviceResponse)
def register_device(
    request: RegisterDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a device for push notifications.
    
    Called by the mobile app after obtaining FCM token and user permission.
    If the token already exists for this user, updates it.
    If the token exists for a different user, reassigns it (device changed users).
    """
    # Check if token already exists
    existing = db.query(DeviceToken).filter(
        DeviceToken.fcm_token == request.fcm_token
    ).first()

    if existing:
        if existing.user_id == current_user.id:
            # Same user, same token - just update last_used
            existing.last_used = datetime.utcnow()
            existing.is_active = "true"
            existing.device_name = request.device_name or existing.device_name
            db.commit()
            db.refresh(existing)
            return RegisterDeviceResponse(
                id=existing.id,
                user_id=existing.user_id,
                platform=existing.platform.value,
                device_name=existing.device_name,
                created_at=existing.created_at,
                message="Device token updated"
            )
        else:
            # Token belonged to different user - reassign (user switched accounts)
            existing.user_id = current_user.id
            existing.platform = DevicePlatform(request.platform.value)
            existing.device_name = request.device_name
            existing.last_used = datetime.utcnow()
            existing.is_active = "true"
            db.commit()
            db.refresh(existing)
            logger.info(f"Reassigned device token to user {current_user.id}")
            return RegisterDeviceResponse(
                id=existing.id,
                user_id=existing.user_id,
                platform=existing.platform.value,
                device_name=existing.device_name,
                created_at=existing.created_at,
                message="Device registered (reassigned from previous user)"
            )

    # New token - create record
    device_token = DeviceToken(
        user_id=current_user.id,
        fcm_token=request.fcm_token,
        platform=DevicePlatform(request.platform.value),
        device_name=request.device_name
    )
    db.add(device_token)
    db.commit()
    db.refresh(device_token)

    logger.info(f"Registered new device for user {current_user.id} on {request.platform.value}")
    
    return RegisterDeviceResponse(
        id=device_token.id,
        user_id=device_token.user_id,
        platform=device_token.platform.value,
        device_name=device_token.device_name,
        created_at=device_token.created_at,
        message="Device registered successfully"
    )


@router.post("/unregister-device")
def unregister_device(
    request: UnregisterDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unregister a device from push notifications.
    
    Called when user logs out or disables notifications.
    """
    token = db.query(DeviceToken).filter(
        DeviceToken.fcm_token == request.fcm_token,
        DeviceToken.user_id == current_user.id
    ).first()

    if not token:
        # Token not found or belongs to different user - that's fine, no error
        return {"message": "Device unregistered", "found": False}

    # Option 1: Delete the token
    db.delete(token)
    db.commit()
    
    # Option 2: Just mark inactive (uncomment if you prefer soft delete)
    # token.is_active = "false"
    # db.commit()

    logger.info(f"Unregistered device for user {current_user.id}")
    return {"message": "Device unregistered successfully", "found": True}


@router.get("/my-devices")
def list_my_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all registered devices for the current user."""
    tokens = db.query(DeviceToken).filter(
        DeviceToken.user_id == current_user.id
    ).order_by(DeviceToken.last_used.desc()).all()

    return [
        {
            "id": t.id,
            "platform": t.platform.value,
            "device_name": t.device_name,
            "is_active": t.is_active == "true",
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "last_used": t.last_used.isoformat() if t.last_used else None
        }
        for t in tokens
    ]


@router.delete("/my-devices/{device_id}")
def remove_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a specific device by ID."""
    token = db.query(DeviceToken).filter(
        DeviceToken.id == device_id,
        DeviceToken.user_id == current_user.id
    ).first()

    if not token:
        raise HTTPException(status_code=404, detail="Device not found")

    db.delete(token)
    db.commit()

    return {"message": "Device removed successfully"}


# Admin endpoints for testing and management

@router.post("/admin/send-test")
def admin_send_test_notification(
    request: SendPushRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin endpoint to send a test push notification to a specific user."""
    payload = PushNotificationPayload(
        title=request.title,
        body=request.body,
        data=request.data
    )
    
    result = PushNotificationService.send_to_user(db, request.user_id, payload)
    return {
        "message": "Test notification sent",
        "result": result
    }


@router.get("/admin/device-stats")
def admin_device_stats(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get statistics about registered devices."""
    from sqlalchemy import func
    
    total = db.query(func.count(DeviceToken.id)).scalar()
    active = db.query(func.count(DeviceToken.id)).filter(
        DeviceToken.is_active == "true"
    ).scalar()
    
    by_platform = db.query(
        DeviceToken.platform,
        func.count(DeviceToken.id)
    ).filter(
        DeviceToken.is_active == "true"
    ).group_by(DeviceToken.platform).all()

    return {
        "total_devices": total,
        "active_devices": active,
        "inactive_devices": total - active,
        "by_platform": {p.value: c for p, c in by_platform}
    }
