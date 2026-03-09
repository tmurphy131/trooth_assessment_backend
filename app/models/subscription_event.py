"""Subscription Events - Audit log for subscription changes.

Records all subscription-related events for debugging, analytics,
and audit purposes. Stores the raw webhook payload for reference.
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db import Base
import uuid


class SubscriptionEventType:
    """Constants for subscription event types."""
    # Purchase events
    INITIAL_PURCHASE = "initial_purchase"
    RENEWAL = "renewal"
    
    # Cancellation events  
    CANCELLATION = "cancellation"
    EXPIRATION = "expiration"
    
    # Refund events
    REFUND = "refund"
    
    # Gift seat events
    GIFT_SEAT_CREATED = "gift_seat_created"
    GIFT_SEAT_REDEEMED = "gift_seat_redeemed"
    GIFT_SEAT_REVOKED = "gift_seat_revoked"
    GIFT_SEAT_EXPIRED = "gift_seat_expired"
    
    # Admin events
    ADMIN_GRANTED = "admin_granted"
    ADMIN_REVOKED = "admin_revoked"
    ADMIN_EXTENDED = "admin_extended"
    
    # Grace period events
    BILLING_ISSUE = "billing_issue"
    GRACE_PERIOD_STARTED = "grace_period_started"
    GRACE_PERIOD_ENDED = "grace_period_ended"
    
    # Beta/launch events
    BETA_PREMIUM_GRANTED = "beta_premium_granted"
    GRANDFATHERED = "grandfathered"


class SubscriptionEvent(Base):
    """Log of all subscription-related events.
    
    Useful for:
    - Debugging subscription issues
    - Audit trail for refunds/disputes
    - Analytics on subscription lifecycle
    - Customer support investigations
    """
    __tablename__ = "subscription_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Who this event is for
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", foreign_keys=[user_id], backref="subscription_events")
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    
    # Platform info
    platform = Column(String(20), nullable=True)  # apple, google, admin, gifted
    product_id = Column(String(100), nullable=True)  # App Store/Play Store product ID
    
    # RevenueCat tracking
    revenuecat_event_id = Column(String(255), nullable=True, index=True)
    
    # Store the full payload for debugging
    raw_payload = Column(JSON, nullable=True)
    
    # Additional context (human-readable notes)
    notes = Column(String(500), nullable=True)
    
    # Who triggered this event (for admin actions)
    triggered_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    triggered_by = relationship("User", foreign_keys=[triggered_by_user_id])
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True)
    
    def __repr__(self):
        return f"<SubscriptionEvent {self.event_type} for user {self.user_id} at {self.created_at}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "platform": self.platform,
            "product_id": self.product_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
