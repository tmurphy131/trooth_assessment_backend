#!/usr/bin/env python3
"""
Admin utility script for managing user subscriptions.

Usage examples:
    # Grant 6 months premium to a user by email
    python manage_subscriptions.py grant --email user@example.com --months 6
    
    # Grant 1 year premium to a user by user ID
    python manage_subscriptions.py grant --user-id abc123 --months 12
    
    # Grant lifetime premium (no expiration)
    python manage_subscriptions.py grant --email user@example.com --lifetime
    
    # Extend existing subscription by 3 months
    python manage_subscriptions.py extend --email user@example.com --months 3
    
    # Revoke premium (set to free)
    python manage_subscriptions.py revoke --email user@example.com
    
    # Check subscription status
    python manage_subscriptions.py status --email user@example.com
    
    # List all premium users
    python manage_subscriptions.py list-premium
    
    # Grant premium to all users (beta reward scenario)
    python manage_subscriptions.py grant-all --months 6

Environment:
    DATABASE_URL - PostgreSQL connection string (required)

"""

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import all models to ensure relationships are resolved
from app.models.user import User, UserRole, SubscriptionTier, SubscriptionPlatform
from app.models.subscription_event import SubscriptionEvent, SubscriptionEventType
from app.models.mentor_premium_seat import MentorPremiumSeat
# Import related models that User has relationships with
from app.models import (
    device_token, notification, mentor_note, assessment, 
    assessment_template, mentor_apprentice
)


