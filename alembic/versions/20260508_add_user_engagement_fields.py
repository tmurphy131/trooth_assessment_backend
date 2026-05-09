"""Add user engagement tracking fields

Revision ID: 20260508_add_user_engagement_fields
Revises: 20260203_seat_sub
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260508_add_user_engagement_fields'
down_revision = '20260203_seat_sub'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add fields for tracking user activity and push notification preferences."""
    
    # Add activity tracking
    op.add_column('users', 
        sa.Column('last_activity_at', sa.DateTime(), nullable=True)
    )
    
    # Add push notification preferences
    op.add_column('users', 
        sa.Column('push_enabled', sa.Boolean(), nullable=False, server_default='true')
    )
    op.add_column('users', 
        sa.Column('push_quiet_hours_start', sa.Integer(), nullable=True)
    )
    op.add_column('users', 
        sa.Column('push_quiet_hours_end', sa.Integer(), nullable=True)
    )
    op.add_column('users', 
        sa.Column('timezone', sa.String(100), nullable=True)
    )
    
    # Backfill last_activity_at from created_at for existing users
    # This gives existing users a baseline activity timestamp
    op.execute("""
        UPDATE users 
        SET last_activity_at = created_at 
        WHERE last_activity_at IS NULL
    """)


def downgrade() -> None:
    """Remove engagement tracking fields."""
    op.drop_column('users', 'timezone')
    op.drop_column('users', 'push_quiet_hours_end')
    op.drop_column('users', 'push_quiet_hours_start')
    op.drop_column('users', 'push_enabled')
    op.drop_column('users', 'last_activity_at')
