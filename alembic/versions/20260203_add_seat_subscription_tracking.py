"""Add subscription tracking to mentor_premium_seats

Revision ID: 20260203_seat_sub
Revises: 20260203_expand_subscription_system
Create Date: 2026-02-03

Adds columns to track individual RevenueCat subscriptions per gift seat
for per-seat IAP billing.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260203_seat_sub'
down_revision = '20260203_grant_beta_premium'
branch_labels = None
depends_on = None


def upgrade():
    # Add RevenueCat subscription tracking columns to mentor_premium_seats
    op.add_column('mentor_premium_seats', 
        sa.Column('revenuecat_subscription_id', sa.String(255), nullable=True))
    op.add_column('mentor_premium_seats', 
        sa.Column('revenuecat_product_id', sa.String(100), nullable=True))
    op.add_column('mentor_premium_seats', 
        sa.Column('subscription_platform', sa.String(20), nullable=True))
    
    # Add apprentice info columns for pre-redemption assignment
    # These store the intended apprentice before they create an account
    op.add_column('mentor_premium_seats',
        sa.Column('apprentice_email', sa.String(255), nullable=True))
    op.add_column('mentor_premium_seats',
        sa.Column('apprentice_name', sa.String(255), nullable=True))
    
    # Add index for subscription ID lookups (webhook handling)
    op.create_index('ix_mentor_premium_seats_rc_sub_id', 
                    'mentor_premium_seats', ['revenuecat_subscription_id'])


def downgrade():
    op.drop_index('ix_mentor_premium_seats_rc_sub_id', table_name='mentor_premium_seats')
    op.drop_column('mentor_premium_seats', 'apprentice_name')
    op.drop_column('mentor_premium_seats', 'apprentice_email')
    op.drop_column('mentor_premium_seats', 'subscription_platform')
    op.drop_column('mentor_premium_seats', 'revenuecat_product_id')
    op.drop_column('mentor_premium_seats', 'revenuecat_subscription_id')
