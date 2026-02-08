"""
Subscription management endpoints for freemium system.

Handles:
- Subscription status checks
- RevenueCat webhook receiver
- Gift seat management
- Code redemption
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import secrets
import logging
import hmac
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.db import get_db
from app.models.user import User, UserRole, SubscriptionTier, SubscriptionPlatform
from app.models.mentor_premium_seat import MentorPremiumSeat
from app.models.subscription_event import SubscriptionEvent, SubscriptionEventType as EventTypes
from app.models.mentor_apprentice import MentorApprentice
from app.services.auth import (
    get_current_user,
    require_mentor,
    require_admin,
    is_premium_user,
    is_mentor_premium,
    check_premium_access,
    PREMIUM_TIERS,
)
from app.core.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# =============================================================================
# Schemas
# =============================================================================

class SubscriptionStatusResponse(BaseModel):
    """User's subscription status."""
    has_premium: bool
    subscription_tier: str
    subscription_expires_at: Optional[str] = None
    subscription_expired: bool
    subscription_platform: Optional[str] = None
    is_admin: bool
    is_grandfathered: bool
    auto_renew: bool
    premium_source: Optional[str] = None
    # Additional info for upgrade prompts
    can_add_apprentices: bool = True
    max_apprentices: Optional[int] = None
    current_apprentice_count: int = 0


class RedeemCodeRequest(BaseModel):
    """Request to redeem a gift code."""
    code: str = Field(..., min_length=8, max_length=20, description="Gift code from mentor")


class RedeemCodeResponse(BaseModel):
    """Response after redeeming code."""
    success: bool
    message: str
    new_tier: Optional[str] = None
    expires_at: Optional[str] = None
    mentor_name: Optional[str] = None


class CreateSeatResponse(BaseModel):
    """Response when creating a gift seat."""
    seat_id: str
    redemption_code: str
    created_at: str
    expires_at: Optional[str] = None


class GiftSeatInfo(BaseModel):
    """Gift seat information."""
    id: str
    redemption_code: str
    is_redeemed: bool
    apprentice_email: Optional[str] = None
    apprentice_name: Optional[str] = None
    created_at: str
    redeemed_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool


# =============================================================================
# Subscription Status
# =============================================================================

@router.get("/status", response_model=SubscriptionStatusResponse)
def get_subscription_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's subscription status.
    
    Returns comprehensive subscription info including:
    - Current tier and premium status
    - Expiration date
    - Platform (Apple/Google/Gifted)
    - Grandfathered status for mentors
    - Apprentice limits for mentors
    """
    base_status = check_premium_access(user)
    
    # Add mentor-specific info
    if user.role == UserRole.mentor or user.role == UserRole.admin:
        current_count = db.query(func.count(MentorApprentice.apprentice_id)).filter(
            MentorApprentice.mentor_id == user.id
        ).scalar() or 0
        
        if is_mentor_premium(user) or getattr(user, 'is_grandfathered_mentor', False):
            max_apprentices = None  # Unlimited
            can_add = True
        else:
            max_apprentices = 1
            can_add = current_count < 1
        
        base_status["can_add_apprentices"] = can_add
        base_status["max_apprentices"] = max_apprentices
        base_status["current_apprentice_count"] = current_count
    else:
        base_status["can_add_apprentices"] = True
        base_status["current_apprentice_count"] = 0
    
    return SubscriptionStatusResponse(**base_status)


@router.post("/restore")
def restore_purchases(
    user: User = Depends(get_current_user),
):
    """
    Trigger restore purchases.
    
    This endpoint doesn't actually restore - that happens on the client via
    RevenueCat SDK. This endpoint just acknowledges the request and tells
    the client the current server-side status after any webhooks have processed.
    
    The client should:
    1. Call RevenueCat.restorePurchases() on the SDK
    2. Wait for webhooks to update server
    3. Call GET /subscriptions/status to get updated status
    """
    return {
        "message": "Restore initiated. Please refresh subscription status after a moment.",
        "current_status": check_premium_access(user)
    }


# =============================================================================
# Debug/Admin Subscription Management
# =============================================================================

class SetSubscriptionRequest(BaseModel):
    """Request to set subscription tier (admin/debug only)."""
    tier: str = Field(..., description="Tier: free, mentor_premium, apprentice_premium, mentor_gifted")
    expires_days: Optional[int] = Field(30, description="Days until expiration (default 30)")


@router.post("/admin/set-tier")
def admin_set_subscription_tier(
    request: SetSubscriptionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    DEBUG/ADMIN: Manually set a user's subscription tier.
    
    Use this for testing freemium features when StoreKit purchases
    don't trigger backend webhooks.
    
    Valid tiers: free, mentor_premium, apprentice_premium, mentor_gifted
    """
    valid_tiers = ["free", "mentor_premium", "apprentice_premium", "mentor_gifted"]
    if request.tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )
    
    # Set tier
    if request.tier == "free":
        user.subscription_tier = SubscriptionTier.free
        user.subscription_expires_at = None
        user.subscription_platform = None
        # Also clear grandfathered status for true free testing
        user.is_grandfathered_mentor = False
    else:
        tier_map = {
            "mentor_premium": SubscriptionTier.mentor_premium,
            "apprentice_premium": SubscriptionTier.apprentice_premium,
            "mentor_gifted": SubscriptionTier.mentor_gifted,
        }
        user.subscription_tier = tier_map[request.tier]
        user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_days or 30)
        user.subscription_platform = SubscriptionPlatform.admin_granted
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin set subscription for user {user.id}: tier={request.tier}, grandfathered={user.is_grandfathered_mentor}")
    
    return {
        "success": True,
        "message": f"Subscription tier set to {request.tier}",
        "new_status": check_premium_access(user)
    }


