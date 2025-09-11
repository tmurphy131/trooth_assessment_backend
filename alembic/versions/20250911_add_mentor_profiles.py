"""
add mentor_profiles table

Revision ID: 20250911_add_mentor_profiles
Revises: f5ec2f6ab712_add_question_types_and_options
Create Date: 2025-09-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250911_add_mentor_profiles'
down_revision = 'f5ec2f6ab712'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mentor_profiles',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('role_title', sa.String(), nullable=True),
        sa.Column('organization', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.UniqueConstraint('user_id', name='uq_mentor_profile_user_id')
    )
    op.create_index('ix_mentor_profiles_user_id', 'mentor_profiles', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_mentor_profiles_user_id', table_name='mentor_profiles')
    op.drop_table('mentor_profiles')
