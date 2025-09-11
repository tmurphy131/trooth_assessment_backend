"""
add mentor_resources table (link-only)

Revision ID: 20250911_add_mentor_resources
Revises: 20250911_add_mentor_profiles
Create Date: 2025-09-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250911_add_mentor_resources'
down_revision = '20250911_add_mentor_profiles'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mentor_resources',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('mentor_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('apprentice_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('link_url', sa.Text(), nullable=True),
        sa.Column('is_shared', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_mr_mentor', 'mentor_resources', ['mentor_id'])
    op.create_index('ix_mr_apprentice', 'mentor_resources', ['apprentice_id'])


def downgrade() -> None:
    op.drop_index('ix_mr_apprentice', table_name='mentor_resources')
    op.drop_index('ix_mr_mentor', table_name='mentor_resources')
    op.drop_table('mentor_resources')
