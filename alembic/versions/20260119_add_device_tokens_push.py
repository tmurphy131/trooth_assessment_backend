"""Add device_tokens table for push notifications

Revision ID: add_device_tokens_push
Revises: 20260101_mentor_notes_updated
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_device_tokens_push'
down_revision = '20260101_mentor_notes_updated'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('fcm_token', sa.String(), nullable=False),
        sa.Column('platform', sa.Enum('ios', 'android', 'web', name='deviceplatform'), nullable=False),
        sa.Column('device_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.String(), nullable=True, default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_device_tokens_user_id', 'device_tokens', ['user_id'], unique=False)
    op.create_index('ix_device_tokens_fcm_token', 'device_tokens', ['fcm_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_device_tokens_fcm_token', table_name='device_tokens')
    op.drop_index('ix_device_tokens_user_id', table_name='device_tokens')
    op.drop_table('device_tokens')
    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS deviceplatform')
