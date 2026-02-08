"""Grant 6 months beta premium to all existing users

Revision ID: 20260203_grant_beta_premium
Revises: 20260203_expand_subscription_system
Create Date: 2026-02-03

This migration runs AFTER the enum values have been committed in the previous
migration. It:
1. Migrates existing 'premium' users to new tier based on role
2. Grants 6 months free premium to ALL existing users as beta reward
3. Grandfathers existing mentors with >1 apprentice
"""
from alembic import op
from datetime import datetime, timezone, timedelta


# revision identifiers, used by Alembic.
revision = '20260203_grant_beta_premium'
down_revision = '20260203_expand_subscription_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Calculate expiration date (6 months from now)
    six_months_from_now = datetime.now(timezone.utc) + timedelta(days=180)
    expiration_str = six_months_from_now.strftime('%Y-%m-%d %H:%M:%S')
    
    # ==========================================================================
    # Step 1: Migrate any existing 'premium' users to role-appropriate tier
    # (This handles anyone who was manually set to premium before this migration)
    # ==========================================================================
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'mentor_premium',
            subscription_platform = 'admin_granted',
            subscription_expires_at = '%s'
        WHERE subscription_tier = 'premium' AND role = 'mentor'
    """ % expiration_str)
    
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'apprentice_premium',
            subscription_platform = 'admin_granted', 
            subscription_expires_at = '%s'
        WHERE subscription_tier = 'premium' AND role = 'apprentice'
    """ % expiration_str)
    
    # ==========================================================================
    # Step 2: Grant 6 months premium to ALL existing 'free' users as beta reward
    # ==========================================================================
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'mentor_premium',
            subscription_platform = 'admin_granted',
            subscription_expires_at = '%s'
        WHERE subscription_tier = 'free' AND role = 'mentor'
    """ % expiration_str)
    
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'apprentice_premium',
            subscription_platform = 'admin_granted',
            subscription_expires_at = '%s'
        WHERE subscription_tier = 'free' AND role = 'apprentice'
    """ % expiration_str)
    
    # ==========================================================================
    # Step 3: Admins get indefinite premium (no expiration)
    # ==========================================================================
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'mentor_premium',
            subscription_platform = 'admin_granted',
            subscription_expires_at = NULL
        WHERE role = 'admin'
    """)
    
    # ==========================================================================
    # Step 4: Grandfather existing mentors with >1 apprentice
    # ==========================================================================
    op.execute("""
        UPDATE users u
        SET is_grandfathered_mentor = true
        WHERE u.role = 'mentor'
        AND (
            SELECT COUNT(*) 
            FROM mentor_apprentice ma 
            WHERE ma.mentor_id = u.id
        ) > 1
    """)


def downgrade() -> None:
    # Reset grandfathered status
    op.execute("UPDATE users SET is_grandfathered_mentor = false")
    
    # Migrate users back to simple 'free' or 'premium'
    # All premium tiers become 'premium', all else becomes 'free'
    op.execute("""
        UPDATE users 
        SET subscription_tier = 'premium',
            subscription_platform = NULL,
            subscription_expires_at = NULL
        WHERE subscription_tier IN ('mentor_premium', 'apprentice_premium', 'mentor_gifted')
    """)
