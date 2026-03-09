from typing import Optional
from firebase_admin import auth
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth
from app.db import get_db
from app.models.user import User, UserRole, SubscriptionTier
from sqlalchemy.orm import Session
from datetime import UTC, datetime
from app.utils.datetime import utc_now
from app.schemas.user import UserSchema
from app.core.settings import settings

security = HTTPBearer(auto_error=False)  # auto_error=False allows optional auth

def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing or invalid")
    id_token = auth_header.split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_role(role: str):
    def role_checker(decoded_token=Depends(verify_token)):
        if decoded_token.get("role") != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Insufficient role")
        return decoded_token
    return role_checker

def require_roles(roles: list):
    def role_checker(decoded_token=Depends(verify_token)):
        if decoded_token.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Insufficient role")
        return decoded_token
    return role_checker

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )
    
    token = credentials.credentials
    # Test tokens for development (ensure persistence so FK constraints pass)
    mock_map = {
        "mock-mentor-token": ("mentor-1", "Mentor One", "mentor@example.com", UserRole.mentor),
        "mock-apprentice-token": ("apprentice-1", "Apprentice One", "apprentice@example.com", UserRole.apprentice),
        "mock-admin-token": ("admin-1", "Admin One", "admin@example.com", UserRole.admin),
    }
    if token in mock_map:
        uid, name, email, role = mock_map[token]
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            user = User(id=uid, name=name, email=email, role=role, created_at=utc_now())
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        user_id = decoded_token["uid"]
        email = decoded_token["email"]
        # Try to get full name from token
        full_name = None
        if "name" in decoded_token:
            full_name = decoded_token["name"]
        else:
            # Try to build from given_name and family_name if available
            given = decoded_token.get("given_name", "")
            family = decoded_token.get("family_name", "")
            if given or family:
                full_name = (given + " " + family).strip()
        # Try to get role from token (custom claim)
        role_from_token = decoded_token.get("role")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )

    # First try to find user by Firebase UID
    user = db.query(User).filter(User.id == user_id).first()
    
    # If not found by UID, try to find by email (for existing users)
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Update the user's ID to match Firebase UID
            user.id = user_id
            db.commit()
            return user
    
    # If still not found, do NOT auto-create - require explicit POST /users/ call
    # This prevents race conditions where user gets created with wrong role
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please complete registration first.",
        )
    
    return user

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Optional authentication - returns User if authenticated, None otherwise.
    Used for endpoints that work for both authenticated and anonymous users.
    """
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None

def require_mentor(user: User = Depends(get_current_user)) -> User:
    # Treat admin as having mentor capabilities; accept enum or string roles
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    if role_val not in {UserRole.mentor.value, UserRole.admin.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mentor (or admin) access required"
        )
    return user

def require_apprentice(user: User = Depends(get_current_user)) -> User:
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    if role_val != UserRole.apprentice.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apprentice access required"
        )
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    if role_val != UserRole.admin.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user

def require_mentor_or_admin(user: User = Depends(get_current_user)) -> User:
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    if role_val not in {UserRole.mentor.value, UserRole.admin.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mentors or admins only"
        )
    return user


# =============================================================================
# Premium Feature Gating
# =============================================================================

# Premium tiers that grant full access
PREMIUM_TIERS = {
    SubscriptionTier.mentor_premium,
    SubscriptionTier.apprentice_premium,
    SubscriptionTier.mentor_gifted,
}


def is_subscription_expired(user: User) -> bool:
    """Check if user's subscription has expired.
    
    Returns True if:
    - subscription_expires_at is set AND is in the past
    
    Returns False if:
    - subscription_expires_at is NULL (lifetime/admin grant)
    - subscription_expires_at is in the future
    """
    if not hasattr(user, 'subscription_expires_at') or user.subscription_expires_at is None:
        return False  # No expiration = never expires
    
    from datetime import datetime, timezone
    
    expires_at = user.subscription_expires_at
    now = datetime.now(timezone.utc)
    
    # Handle timezone-naive datetimes from database (assume UTC)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    return expires_at < now


def is_premium_user(user: User) -> bool:
    """Check if user has premium access.
    
    Premium access is granted if:
    1. User's subscription_tier is one of: mentor_premium, apprentice_premium, mentor_gifted
       AND subscription has not expired, OR
    2. PREMIUM_FEATURES_ENABLED env var is true (for testing), OR
    3. User is an admin (admins always have premium access)
    
    Args:
        user: The user to check
        
    Returns:
        True if user has premium access
    """
    # Admins always have premium access
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    if role_val == UserRole.admin.value:
        return True
    
    # Check env var for testing/override
    if settings.premium_features_enabled:
        return True
    
    # Check user's subscription tier (handle missing attribute gracefully)
    if not hasattr(user, 'subscription_tier') or user.subscription_tier is None:
        return False
    
    # Check if tier is a premium tier
    tier = user.subscription_tier
    if tier not in PREMIUM_TIERS:
        return False
    
    # Check if subscription has expired
    if is_subscription_expired(user):
        return False
    
    return True


def is_mentor_premium(user: User) -> bool:
    """Check if user has mentor premium specifically (not gifted/apprentice).
    
    Used for mentor-only premium features like:
    - Unlimited apprentices
    - Creating custom templates
    - Purchasing gift seats
    """
    if not is_premium_user(user):
        return False
    
    tier = user.subscription_tier
    return tier == SubscriptionTier.mentor_premium


def can_mentor_add_apprentice(user: User, current_apprentice_count: int) -> tuple[bool, str]:
    """Check if a mentor can add another apprentice.
    
    Rules:
    - Premium mentors: unlimited apprentices
    - Grandfathered mentors: unlimited apprentices (existing relationships preserved)
    - Free mentors: max 1 apprentice
    
    Args:
        user: The mentor user
        current_apprentice_count: Current number of linked apprentices
        
    Returns:
        Tuple of (can_add: bool, reason: str)
    """
    # Premium mentors have no limit
    if is_mentor_premium(user):
        return True, "Premium mentor - unlimited apprentices"
    
    # Grandfathered mentors have no limit
    if hasattr(user, 'is_grandfathered_mentor') and user.is_grandfathered_mentor:
        return True, "Grandfathered mentor - unlimited apprentices"
    
    # Free mentors limited to 1
    if current_apprentice_count >= 1:
        return False, "Free mentors can only have 1 apprentice. Upgrade to premium for unlimited."
    
    return True, "Free mentor - can add 1 apprentice"


def require_premium(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency that requires premium subscription.
    
    Use this for endpoints that should only be accessible to premium users.
    Raises HTTP 403 if user doesn't have premium access.
    
    Usage:
        @router.get("/premium-feature")
        def premium_endpoint(user: User = Depends(require_premium)):
            # Only premium users reach here
            pass
    """
    if not is_premium_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for this feature"
        )
    return user


