"""Add email_send_events table

Revision ID: 20250913_add_email_send_events_table
Revises: 20250913_add_version_to_assessment_templates
Create Date: 2025-09-13 12:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250913_add_email_send_events_table'
down_revision: Union[str, None] = '20250913_add_version_to_assessment_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'email_send_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('sender_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('target_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('assessment_id', sa.String(), sa.ForeignKey('assessments.id'), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('template_version', sa.Integer(), nullable=True),
        sa.Column('role_context', sa.String(), nullable=True),
        sa.Column('purpose', sa.String(), nullable=False, server_default='report'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_email_send_events_sender_created', 'email_send_events', ['sender_user_id', 'created_at'])
    op.create_index('ix_email_send_events_assessment', 'email_send_events', ['assessment_id'])


def downgrade() -> None:
    op.drop_index('ix_email_send_events_assessment', table_name='email_send_events')
    op.drop_index('ix_email_send_events_sender_created', table_name='email_send_events')
    op.drop_table('email_send_events')
