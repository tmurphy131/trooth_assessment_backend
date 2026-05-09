"""Expand email tracking for campaigns

Revision ID: 20260508_expand_email_tracking
Revises: 20260508_add_user_engagement_fields
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260508_expand_email_tracking'
down_revision = '20260508_add_user_engagement_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add campaign tracking fields to email_send_events table."""
    
    # Add campaign type for easier filtering
    op.add_column('email_send_events', 
        sa.Column('campaign_type', sa.String(100), nullable=True)
    )
    
    # Add flexible context field for storing campaign-specific metadata
    # e.g., {'draft_id': '123', 'days_since_start': 5, 'progress_percent': 60}
    op.add_column('email_send_events', 
        sa.Column('context', sa.JSON(), nullable=True)
    )
    
    # Track delivery status for monitoring campaign effectiveness
    op.add_column('email_send_events', 
        sa.Column('delivery_status', sa.String(50), nullable=True, server_default='sent')
    )
    
    # Create index for efficient campaign analytics queries
    op.create_index(
        'ix_email_send_events_campaign', 
        'email_send_events', 
        ['campaign_type', 'created_at']
    )


def downgrade() -> None:
    """Remove campaign tracking fields."""
    op.drop_index('ix_email_send_events_campaign', table_name='email_send_events')
    op.drop_column('email_send_events', 'delivery_status')
    op.drop_column('email_send_events', 'context')
    op.drop_column('email_send_events', 'campaign_type')
