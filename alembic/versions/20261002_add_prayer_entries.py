"""add prayer_entries table

Revision ID: 20261002_prayer_entries
Revises: a1b2c3d4e5f6
Create Date: 2026-10-02

"""
from alembic import op
import sqlalchemy as sa

revision = '20261002_prayer_entries'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'prayer_entries',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('apprentice_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=20), nullable=False, server_default='request'),
        sa.Column('praying_for', sa.String(length=120), nullable=True),
        sa.Column('scripture_ref', sa.String(length=120), nullable=True),
        sa.Column('shared_with_mentor', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('answered_at', sa.DateTime(), nullable=True),
        sa.Column('answer_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_prayer_entries_apprentice_id', 'prayer_entries', ['apprentice_id'])


def downgrade() -> None:
    op.drop_index('ix_prayer_entries_apprentice_id', table_name='prayer_entries')
    op.drop_table('prayer_entries')