def require_premium_mentor(user: User = Depends(require_mentor)) -> User:
    """FastAPI dependency that requires both mentor role AND premium subscription.
    
    Use this for premium mentor-only features like full AI reports.
    
    Usage:
        @router.get("/mentor/reports/{id}/full")
        def get_full_report(user: User = Depends(require_premium_mentor)):
            # Only premium mentors reach here
            pass
    """
    if not is_premium_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for this feature"
        )
    return user


def check_premium_access(user: User) -> dict:
    """Check user's premium access and return status details.
    
    Useful for frontend to show upgrade prompts or feature availability.
    
    Returns:
        Dict with premium status info
    """
    has_premium = is_premium_user(user)
    tier_val = user.subscription_tier.value if hasattr(user.subscription_tier, 'value') else str(user.subscription_tier)
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    
    # Check expiration
    expires_at = None
    is_expired = False
    if hasattr(user, 'subscription_expires_at') and user.subscription_expires_at:
        expires_at = user.subscription_expires_at.isoformat()
        is_expired = is_subscription_expired(user)
    
    # Check platform
    platform = None
    if hasattr(user, 'subscription_platform') and user.subscription_platform:
        platform = user.subscription_platform.value
    
    return {
        "has_premium": has_premium,
        "subscription_tier": tier_val,
        "subscription_expires_at": expires_at,
        "subscription_expired": is_expired,
        "subscription_platform": platform,
        "is_admin": role_val == UserRole.admin.value,
        "is_grandfathered": getattr(user, 'is_grandfathered_mentor', False),
        "auto_renew": getattr(user, 'subscription_auto_renew', False),
        "premium_source": (
            "admin" if role_val == UserRole.admin.value else
            "env_override" if settings.premium_features_enabled else
            "subscription" if has_premium else
            None
        )
    }