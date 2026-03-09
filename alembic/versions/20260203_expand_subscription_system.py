"""Expand subscription system with 4-tier enum, new columns, and gift seats

Revision ID: 20260203_expand_subscription_system
Revises: 08d60ff3eee2
Create Date: 2026-02-03

This migration:
1. Expands SubscriptionTier enum from 2 values (free, premium) to 4 values
2. Adds new subscription metadata columns to users table
3. Creates mentor_premium_seats table for gift codes
4. Creates subscription_events table for audit logging

NOTE: The data migration (granting 6 months premium to existing users) is handled
in a separate migration (20260203_grant_beta_premium) because PostgreSQL requires
new enum values to be committed before they can be used.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260203_expand_subscription_system'
down_revision = '08d60ff3eee2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Step 1: Add new enum values to subscriptiontier
    # PostgreSQL requires special handling - must commit before using new values
    # Using connection.execute with COMMIT to make values available immediately
    # ==========================================================================
    
    # Add the new enum values (these need to be committed before use)
    op.execute("ALTER TYPE subscriptiontier ADD VALUE IF NOT EXISTS 'mentor_premium'")
    op.execute("ALTER TYPE subscriptiontier ADD VALUE IF NOT EXISTS 'apprentice_premium'")
    op.execute("ALTER TYPE subscriptiontier ADD VALUE IF NOT EXISTS 'mentor_gifted'")
    
    # ==========================================================================
    # Step 2: Create subscriptionplatform enum
    # ==========================================================================
    subscription_platform_enum = sa.Enum(
        'apple', 'google', 'gifted', 'admin_granted', 
        name='subscriptionplatform'
    )
    subscription_platform_enum.create(op.get_bind(), checkfirst=True)
    
    # ==========================================================================
    # Step 3: Add new columns to users table
    # ==========================================================================
    op.add_column('users', sa.Column(
        'subscription_expires_at', 
        sa.DateTime(), 
        nullable=True
    ))
    
    op.add_column('users', sa.Column(
        'subscription_platform',
        sa.Enum('apple', 'google', 'gifted', 'admin_granted', name='subscriptionplatform'),
        nullable=True
    ))
    
    op.add_column('users', sa.Column(
        'revenuecat_customer_id',
        sa.String(255),
        nullable=True
    ))
    
    op.add_column('users', sa.Column(
        'subscription_auto_renew',
        sa.Boolean(),
        nullable=False,
        server_default='false'
    ))
    
    op.add_column('users', sa.Column(
        'is_grandfathered_mentor',
        sa.Boolean(),
        nullable=False,
        server_default='false'
    ))
    
    # Add index for RevenueCat customer ID lookups
    op.create_index(
        'ix_users_revenuecat_customer_id',
        'users',
        ['revenuecat_customer_id'],
        unique=False
    )
    
    # ==========================================================================
    # Step 4: Create mentor_premium_seats table
    # ==========================================================================
    op.create_table(
        'mentor_premium_seats',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('mentor_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('apprentice_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('redemption_code', sa.String(20), unique=True, nullable=False),
        sa.Column('is_redeemed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('redeemed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.Column('deactivation_reason', sa.String(100), nullable=True),
    )
    
    op.create_index('ix_mentor_premium_seats_mentor_id', 'mentor_premium_seats', ['mentor_id'])
    op.create_index('ix_mentor_premium_seats_apprentice_id', 'mentor_premium_seats', ['apprentice_id'])
    op.create_index('ix_mentor_premium_seats_redemption_code', 'mentor_premium_seats', ['redemption_code'])
    
    # ==========================================================================
    # Step 5: Create subscription_events table
    # ==========================================================================
    op.create_table(
        'subscription_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('platform', sa.String(20), nullable=True),
        sa.Column('product_id', sa.String(100), nullable=True),
        sa.Column('revenuecat_event_id', sa.String(255), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('triggered_by_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    op.create_index('ix_subscription_events_user_id', 'subscription_events', ['user_id'])
    op.create_index('ix_subscription_events_event_type', 'subscription_events', ['event_type'])
    op.create_index('ix_subscription_events_revenuecat_event_id', 'subscription_events', ['revenuecat_event_id'])
    op.create_index('ix_subscription_events_created_at', 'subscription_events', ['created_at'])


def downgrade() -> None:
    # ==========================================================================
    # Reverse all changes
    # ==========================================================================
    
    # Drop new tables
    op.drop_table('subscription_events')
    op.drop_table('mentor_premium_seats')
    
    # Drop index
    op.drop_index('ix_users_revenuecat_customer_id', table_name='users')
    
    # Drop new columns
    op.drop_column('users', 'is_grandfathered_mentor')
    op.drop_column('users', 'subscription_auto_renew')
    op.drop_column('users', 'revenuecat_customer_id')
    op.drop_column('users', 'subscription_platform')
    op.drop_column('users', 'subscription_expires_at')
    
    # Drop subscriptionplatform enum
    subscription_platform_enum = sa.Enum('apple', 'google', 'gifted', 'admin_granted', name='subscriptionplatform')
    subscription_platform_enum.drop(op.get_bind(), checkfirst=True)
    
    # Note: We cannot remove enum values from PostgreSQL, so mentor_premium, 
    # apprentice_premium, mentor_gifted will remain in the enum type.
    # This is a PostgreSQL limitation.
