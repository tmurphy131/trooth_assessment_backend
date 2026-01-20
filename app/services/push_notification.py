"""Push notification service using Firebase Cloud Messaging."""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.device_token import DeviceToken
from app.models.user import User
from app.schemas.push_notification import PushNotificationPayload

logger = logging.getLogger(__name__)


def _is_fcm_available() -> bool:
    """Check if Firebase Cloud Messaging is available."""
    try:
        import firebase_admin
        from firebase_admin import messaging
        # Check if Firebase app is initialized
        firebase_admin.get_app()
        return True
    except Exception:
        return False


def _convert_data_to_strings(data: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Convert data payload values to strings (FCM requirement)."""
    if not data:
        return {}
    return {k: str(v) for k, v in data.items()}


class PushNotificationService:
    """Service for sending push notifications via FCM."""

    @staticmethod
    def send_to_user(
        db: Session,
        user_id: str,
        payload: PushNotificationPayload
    ) -> Dict[str, Any]:
        """Send push notification to all devices of a specific user.
        
        Args:
            db: Database session
            user_id: Target user's ID
            payload: Notification content
            
        Returns:
            Dict with success count and any errors
        """
        if not _is_fcm_available():
            logger.warning("FCM not available - push notification skipped")
            return {"success_count": 0, "failure_count": 0, "message": "FCM not configured"}

        # Get all active device tokens for the user
        tokens = db.query(DeviceToken).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active == "true"
        ).all()

        if not tokens:
            logger.info(f"No active device tokens for user {user_id}")
            return {"success_count": 0, "failure_count": 0, "message": "No registered devices"}

        fcm_tokens = [t.fcm_token for t in tokens]
        return PushNotificationService._send_multicast(db, fcm_tokens, payload)

    @staticmethod
    def send_to_users(
        db: Session,
        user_ids: List[str],
        payload: PushNotificationPayload
    ) -> Dict[str, Any]:
        """Send push notification to multiple users.
        
        Args:
            db: Database session
            user_ids: List of target user IDs
            payload: Notification content
            
        Returns:
            Dict with success count and any errors
        """
        if not _is_fcm_available():
            logger.warning("FCM not available - push notification skipped")
            return {"success_count": 0, "failure_count": 0, "message": "FCM not configured"}

        tokens = db.query(DeviceToken).filter(
            DeviceToken.user_id.in_(user_ids),
            DeviceToken.is_active == "true"
        ).all()

        if not tokens:
            logger.info(f"No active device tokens for users {user_ids}")
            return {"success_count": 0, "failure_count": 0, "message": "No registered devices"}

        fcm_tokens = [t.fcm_token for t in tokens]
        return PushNotificationService._send_multicast(db, fcm_tokens, payload)

    @staticmethod
    def send_to_token(
        db: Session,
        fcm_token: str,
        payload: PushNotificationPayload
    ) -> Dict[str, Any]:
        """Send push notification to a specific device token.
        
        Args:
            db: Database session
            fcm_token: Target FCM token
            payload: Notification content
            
        Returns:
            Dict with success status
        """
        if not _is_fcm_available():
            logger.warning("FCM not available - push notification skipped")
            return {"success": False, "error": "FCM not configured"}

        from firebase_admin import messaging
        from firebase_admin.exceptions import FirebaseError

        message = PushNotificationService._build_message(payload, fcm_token)
        
        try:
            response = messaging.send(message)
            logger.info(f"Successfully sent message: {response}")
            return {"success": True, "message_id": response}
        except FirebaseError as e:
            logger.error(f"Failed to send push notification: {e}")
            # Handle invalid/expired tokens
            if "UNREGISTERED" in str(e) or "INVALID_ARGUMENT" in str(e):
                PushNotificationService._deactivate_token(db, fcm_token)
            return {"success": False, "error": str(e)}

    @staticmethod
    def _send_multicast(
        db: Session,
        fcm_tokens: List[str],
        payload: PushNotificationPayload
    ) -> Dict[str, Any]:
        """Send to multiple tokens using multicast.
        
        FCM supports up to 500 tokens per multicast.
        """
        from firebase_admin import messaging
        from firebase_admin.exceptions import FirebaseError

        if not fcm_tokens:
            return {"success_count": 0, "failure_count": 0}

        # Build the multicast message
        notification = messaging.Notification(
            title=payload.title,
            body=payload.body,
            image=payload.image_url
        )

        # Platform-specific configurations
        android_config = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                sound=payload.sound or "default",
                channel_id=payload.channel_id or "default",
                click_action=payload.click_action
            )
        )

        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound=payload.sound or "default",
                    badge=payload.badge
                )
            )
        )

        message = messaging.MulticastMessage(
            tokens=fcm_tokens,
            notification=notification,
            data=_convert_data_to_strings(payload.data),
            android=android_config,
            apns=apns_config
        )

        try:
            response = messaging.send_each_for_multicast(message)
            logger.info(
                f"Multicast result: {response.success_count} success, "
                f"{response.failure_count} failures"
            )

            # Handle failed tokens (invalid/expired)
            if response.failure_count > 0:
                for idx, send_response in enumerate(response.responses):
                    if not send_response.success:
                        error = send_response.exception
                        if error and ("UNREGISTERED" in str(error) or "INVALID" in str(error)):
                            PushNotificationService._deactivate_token(db, fcm_tokens[idx])
                            logger.warning(f"Deactivated invalid token: {fcm_tokens[idx][:20]}...")

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }
        except FirebaseError as e:
            logger.error(f"Multicast send failed: {e}")
            return {"success_count": 0, "failure_count": len(fcm_tokens), "error": str(e)}

    @staticmethod
    def _build_message(payload: PushNotificationPayload, token: str):
        """Build a single FCM message."""
        from firebase_admin import messaging

        notification = messaging.Notification(
            title=payload.title,
            body=payload.body,
            image=payload.image_url
        )

        android_config = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                sound=payload.sound or "default",
                channel_id=payload.channel_id or "default"
            )
        )

        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound=payload.sound or "default",
                    badge=payload.badge
                )
            )
        )

        return messaging.Message(
            token=token,
            notification=notification,
            data=_convert_data_to_strings(payload.data),
            android=android_config,
            apns=apns_config
        )

    @staticmethod
    def _deactivate_token(db: Session, fcm_token: str):
        """Mark a token as inactive (invalid/expired)."""
        token = db.query(DeviceToken).filter(
            DeviceToken.fcm_token == fcm_token
        ).first()
        if token:
            token.is_active = "false"
            db.commit()
            logger.info(f"Deactivated token for user {token.user_id}")


# Convenience functions for common notification types

def notify_assessment_submitted(
    db: Session,
    mentor_id: str,
    apprentice_name: str,
    assessment_name: str
) -> Dict[str, Any]:
    """Notify mentor that an apprentice submitted an assessment."""
    payload = PushNotificationPayload(
        title="Assessment Submitted",
        body=f"{apprentice_name} completed the {assessment_name} assessment",
        data={
            "type": "assessment_submitted",
            "screen": "mentor_dashboard"
        }
    )
    return PushNotificationService.send_to_user(db, mentor_id, payload)


def notify_agreement_signed(
    db: Session,
    user_id: str,
    signer_name: str,
    agreement_status: str
) -> Dict[str, Any]:
    """Notify user about agreement signature update."""
    if agreement_status == "fully_signed":
        body = f"Your mentorship agreement with {signer_name} is now fully signed!"
    else:
        body = f"{signer_name} has signed the mentorship agreement"
    
    payload = PushNotificationPayload(
        title="Agreement Update",
        body=body,
        data={
            "type": "agreement_signed",
            "screen": "agreements"
        }
    )
    return PushNotificationService.send_to_user(db, user_id, payload)


def notify_invitation_accepted(
    db: Session,
    mentor_id: str,
    apprentice_name: str
) -> Dict[str, Any]:
    """Notify mentor that an apprentice accepted their invitation."""
    payload = PushNotificationPayload(
        title="Invitation Accepted!",
        body=f"{apprentice_name} has accepted your mentorship invitation",
        data={
            "type": "invitation_accepted",
            "screen": "mentor_apprentices"
        }
    )
    return PushNotificationService.send_to_user(db, mentor_id, payload)


def notify_weekly_tip(
    db: Session,
    user_id: str,
    tip_title: str,
    is_mentor: bool = True
) -> Dict[str, Any]:
    """Send weekly tip notification to a user."""
    role = "Mentor" if is_mentor else "Apprentice"
    payload = PushNotificationPayload(
        title=f"Weekly {role} Tip",
        body=tip_title,
        data={
            "type": "weekly_tip",
            "screen": "resources"
        }
    )
    return PushNotificationService.send_to_user(db, user_id, payload)


def notify_weekly_tips_batch(
    db: Session,
    mentor_ids: List[str],
    apprentice_ids: List[str],
    mentor_tip_title: str,
    apprentice_tip_title: str
) -> Dict[str, Any]:
    """Send weekly tips to all mentors and apprentices."""
    results = {"mentors": None, "apprentices": None}
    
    if mentor_ids:
        mentor_payload = PushNotificationPayload(
            title="Weekly Mentor Tip",
            body=mentor_tip_title,
            data={"type": "weekly_tip", "screen": "resources"}
        )
        results["mentors"] = PushNotificationService.send_to_users(
            db, mentor_ids, mentor_payload
        )
    
    if apprentice_ids:
        apprentice_payload = PushNotificationPayload(
            title="Weekly Apprentice Tip",
            body=apprentice_tip_title,
            data={"type": "weekly_tip", "screen": "resources"}
        )
        results["apprentices"] = PushNotificationService.send_to_users(
            db, apprentice_ids, apprentice_payload
        )
    
    return results
