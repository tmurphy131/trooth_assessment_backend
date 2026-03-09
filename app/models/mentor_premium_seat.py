"""Mentor Premium Seats - Gift codes for apprentices.

When a premium mentor wants to gift premium access to their apprentices,
they purchase seats which generate unique redemption codes.
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db import Base
import uuid
import secrets
import string


def generate_redemption_code() -> str:
    """Generate a unique, human-readable redemption code.
    
    Format: TROOTH-XXXX-XXXX (uppercase letters and digits, no ambiguous chars)
    Example: TROOTH-A7K9-M2P4
    """
    # Exclude ambiguous characters: 0, O, I, 1, L
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    part1 = ''.join(secrets.choice(alphabet) for _ in range(4))
    part2 = ''.join(secrets.choice(alphabet) for _ in range(4))
    return f"TROOTH-{part1}-{part2}"


class MentorPremiumSeat(Base):
    """A premium seat that a mentor can gift to an apprentice.
    
    Flow:
    1. Mentor purchases seat subscription via RevenueCat (mentor_gift_seat_monthly)
    2. RevenueCat webhook creates seat record with subscription ID
    3. System generates unique redemption_code
    4. Mentor shares code with apprentice (or assigns directly by email)
    5. Apprentice redeems code → gets mentor_gifted tier
    6. If subscription lapses, webhook deactivates the seat
    """
    __tablename__ = "mentor_premium_seats"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Who owns this seat
    mentor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    mentor = relationship("User", foreign_keys=[mentor_id], backref="premium_seats_owned")
    
    # Who redeemed this seat (NULL until redeemed)
    apprentice_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    apprentice = relationship("User", foreign_keys=[apprentice_id], backref="gifted_seat")
    
    # Apprentice info for when seat is assigned but not yet redeemed
    # This stores the email/name before the apprentice creates an account
    apprentice_email = Column(String(255), nullable=True)
    apprentice_name = Column(String(255), nullable=True)
    
    # Unique code for redemption
    redemption_code = Column(String(20), unique=True, nullable=False, index=True, 
                            default=generate_redemption_code)
    
    # RevenueCat subscription tracking for per-seat billing
    # This links the seat to the actual IAP subscription
    revenuecat_subscription_id = Column(String(255), nullable=True, index=True)
    revenuecat_product_id = Column(String(100), nullable=True)  # e.g., 'mentor_gift_seat_monthly'
    subscription_platform = Column(String(20), nullable=True)  # 'apple' or 'google'
    
    # Redemption status
    is_redeemed = Column(Boolean, nullable=False, default=False, server_default="false")
    redeemed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    
    # Expiration - linked to subscription renewal
    # Updated by webhook on each renewal
    expires_at = Column(DateTime, nullable=True)
    
    # Active status - set to False when subscription lapses or seat is revoked
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    deactivated_at = Column(DateTime, nullable=True)
    deactivation_reason = Column(String(100), nullable=True)  # 'subscription_expired', 'revoked', 'cancelled'
    
    def __repr__(self):
        status = "redeemed" if self.is_redeemed else "available"
        active = "active" if self.is_active else "inactive"
        return f"<MentorPremiumSeat {self.redemption_code} ({status}, {active})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "mentor_id": self.mentor_id,
            "apprentice_id": self.apprentice_id,
            "apprentice_email": self.apprentice_email,
            "apprentice_name": self.apprentice_name,
            "redemption_code": self.redemption_code if not self.is_redeemed else None,  # Hide code once redeemed
            "is_redeemed": self.is_redeemed,
            "redeemed_at": self.redeemed_at.isoformat() if self.redeemed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "has_subscription": self.revenuecat_subscription_id is not None,
            "subscription_platform": self.subscription_platform,
        }