def get_db_session():
    """Create a database session."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Example: export DATABASE_URL=postgresql://user:pass@localhost:5432/trooth_db")
        sys.exit(1)
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def get_user(db, email=None, user_id=None):
    """Get user by email or ID."""
    if email:
        user = db.query(User).filter(User.email == email).first()
    elif user_id:
        user = db.query(User).filter(User.id == user_id).first()
    else:
        return None
    
    if not user:
        print(f"ERROR: User not found (email={email}, id={user_id})")
        sys.exit(1)
    
    return user


def log_event(db, user, event_type, notes=None, triggered_by_id=None):
    """Log a subscription event."""
    import uuid
    event = SubscriptionEvent(
        id=str(uuid.uuid4()),
        user_id=user.id,
        event_type=event_type,
        platform="admin_granted",
        notes=notes,
        triggered_by_user_id=triggered_by_id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(event)


def get_tier_for_role(role):
    """Get appropriate premium tier based on user role."""
    if role == UserRole.mentor or role == UserRole.admin:
        return SubscriptionTier.mentor_premium
    else:
        return SubscriptionTier.apprentice_premium


def grant_premium(args):
    """Grant premium to a user."""
    db = get_db_session()
    user = get_user(db, email=args.email, user_id=args.user_id)
    
    # Calculate expiration
    if args.lifetime:
        expires_at = None
        duration_str = "lifetime"
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(days=args.months * 30)
        duration_str = f"{args.months} months"
    
    # Set appropriate tier based on role
    tier = get_tier_for_role(user.role)
    
    # Update user
    user.subscription_tier = tier
    user.subscription_expires_at = expires_at
    user.subscription_platform = SubscriptionPlatform.admin_granted
    
    # Log event
    log_event(db, user, SubscriptionEventType.ADMIN_GRANTED, 
              notes=f"Granted {tier.value} for {duration_str}")
    
    db.commit()
    
    print(f"✅ Granted {tier.value} to {user.email}")
    print(f"   Duration: {duration_str}")
    print(f"   Expires: {expires_at.isoformat() if expires_at else 'Never'}")


def extend_premium(args):
    """Extend existing subscription."""
    db = get_db_session()
    user = get_user(db, email=args.email, user_id=args.user_id)
    
    if user.subscription_tier == SubscriptionTier.free:
        print(f"ERROR: User {user.email} is not premium. Use 'grant' instead.")
        sys.exit(1)
    
    # Calculate new expiration
    if user.subscription_expires_at:
        # Extend from current expiration
        base_date = max(user.subscription_expires_at, datetime.now(timezone.utc))
    else:
        # Currently lifetime, extending makes no sense
        print(f"User {user.email} has lifetime premium. No extension needed.")
        return
    
    new_expires = base_date + timedelta(days=args.months * 30)
    old_expires = user.subscription_expires_at
    
    user.subscription_expires_at = new_expires
    
    # Log event
    log_event(db, user, SubscriptionEventType.ADMIN_EXTENDED,
              notes=f"Extended {args.months} months. Old: {old_expires}, New: {new_expires}")
    
    db.commit()
    
    print(f"✅ Extended subscription for {user.email}")
    print(f"   Old expiration: {old_expires.isoformat()}")
    print(f"   New expiration: {new_expires.isoformat()}")


def revoke_premium(args):
    """Revoke premium from a user."""
    db = get_db_session()
    user = get_user(db, email=args.email, user_id=args.user_id)
    
    old_tier = user.subscription_tier
    
    user.subscription_tier = SubscriptionTier.free
    user.subscription_expires_at = None
    user.subscription_platform = None
    
    # Log event
    log_event(db, user, SubscriptionEventType.ADMIN_REVOKED,
              notes=f"Revoked {old_tier.value}")
    
    db.commit()
    
    print(f"✅ Revoked premium from {user.email}")
    print(f"   Previous tier: {old_tier.value}")


def check_status(args):
    """Check subscription status for a user."""
    db = get_db_session()
    user = get_user(db, email=args.email, user_id=args.user_id)
    
    print(f"\n📊 Subscription Status for {user.email}")
    print("=" * 50)
    print(f"User ID:          {user.id}")
    print(f"Name:             {user.name}")
    print(f"Role:             {user.role.value}")
    print(f"Subscription Tier:{user.subscription_tier.value}")
    
    if user.subscription_expires_at:
        is_expired = user.subscription_expires_at < datetime.now(timezone.utc)
        status = "EXPIRED" if is_expired else "Active"
        print(f"Expires:          {user.subscription_expires_at.isoformat()} ({status})")
    else:
        print(f"Expires:          Never (lifetime)")
    
    if user.subscription_platform:
        print(f"Platform:         {user.subscription_platform.value}")
    
    print(f"Grandfathered:    {user.is_grandfathered_mentor}")
    print(f"Auto-renew:       {user.subscription_auto_renew}")
    
    # Show recent events
    events = db.query(SubscriptionEvent).filter(
        SubscriptionEvent.user_id == user.id
    ).order_by(SubscriptionEvent.created_at.desc()).limit(5).all()
    
    if events:
        print(f"\n📜 Recent Subscription Events:")
        for event in events:
            print(f"   {event.created_at.isoformat()}: {event.event_type}")
            if event.notes:
                print(f"      Notes: {event.notes}")


def list_premium(args):
    """List all premium users."""
    db = get_db_session()
    
    premium_tiers = [
        SubscriptionTier.mentor_premium,
        SubscriptionTier.apprentice_premium,
        SubscriptionTier.mentor_gifted,
    ]
    
    users = db.query(User).filter(User.subscription_tier.in_(premium_tiers)).all()
    
    print(f"\n📋 Premium Users ({len(users)} total)")
    print("=" * 80)
    print(f"{'Email':<35} {'Tier':<20} {'Expires':<25}")
    print("-" * 80)
    
    for user in users:
        expires = user.subscription_expires_at.strftime('%Y-%m-%d') if user.subscription_expires_at else "Never"
        print(f"{user.email:<35} {user.subscription_tier.value:<20} {expires:<25}")


def grant_all(args):
    """Grant premium to all users (beta reward scenario)."""
    db = get_db_session()
    
    if not args.confirm:
        count = db.query(User).filter(User.role != UserRole.admin).count()
        print(f"⚠️  This will grant {args.months} months premium to {count} users.")
        print(f"   Run with --confirm to execute.")
        return
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=args.months * 30)
    
    # Update mentors
    mentors = db.query(User).filter(
        User.role == UserRole.mentor,
        User.subscription_tier == SubscriptionTier.free
    ).all()
    
    for user in mentors:
        user.subscription_tier = SubscriptionTier.mentor_premium
        user.subscription_expires_at = expires_at
        user.subscription_platform = SubscriptionPlatform.admin_granted
        log_event(db, user, SubscriptionEventType.BETA_PREMIUM_GRANTED,
                  notes=f"Beta reward: {args.months} months premium")
    
    # Update apprentices
    apprentices = db.query(User).filter(
        User.role == UserRole.apprentice,
        User.subscription_tier == SubscriptionTier.free
    ).all()
    
    for user in apprentices:
        user.subscription_tier = SubscriptionTier.apprentice_premium
        user.subscription_expires_at = expires_at
        user.subscription_platform = SubscriptionPlatform.admin_granted
        log_event(db, user, SubscriptionEventType.BETA_PREMIUM_GRANTED,
                  notes=f"Beta reward: {args.months} months premium")
    
    db.commit()
    
    print(f"✅ Granted {args.months} months premium to:")
    print(f"   - {len(mentors)} mentors (mentor_premium)")
    print(f"   - {len(apprentices)} apprentices (apprentice_premium)")
    print(f"   Expires: {expires_at.isoformat()}")


def main():
    parser = argparse.ArgumentParser(description="Manage user subscriptions")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Grant command
    grant_parser = subparsers.add_parser("grant", help="Grant premium to a user")
    grant_parser.add_argument("--email", help="User email")
    grant_parser.add_argument("--user-id", help="User ID")
    grant_parser.add_argument("--months", type=int, default=6, help="Duration in months")
    grant_parser.add_argument("--lifetime", action="store_true", help="Grant lifetime premium")
    grant_parser.set_defaults(func=grant_premium)
    
    # Extend command
    extend_parser = subparsers.add_parser("extend", help="Extend existing subscription")
    extend_parser.add_argument("--email", help="User email")
    extend_parser.add_argument("--user-id", help="User ID")
    extend_parser.add_argument("--months", type=int, required=True, help="Months to add")
    extend_parser.set_defaults(func=extend_premium)
    
    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke premium from a user")
    revoke_parser.add_argument("--email", help="User email")
    revoke_parser.add_argument("--user-id", help="User ID")
    revoke_parser.set_defaults(func=revoke_premium)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check subscription status")
    status_parser.add_argument("--email", help="User email")
    status_parser.add_argument("--user-id", help="User ID")
    status_parser.set_defaults(func=check_status)
    
    # List premium command
    list_parser = subparsers.add_parser("list-premium", help="List all premium users")
    list_parser.set_defaults(func=list_premium)
    
    # Grant all command
    grant_all_parser = subparsers.add_parser("grant-all", help="Grant premium to all users")
    grant_all_parser.add_argument("--months", type=int, required=True, help="Duration in months")
    grant_all_parser.add_argument("--confirm", action="store_true", help="Confirm bulk operation")
    grant_all_parser.set_defaults(func=grant_all)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
