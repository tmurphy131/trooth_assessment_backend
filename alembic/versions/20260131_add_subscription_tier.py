"""Add subscription_tier column to users table

Revision ID: 20260131_add_subscription_tier
Revises: add_device_tokens_push
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260131_add_subscription_tier'
down_revision = 'add_device_tokens_push'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the enum type first (PostgreSQL specific)
    subscription_tier_enum = sa.Enum('free', 'premium', name='subscriptiontier')
    subscription_tier_enum.create(op.get_bind(), checkfirst=True)
    
    # Add the column with default value 'free'
    op.add_column(
        'users',
        sa.Column(
            'subscription_tier',
            sa.Enum('free', 'premium', name='subscriptiontier'),
            nullable=False,
            server_default='free'
        )
    )


def downgrade() -> None:
    # Remove the column
    op.drop_column('users', 'subscription_tier')
    
    # Drop the enum type (PostgreSQL specific)
    subscription_tier_enum = sa.Enum('free', 'premium', name='subscriptiontier')
    subscription_tier_enum.drop(op.get_bind(), checkfirst=True)