class SetGrandfatheredRequest(BaseModel):
    """Request to set grandfathered status."""
    is_grandfathered: bool = Field(..., description="Whether user is grandfathered")


@router.post("/admin/set-grandfathered")
def admin_set_grandfathered(
    request: SetGrandfatheredRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    DEBUG/ADMIN: Toggle grandfathered status for testing freemium restrictions.
    
    Grandfathered mentors have unlimited apprentice access even on free tier.
    """
    user.is_grandfathered_mentor = request.is_grandfathered
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin set grandfathered for user {user.id}: {request.is_grandfathered}")
    
    return {
        "success": True,
        "message": f"Grandfathered status set to {request.is_grandfathered}",
        "new_status": check_premium_access(user)
    }


# =============================================================================
# Gift Seat Management (Mentors)
# =============================================================================

mentor_seats_router = APIRouter(prefix="/mentor/seats", tags=["Mentor Gift Seats"])


@mentor_seats_router.post("", response_model=CreateSeatResponse)
def create_gift_seat(
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    """
    Create a new gift seat code (manual/admin creation).
    
    NOTE: For per-seat IAP billing, gift seats are created automatically 
    by the RevenueCat webhook when a mentor purchases a `mentor_gift_seat_monthly` 
    subscription. This endpoint is for:
    - Admin-granted seats (no RevenueCat subscription)
    - Premium mentors who want to create extra seats tied to their existing subscription
    
    For IAP-based seats, the flow is:
    1. Frontend calls RevenueCat to purchase mentor_gift_seat_monthly
    2. RevenueCat webhook creates seat automatically with subscription ID
    3. Frontend refreshes list via GET /mentor/seats
    
    Requires: Mentor with premium subscription
    
    Returns: Seat ID and redemption code
    """
    # Verify mentor has premium
    if not is_mentor_premium(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required to create gift seats. Upgrade to mentor premium."
        )
    
    # Generate unique code
    code = generate_redemption_code()
    while db.query(MentorPremiumSeat).filter(MentorPremiumSeat.redemption_code == code).first():
        code = generate_redemption_code()
    
    # Set expiration to match mentor's subscription (legacy behavior for non-IAP seats)
    expires_at = getattr(user, 'subscription_expires_at', None)
    
    seat = MentorPremiumSeat(
        mentor_id=user.id,
        redemption_code=code,
        expires_at=expires_at,
        # No RevenueCat subscription - this is a legacy/admin seat
        revenuecat_subscription_id=None,
    )
    db.add(seat)
    db.commit()
    db.refresh(seat)
    
    logger.info(f"Mentor {user.email} created manual gift seat {seat.id}")
    
    return CreateSeatResponse(
        seat_id=seat.id,
        redemption_code=seat.redemption_code,
        created_at=seat.created_at.isoformat(),
        expires_at=seat.expires_at.isoformat() if seat.expires_at else None,
    )


@mentor_seats_router.get("", response_model=list[GiftSeatInfo])
def list_gift_seats(
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    """
    List all gift seats created by this mentor.
    
    Returns seats in order of creation (newest first), showing:
    - Redemption code
    - Whether redeemed and by whom
    - Expiration status
    """
    seats = db.query(MentorPremiumSeat).filter(
        MentorPremiumSeat.mentor_id == user.id
    ).order_by(MentorPremiumSeat.created_at.desc()).all()
    
    result = []
    for seat in seats:
        apprentice = None
        if seat.apprentice_id:
            apprentice = db.query(User).filter(User.id == seat.apprentice_id).first()
        
        result.append(GiftSeatInfo(
            id=seat.id,
            redemption_code=seat.redemption_code,
            is_redeemed=seat.is_redeemed,
            apprentice_email=apprentice.email if apprentice else None,
            apprentice_name=apprentice.name if apprentice else None,
            created_at=seat.created_at.isoformat(),
            redeemed_at=seat.redeemed_at.isoformat() if seat.redeemed_at else None,
            expires_at=seat.expires_at.isoformat() if seat.expires_at else None,
            is_active=seat.is_active,
        ))
    
    return result


class PurchaseSeatRequest(BaseModel):
    """Request to confirm a gift seat IAP purchase."""
    subscription_id: str = Field(..., description="RevenueCat subscription/transaction ID")
    product_id: str = Field(..., description="Product ID (e.g., mentor_gift_seat_monthly)")
    apprentice_email: Optional[str] = Field(None, description="Optional apprentice email to auto-assign")
    apprentice_name: Optional[str] = Field(None, description="Optional apprentice name")
    apprentice_id: Optional[str] = Field(None, description="Optional apprentice ID for direct assignment (preferred over email)")


@mentor_seats_router.post("/purchase", response_model=CreateSeatResponse)
def confirm_seat_purchase(
    data: PurchaseSeatRequest,
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    """
    Confirm a gift seat IAP purchase from the client.
    
    This is called after the RevenueCat SDK successfully processes a purchase.
    It may find a seat already created by webhook, or create one if webhook
    hasn't arrived yet (race condition handling).
    
    Flow:
    1. Client purchases mentor_gift_seat_monthly via RevenueCat SDK
    2. Client calls this endpoint with subscription ID
    3. Backend finds or creates the seat
    4. Returns seat details to client
    
    Args:
        subscription_id: RevenueCat transaction/subscription ID
        product_id: Product purchased (for validation)
    
    Returns: Seat ID and redemption code
    """
    # Check if seat already exists (created by webhook)
    existing_seat = db.query(MentorPremiumSeat).filter(
        MentorPremiumSeat.revenuecat_subscription_id == data.subscription_id
    ).first()
    
    if existing_seat:
        # Seat already created by webhook - just return it
        if existing_seat.mentor_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This subscription belongs to a different user"
            )
        
        logger.info(f"Found existing seat {existing_seat.id} for subscription {data.subscription_id}")
        
        # If seat exists but not yet assigned, try to assign apprentice now
        if not existing_seat.apprentice_id:
            apprentice = None
            
            # First try by apprentice_id (direct selection from dropdown)
            if data.apprentice_id:
                apprentice = db.query(User).filter(
                    User.id == data.apprentice_id,
                    User.role == UserRole.apprentice
                ).first()
                
                # Verify this apprentice is linked to the mentor
                if apprentice:
                    is_linked = db.query(MentorApprentice).filter(
                        MentorApprentice.mentor_id == user.id,
                        MentorApprentice.apprentice_id == data.apprentice_id
                    ).first()
                    if not is_linked:
                        logger.warning(f"Mentor {user.id} tried to gift existing seat to unlinked apprentice {data.apprentice_id}")
                        apprentice = None
            
            # Fallback to email lookup
            if not apprentice and data.apprentice_email:
                apprentice = db.query(User).filter(
                    User.email == data.apprentice_email.lower(),
                    User.role == UserRole.apprentice
                ).first()
            
            if apprentice:
                # Check if apprentice already has premium
                if apprentice.subscription_tier not in [None, SubscriptionTier.free]:
                    logger.info(f"Apprentice {apprentice.email} already has {apprentice.subscription_tier} - seat will remain unassigned")
                    apprentice = None  # Clear so seat stays unassigned
            
            if apprentice:
                # Auto-assign to existing apprentice
                existing_seat.apprentice_id = apprentice.id
                existing_seat.apprentice_email = apprentice.email
                existing_seat.apprentice_name = data.apprentice_name or apprentice.name
                existing_seat.is_redeemed = True
                existing_seat.redeemed_at = datetime.now(timezone.utc)
                
                # Grant premium to apprentice
                expires_at = existing_seat.expires_at or (datetime.now(timezone.utc) + timedelta(days=30))
                platform = existing_seat.subscription_platform or "apple"
                apprentice.subscription_tier = SubscriptionTier.mentor_gifted
                apprentice.subscription_expires_at = expires_at
                apprentice.subscription_platform = platform
                
                log_subscription_event(
                    db, apprentice.id, EventTypes.GIFT_SEAT_REDEEMED,
                    {"seat_id": existing_seat.id, "mentor_id": user.id, "auto_assigned": True, "from_existing_seat": True}
                )
                
                db.commit()
                db.refresh(existing_seat)
                
                # Send email notification to apprentice about the gift
                try:
                    from app.services.email import send_gift_seat_email
                    send_gift_seat_email(
                        to_email=apprentice.email,
                        apprentice_name=apprentice.name,
                        mentor_name=user.name or user.email,
                        redemption_code=existing_seat.redemption_code,
                        auto_activated=True,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send gift seat email to {apprentice.email}: {e}")
        
        return CreateSeatResponse(
            seat_id=existing_seat.id,
            redemption_code=existing_seat.redemption_code,
            created_at=existing_seat.created_at.isoformat(),
            expires_at=existing_seat.expires_at.isoformat() if existing_seat.expires_at else None,
        )
    
    # Seat not found - create it (webhook hasn't arrived yet)
    # This handles race conditions between client and webhook
    from app.models.mentor_premium_seat import generate_redemption_code as gen_code
    
    code = gen_code()
    while db.query(MentorPremiumSeat).filter(MentorPremiumSeat.redemption_code == code).first():
        code = gen_code()
    
    platform = "apple" if "apple" in data.product_id.lower() else "google"
    
    # Set initial expiration to 1 month (webhook will update on renewal)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    
    seat = MentorPremiumSeat(
        mentor_id=user.id,
        redemption_code=code,
        revenuecat_subscription_id=data.subscription_id,
        revenuecat_product_id=data.product_id,
        subscription_platform=platform,
        expires_at=expires_at,
        is_active=True,
    )
    
    # Try to assign to apprentice (prefer ID over email lookup)
    apprentice = None
    
    # First try by apprentice_id (direct selection from dropdown)
    if data.apprentice_id:
        apprentice = db.query(User).filter(
            User.id == data.apprentice_id,
            User.role == UserRole.apprentice
        ).first()
        
        # Verify this apprentice is linked to the mentor
        if apprentice:
            is_linked = db.query(MentorApprentice).filter(
                MentorApprentice.mentor_id == user.id,
                MentorApprentice.apprentice_id == data.apprentice_id
            ).first()
            if not is_linked:
                logger.warning(f"Mentor {user.id} tried to gift seat to unlinked apprentice {data.apprentice_id}")
                apprentice = None  # Don't allow gifting to unlinked apprentices
    
    # Fallback to email lookup if no ID or ID lookup failed
    if not apprentice and data.apprentice_email:
        apprentice = db.query(User).filter(
            User.email == data.apprentice_email.lower(),
            User.role == UserRole.apprentice
        ).first()
    
    if apprentice:
        # Check if apprentice already has premium
        if apprentice.subscription_tier not in [None, SubscriptionTier.free]:
            # Don't auto-assign to someone who already has premium
            logger.info(f"Apprentice {apprentice.email} already has {apprentice.subscription_tier} - seat will remain unassigned")
            apprentice = None  # Clear so seat stays unassigned
    
    if apprentice:
        # Auto-assign to existing apprentice
        seat.apprentice_id = apprentice.id
        seat.apprentice_email = apprentice.email
        seat.apprentice_name = data.apprentice_name or apprentice.name
        seat.is_redeemed = True
        seat.redeemed_at = datetime.now(timezone.utc)
        
        # Grant premium to apprentice
        apprentice.subscription_tier = SubscriptionTier.mentor_gifted
        apprentice.subscription_expires_at = expires_at
        apprentice.subscription_platform = platform
        
        log_subscription_event(
            db, apprentice.id, EventTypes.GIFT_SEAT_REDEEMED,
            {"seat_id": seat.id, "mentor_id": user.id, "auto_assigned": True}
        )
        
        # Send email notification to apprentice about the gift
        try:
            from app.services.email import send_gift_seat_email
            send_gift_seat_email(
                to_email=apprentice.email,
                apprentice_name=apprentice.name,
                mentor_name=user.name or user.email,
                redemption_code=code,
                auto_activated=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send gift seat email to {apprentice.email}: {e}")
    elif data.apprentice_email:
        # Apprentice doesn't exist yet - save email for later redemption
        seat.apprentice_email = data.apprentice_email.lower()
        seat.apprentice_name = data.apprentice_name
    
    db.add(seat)
    
    log_subscription_event(
        db, user.id, EventTypes.GIFT_SEAT_CREATED,
        {"seat_id": seat.id, "subscription_id": data.subscription_id, "source": "client_confirm"}
    )
    
    db.commit()
    db.refresh(seat)
    
    logger.info(f"Created seat {seat.id} from client purchase confirm (subscription {data.subscription_id})")
    
    return CreateSeatResponse(
        seat_id=seat.id,
        redemption_code=seat.redemption_code,
        created_at=seat.created_at.isoformat(),
        expires_at=seat.expires_at.isoformat() if seat.expires_at else None,
    )


@mentor_seats_router.post("/{seat_id}/revoke")
def revoke_gift_seat(
    seat_id: str,
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    """
    Revoke a gift seat, removing premium from the apprentice.
    
    The seat becomes available for reassignment (new code generated).
    The apprentice's subscription reverts to free.
    
    Returns: New redemption code if seat is regenerated
    """
    seat = db.query(MentorPremiumSeat).filter(
        MentorPremiumSeat.id == seat_id,
        MentorPremiumSeat.mentor_id == user.id,
    ).first()
    
    if not seat:
        raise HTTPException(status_code=404, detail="Gift seat not found")
    
    # If seat was redeemed, revoke apprentice's premium
    if seat.apprentice_id:
        apprentice = db.query(User).filter(User.id == seat.apprentice_id).first()
        if apprentice and apprentice.subscription_tier == SubscriptionTier.mentor_gifted:
            apprentice.subscription_tier = SubscriptionTier.free
            apprentice.subscription_expires_at = None
            apprentice.subscription_platform = None
            
            # Log event
            log_subscription_event(
                db, apprentice.id, EventTypes.ADMIN_REVOKED,
                {"reason": "Mentor revoked gift seat", "mentor_id": user.id}
            )
            logger.info(f"Revoked premium from {apprentice.email} (seat {seat_id})")
            
            # Send email notification to apprentice about revocation
            try:
                from app.services.email import send_gift_seat_revoked_email
                send_gift_seat_revoked_email(
                    to_email=apprentice.email,
                    apprentice_name=apprentice.name,
                    mentor_name=user.name or user.email,
                )
            except Exception as e:
                logger.warning(f"Failed to send gift seat revoked email to {apprentice.email}: {e}")
    
    # Reset seat for reuse
    seat.apprentice_id = None
    seat.is_redeemed = False
    seat.redeemed_at = None
    seat.redemption_code = generate_redemption_code()
    
    db.commit()
    
    return {
        "message": "Gift seat revoked and regenerated",
        "new_code": seat.redemption_code
    }


class AssignSeatRequest(BaseModel):
    """Request to assign an unassigned gift seat to an apprentice."""
    apprentice_id: Optional[str] = Field(None, description="Apprentice ID (preferred)")
    apprentice_email: Optional[str] = Field(None, description="Apprentice email (fallback)")
    apprentice_name: Optional[str] = Field(None, description="Apprentice name")


@mentor_seats_router.post("/{seat_id}/assign")
def assign_gift_seat(
    seat_id: str,
    data: AssignSeatRequest,
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    """
    Assign an unassigned gift seat to an apprentice.
    
    This is used to assign/reassign a seat after it was created or revoked.
    The apprentice gets immediate premium access.
    """
    seat = db.query(MentorPremiumSeat).filter(
        MentorPremiumSeat.id == seat_id,
        MentorPremiumSeat.mentor_id == user.id,
    ).first()
    
    if not seat:
        raise HTTPException(status_code=404, detail="Gift seat not found")
    
    if not seat.is_active:
        raise HTTPException(status_code=400, detail="This gift seat subscription has expired")
    
    if seat.apprentice_id:
        raise HTTPException(status_code=400, detail="Seat is already assigned. Revoke it first to reassign.")
    
    # Find the apprentice
    apprentice = None
    
    if data.apprentice_id:
        apprentice = db.query(User).filter(
            User.id == data.apprentice_id,
            User.role == UserRole.apprentice
        ).first()
        
        # Verify linked to mentor
        if apprentice:
            is_linked = db.query(MentorApprentice).filter(
                MentorApprentice.mentor_id == user.id,
                MentorApprentice.apprentice_id == data.apprentice_id
            ).first()
            if not is_linked:
                raise HTTPException(status_code=403, detail="This apprentice is not linked to you")
    
    if not apprentice and data.apprentice_email:
        apprentice = db.query(User).filter(
            User.email == data.apprentice_email.lower(),
            User.role == UserRole.apprentice
        ).first()
    
    if not apprentice:
        raise HTTPException(status_code=404, detail="Apprentice not found")
    
    # Check if apprentice already has premium
    if apprentice.subscription_tier not in [None, SubscriptionTier.free]:
        raise HTTPException(
            status_code=400, 
            detail=f"{apprentice.name or apprentice.email} already has a premium subscription"
        )
    
    # Assign the seat
    seat.apprentice_id = apprentice.id
    seat.apprentice_email = apprentice.email
    seat.apprentice_name = data.apprentice_name or apprentice.name
    seat.is_redeemed = True
    seat.redeemed_at = datetime.now(timezone.utc)
    
    # Grant premium
    apprentice.subscription_tier = SubscriptionTier.mentor_gifted
    apprentice.subscription_expires_at = seat.expires_at
    apprentice.subscription_platform = seat.subscription_platform
    
    log_subscription_event(
        db, apprentice.id, EventTypes.GIFT_SEAT_REDEEMED,
        {"seat_id": seat.id, "mentor_id": user.id, "assigned": True}
    )
    
    db.commit()
    
    # Send email notification
    try:
        from app.services.email import send_gift_seat_email
        send_gift_seat_email(
            to_email=apprentice.email,
            apprentice_name=apprentice.name,
            mentor_name=user.name or user.email,
            redemption_code=seat.redemption_code,
            auto_activated=True,
        )
    except Exception as e:
        logger.warning(f"Failed to send gift seat email to {apprentice.email}: {e}")
    
    return {
        "message": f"Gift seat assigned to {apprentice.name or apprentice.email}",
        "apprentice_id": apprentice.id,
        "apprentice_name": apprentice.name,
    }


@mentor_seats_router.delete("/{seat_id}")
def delete_gift_seat(
    seat_id: str,
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    """
    Permanently delete a gift seat.
    
    If the seat was redeemed, the apprentice's premium is revoked.
    """
    seat = db.query(MentorPremiumSeat).filter(
        MentorPremiumSeat.id == seat_id,
        MentorPremiumSeat.mentor_id == user.id,
    ).first()
    
    if not seat:
        raise HTTPException(status_code=404, detail="Gift seat not found")
    
    # If seat was redeemed, revoke apprentice's premium
    if seat.apprentice_id:
        apprentice = db.query(User).filter(User.id == seat.apprentice_id).first()
        if apprentice and apprentice.subscription_tier == SubscriptionTier.mentor_gifted:
            apprentice.subscription_tier = SubscriptionTier.free
            apprentice.subscription_expires_at = None
            apprentice.subscription_platform = None
    
    db.delete(seat)
    db.commit()
    
    return {"message": "Gift seat deleted"}


# =============================================================================
# Apprentice Code Redemption
# =============================================================================

apprentice_router = APIRouter(prefix="/apprentice", tags=["Apprentice Subscription"])


@apprentice_router.post("/redeem-code", response_model=RedeemCodeResponse)
def redeem_gift_code(
    request: RedeemCodeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Redeem a gift code from a mentor.
    
    The code grants the apprentice premium access (mentor_gifted tier) until
    the mentor's subscription expires or the seat is revoked.
    
    Codes are case-insensitive.
    """
    code = request.code.strip().upper()
    
    seat = db.query(MentorPremiumSeat).filter(
        MentorPremiumSeat.redemption_code == code
    ).first()
    
    if not seat:
        return RedeemCodeResponse(
            success=False,
            message="Invalid code. Please check the code and try again."
        )
    
    if seat.is_redeemed:
        return RedeemCodeResponse(
            success=False,
            message="This code has already been redeemed."
        )
    
    if not seat.is_active:
        return RedeemCodeResponse(
            success=False,
            message="This code is no longer active."
        )
    
    # Check if seat has expired
    if seat.expires_at and seat.expires_at < datetime.now(timezone.utc):
        return RedeemCodeResponse(
            success=False,
            message="This code has expired."
        )
    
    # Check if user already has premium from another source
    if user.subscription_tier in PREMIUM_TIERS:
        return RedeemCodeResponse(
            success=False,
            message="You already have a premium subscription."
        )
    
    # Get mentor for response
    mentor = db.query(User).filter(User.id == seat.mentor_id).first()
    
    # Redeem the seat
    seat.apprentice_id = user.id
    seat.is_redeemed = True
    seat.redeemed_at = datetime.now(timezone.utc)
    
    # Update user's subscription
    user.subscription_tier = SubscriptionTier.mentor_gifted
    user.subscription_platform = SubscriptionPlatform.gifted
    user.subscription_expires_at = seat.expires_at
    
    # Log event
    log_subscription_event(
        db, user.id, EventTypes.GIFT_SEAT_REDEEMED,
        {"mentor_id": seat.mentor_id, "seat_id": seat.id}
    )
    
    db.commit()
    
    logger.info(f"User {user.email} redeemed gift code from mentor {mentor.email if mentor else 'unknown'}")
    
    return RedeemCodeResponse(
        success=True,
        message="Premium access activated!",
        new_tier="mentor_gifted",
        expires_at=seat.expires_at.isoformat() if seat.expires_at else None,
        mentor_name=mentor.name if mentor else None,
    )


@apprentice_router.get("/subscription-source")
def get_subscription_source(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if apprentice's premium is gifted or self-purchased.
    
    Returns source information and mentor details if gifted.
    """
    if user.subscription_tier == SubscriptionTier.mentor_gifted:
        # Find the seat
        seat = db.query(MentorPremiumSeat).filter(
            MentorPremiumSeat.apprentice_id == user.id,
            MentorPremiumSeat.is_redeemed == True,
        ).first()
        
        mentor = None
        if seat:
            mentor = db.query(User).filter(User.id == seat.mentor_id).first()
        
        return {
            "source": "gifted",
            "mentor_name": mentor.name if mentor else None,
            "mentor_email": mentor.email if mentor else None,
            "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
        }
    
    elif user.subscription_tier == SubscriptionTier.apprentice_premium:
        platform = user.subscription_platform.value if user.subscription_platform else None
        return {
            "source": "self_purchased",
            "platform": platform,
            "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "auto_renew": getattr(user, 'subscription_auto_renew', False),
        }
    
    else:
        return {
            "source": None,
            "tier": user.subscription_tier.value if user.subscription_tier else "free",
        }


# =============================================================================
# RevenueCat Webhook
# =============================================================================

@router.post("/webhook")
async def revenuecat_webhook(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """
    RevenueCat webhook receiver.
    
    Handles subscription lifecycle events:
    - INITIAL_PURCHASE: New subscription
    - RENEWAL: Subscription renewed
    - CANCELLATION: User cancelled (still active until end of period)
    - EXPIRATION: Subscription ended
    - BILLING_ISSUE: Payment failed, in grace period
    - PRODUCT_CHANGE: User changed plan
    
    Security: Verifies webhook using RevenueCat's authorization header.
    """
    # Verify webhook authenticity
    if settings.revenuecat_webhook_secret:
        expected = f"Bearer {settings.revenuecat_webhook_secret}"
        if authorization != expected:
            logger.warning("Invalid RevenueCat webhook authorization")
            raise HTTPException(status_code=401, detail="Invalid webhook authorization")
    
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event = payload.get("event", {})
    event_type = event.get("type")
    app_user_id = event.get("app_user_id")  # This is the Firebase UID
    product_id = event.get("product_id", "")
    
    logger.info(f"RevenueCat webhook: {event_type} for user {app_user_id}, product {product_id}")
    
    if not app_user_id:
        logger.warning("Webhook missing app_user_id")
        return {"status": "missing_user_id"}
    
    # Find user by Firebase UID (which is their user.id)
    user = db.query(User).filter(User.id == app_user_id).first()
    if not user:
        logger.warning(f"Webhook user not found: {app_user_id}")
        return {"status": "user_not_found"}
    
    # Check if this is a gift seat subscription
    is_gift_seat = "gift_seat" in product_id.lower()
    
    if is_gift_seat:
        # Handle gift seat subscription events
        return handle_gift_seat_webhook(db, user, event, event_type, product_id)
    
    # Map product IDs to subscription tiers
    tier = map_product_to_tier(product_id)
    platform = map_product_to_platform(product_id)
    
    # Parse expiration
    expires_at = parse_expiration_from_webhook(event)
    
    # Handle event types
    if event_type in ["INITIAL_PURCHASE", "RENEWAL", "UNCANCELLATION"]:
        user.subscription_tier = tier
        user.subscription_platform = platform
        user.subscription_expires_at = expires_at
        user.subscription_auto_renew = True
        
        log_subscription_event(
            db, user.id, 
            EventTypes.INITIAL_PURCHASE if event_type == "INITIAL_PURCHASE" else EventTypes.RENEWAL,
            {"product_id": product_id, "event_type": event_type}
        )
        
    elif event_type == "CANCELLATION":
        # User cancelled but subscription is still active until end of period
        user.subscription_auto_renew = False
        log_subscription_event(
            db, user.id, EventTypes.CANCELLATION,
            {"product_id": product_id}
        )
        
    elif event_type == "EXPIRATION":
        # Subscription period ended
        previous_tier = user.subscription_tier
        user.subscription_tier = SubscriptionTier.free
        user.subscription_auto_renew = False
        
        # If this was a mentor, deactivate their gift seats
        if previous_tier == SubscriptionTier.mentor_premium:
            deactivate_mentor_gift_seats(db, user.id)
        
        log_subscription_event(
            db, user.id, EventTypes.EXPIRATION,
            {"product_id": product_id}
        )
        
    elif event_type == "BILLING_ISSUE":
        # Payment failed - in grace period
        # Keep premium but flag the issue
        log_subscription_event(
            db, user.id, EventTypes.BILLING_ISSUE,
            {"product_id": product_id}
        )
        logger.warning(f"Billing issue for user {user.email}")
        
    elif event_type == "PRODUCT_CHANGE":
        # User upgraded/downgraded
        user.subscription_tier = tier
        log_subscription_event(
            db, user.id, EventTypes.INITIAL_PURCHASE,
            {"product_id": product_id, "event_type": "PRODUCT_CHANGE"}
        )
    
    db.commit()
    
    return {"status": "ok"}


# =============================================================================
# Admin Endpoints
# =============================================================================

admin_router = APIRouter(prefix="/admin/subscriptions", tags=["Admin - Subscriptions"])


@admin_router.post("/users/{user_id}/grant-premium")
def admin_grant_premium(
    user_id: str,
    tier: str = "mentor_premium",
    months: Optional[int] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Manually grant premium to a user.
    
    Args:
        user_id: Target user's ID
        tier: Subscription tier to grant (mentor_premium, apprentice_premium)
        months: Number of months (None = lifetime)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Map tier string to enum
    tier_map = {
        "mentor_premium": SubscriptionTier.mentor_premium,
        "apprentice_premium": SubscriptionTier.apprentice_premium,
    }
    if tier not in tier_map:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Use: {list(tier_map.keys())}")
    
    user.subscription_tier = tier_map[tier]
    user.subscription_platform = SubscriptionPlatform.admin_granted
    
    if months:
        user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=months * 30)
    else:
        user.subscription_expires_at = None  # Lifetime
    
    log_subscription_event(
        db, user.id, EventTypes.ADMIN_GRANTED,
        {"tier": tier, "months": months, "granted_by": admin.id}
    )
    
    db.commit()
    
    logger.info(f"Admin {admin.email} granted {tier} to {user.email} for {months or 'lifetime'} months")
    
    return {
        "message": f"Granted {tier} to {user.email}",
        "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
    }


@admin_router.delete("/users/{user_id}/revoke-premium")
def admin_revoke_premium(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually revoke premium from a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    previous_tier = user.subscription_tier
    user.subscription_tier = SubscriptionTier.free
    user.subscription_expires_at = None
    user.subscription_platform = None
    user.subscription_auto_renew = False
    
    log_subscription_event(
        db, user.id, EventTypes.ADMIN_REVOKED,
        {"previous_tier": previous_tier.value if previous_tier else None, "revoked_by": admin.id}
    )
    
    db.commit()
    
    logger.info(f"Admin {admin.email} revoked premium from {user.email}")
    
    return {"message": f"Revoked premium from {user.email}"}


@admin_router.get("/stats")
def get_subscription_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get subscription statistics."""
    total_users = db.query(func.count(User.id)).scalar()
    
    # Count by tier
    tier_counts = {}
    for tier in SubscriptionTier:
        count = db.query(func.count(User.id)).filter(User.subscription_tier == tier).scalar()
        tier_counts[tier.value] = count
    
    # Count by platform
    platform_counts = {}
    for platform in SubscriptionPlatform:
        count = db.query(func.count(User.id)).filter(User.subscription_platform == platform).scalar()
        platform_counts[platform.value] = count
    
    # Active gift seats
    active_seats = db.query(func.count(MentorPremiumSeat.id)).filter(
        MentorPremiumSeat.is_active == True
    ).scalar()
    
    redeemed_seats = db.query(func.count(MentorPremiumSeat.id)).filter(
        MentorPremiumSeat.is_redeemed == True
    ).scalar()
    
    return {
        "total_users": total_users,
        "by_tier": tier_counts,
        "by_platform": platform_counts,
        "gift_seats": {
            "active": active_seats,
            "redeemed": redeemed_seats,
        }
    }


# =============================================================================
# Helper Functions
# =============================================================================

def generate_redemption_code() -> str:
    """Generate a unique redemption code (8 characters, uppercase alphanumeric)."""
    # Avoid confusing characters (0/O, 1/I/L)
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return ''.join(secrets.choice(alphabet) for _ in range(8))


def log_subscription_event(
    db: Session,
    user_id: str,
    event_type: str,
    details: dict,
    platform: str = None,
    product_id: str = None,
):
    """Log a subscription event for auditing."""
    import json
    event = SubscriptionEvent(
        user_id=user_id,
        event_type=event_type,
        raw_payload=details,
        platform=platform,
        product_id=product_id,
        notes=json.dumps(details)[:500] if details else None,
    )
    db.add(event)


def map_product_to_tier(product_id: str) -> SubscriptionTier:
    """Map RevenueCat product ID to subscription tier."""
    product_id = product_id.lower()
    
    if "mentor" in product_id:
        return SubscriptionTier.mentor_premium
    elif "apprentice" in product_id:
        return SubscriptionTier.apprentice_premium
    else:
        # Default based on product prefix
        return SubscriptionTier.mentor_premium


def map_product_to_platform(product_id: str) -> SubscriptionPlatform:
    """Map RevenueCat product ID to platform."""
    product_id = product_id.lower()
    
    if "apple" in product_id or "ios" in product_id:
        return SubscriptionPlatform.apple
    elif "google" in product_id or "android" in product_id:
        return SubscriptionPlatform.google
    else:
        # RevenueCat usually includes platform info, but default to Apple
        return SubscriptionPlatform.apple


def parse_expiration_from_webhook(event: dict) -> Optional[datetime]:
    """Parse expiration timestamp from RevenueCat webhook event."""
    # RevenueCat sends expiration_at_ms in milliseconds
    expiration_ms = event.get("expiration_at_ms")
    if expiration_ms:
        return datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc)
    
    # Fallback to expiration_at string
    expiration_str = event.get("expiration_at")
    if expiration_str:
        try:
            return datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
        except ValueError:
            pass
    
    return None


def deactivate_mentor_gift_seats(db: Session, mentor_id: str):
    """
    Deactivate all gift seats when mentor's subscription expires.
    
    Apprentices with gifted seats lose their premium access.
    """
    seats = db.query(MentorPremiumSeat).filter(
        MentorPremiumSeat.mentor_id == mentor_id,
        MentorPremiumSeat.is_redeemed == True,
    ).all()
    
    for seat in seats:
        seat.is_active = False
        
        if seat.apprentice_id:
            apprentice = db.query(User).filter(User.id == seat.apprentice_id).first()
            if apprentice and apprentice.subscription_tier == SubscriptionTier.mentor_gifted:
                apprentice.subscription_tier = SubscriptionTier.free
                apprentice.subscription_expires_at = None
                apprentice.subscription_platform = None
                
                log_subscription_event(
                    db, apprentice.id, EventTypes.EXPIRATION,
                    {"reason": "Mentor subscription expired", "mentor_id": mentor_id}
                )
                logger.info(f"Deactivated gifted premium for {apprentice.email} due to mentor expiration")
                
                # Send email notification to apprentice
                try:
                    mentor = db.query(User).filter(User.id == mentor_id).first()
                    mentor_name = mentor.name or mentor.email if mentor else "Your mentor"
                    from app.services.email import send_gift_seat_revoked_email
                    send_gift_seat_revoked_email(
                        to_email=apprentice.email,
                        apprentice_name=apprentice.name,
                        mentor_name=mentor_name,
                    )
                    logger.info(f"Sent gift seat expired email to {apprentice.email}")
                except Exception as e:
                    logger.warning(f"Failed to send gift seat expired email to {apprentice.email}: {e}")


def handle_gift_seat_webhook(
    db: Session, 
    mentor: User, 
    event: dict, 
    event_type: str, 
    product_id: str
) -> dict:
    """
    Handle RevenueCat webhook events for gift seat subscriptions.
    
    Gift seats are separate subscriptions (mentor_gift_seat_monthly) that mentors
    purchase for each apprentice they want to give premium access to.
    
    Flow:
    - INITIAL_PURCHASE: Create a new seat with the subscription ID
    - RENEWAL: Extend the seat's expiration
    - CANCELLATION: Mark seat as not auto-renewing
    - EXPIRATION: Deactivate the seat and revoke apprentice's premium
    """
    from app.models.mentor_premium_seat import generate_redemption_code
    
    # Get subscription identifier from RevenueCat event
    # This ties the seat to the specific subscription
    subscription_id = event.get("id") or event.get("original_transaction_id")
    expires_at = parse_expiration_from_webhook(event)
    platform = "apple" if "apple" in product_id.lower() else "google"
    
    if event_type in ["INITIAL_PURCHASE"]:
        # Create new gift seat for this subscription
        seat = MentorPremiumSeat(
            mentor_id=mentor.id,
            redemption_code=generate_redemption_code(),
            revenuecat_subscription_id=subscription_id,
            revenuecat_product_id=product_id,
            subscription_platform=platform,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(seat)
        db.commit()
        db.refresh(seat)
        
        log_subscription_event(
            db, mentor.id, EventTypes.GIFT_SEAT_CREATED,
            {"seat_id": seat.id, "subscription_id": subscription_id, "product_id": product_id}
        )
        logger.info(f"Created gift seat {seat.id} for mentor {mentor.email} via subscription {subscription_id}")
        
        return {"status": "seat_created", "seat_id": seat.id}
    
    # Find existing seat by subscription ID
    seat = db.query(MentorPremiumSeat).filter(
        MentorPremiumSeat.revenuecat_subscription_id == subscription_id
    ).first()
    
    if not seat:
        logger.warning(f"Gift seat subscription {subscription_id} not found for event {event_type}")
        return {"status": "seat_not_found"}
    
    if event_type == "RENEWAL":
        # Extend seat expiration
        seat.expires_at = expires_at
        seat.is_active = True
        
        # If seat is redeemed, extend apprentice's premium too
        if seat.apprentice_id:
            apprentice = db.query(User).filter(User.id == seat.apprentice_id).first()
            if apprentice:
                apprentice.subscription_expires_at = expires_at
        
        db.commit()
        logger.info(f"Renewed gift seat {seat.id} until {expires_at}")
        return {"status": "seat_renewed"}
    
    elif event_type == "CANCELLATION":
        # Subscription cancelled but still active until end of period
        # Just note the cancellation, don't deactivate yet
        log_subscription_event(
            db, mentor.id, EventTypes.CANCELLATION,
            {"seat_id": seat.id, "subscription_id": subscription_id}
        )
        db.commit()
        logger.info(f"Gift seat {seat.id} subscription cancelled (will expire at {seat.expires_at})")
        return {"status": "cancellation_noted"}
    
    elif event_type == "EXPIRATION":
        # Subscription ended - deactivate seat and revoke apprentice premium
        seat.is_active = False
        seat.deactivated_at = datetime.now(timezone.utc)
        seat.deactivation_reason = "subscription_expired"
        
        if seat.apprentice_id:
            apprentice = db.query(User).filter(User.id == seat.apprentice_id).first()
            if apprentice and apprentice.subscription_tier == SubscriptionTier.mentor_gifted:
                apprentice.subscription_tier = SubscriptionTier.free
                apprentice.subscription_expires_at = None
                apprentice.subscription_platform = None
                
                log_subscription_event(
                    db, apprentice.id, EventTypes.EXPIRATION,
                    {"reason": "Gift seat subscription expired", "seat_id": seat.id}
                )
                logger.info(f"Revoked gifted premium from {apprentice.email} due to seat subscription expiration")
                
                # Send email notification to apprentice about gift expiration
                try:
                    from app.services.email import send_gift_seat_revoked_email
                    send_gift_seat_revoked_email(
                        to_email=apprentice.email,
                        apprentice_name=apprentice.name,
                        mentor_name=mentor.name or mentor.email,
                    )
                    logger.info(f"Sent gift seat expired email to {apprentice.email}")
                except Exception as e:
                    logger.warning(f"Failed to send gift seat expired email to {apprentice.email}: {e}")
        
        log_subscription_event(
            db, mentor.id, EventTypes.GIFT_SEAT_EXPIRED,
            {"seat_id": seat.id, "subscription_id": subscription_id}
        )
        db.commit()
        logger.info(f"Gift seat {seat.id} expired and deactivated")
        return {"status": "seat_expired"}
    
    elif event_type == "BILLING_ISSUE":
        # In grace period - keep premium but log issue
        log_subscription_event(
            db, mentor.id, EventTypes.BILLING_ISSUE,
            {"seat_id": seat.id, "subscription_id": subscription_id}
        )
        db.commit()
        logger.warning(f"Billing issue for gift seat {seat.id}")
        return {"status": "billing_issue_noted"}
    
    return {"status": "event_ignored"}
