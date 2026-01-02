"""add updated_at to mentor_notes

Revision ID: 20260101_mentor_notes_updated
Revises: 
Create Date: 2026-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260101_mentor_notes_updated'
down_revision: str = 'a345d98395e5_mentor_notes'  # Will be set by alembic
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at column to mentor_notes table."""
    op.add_column(
        'mentor_notes',
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()'))
    )


def downgrade() -> None:
    """Remove updated_at column from mentor_notes table."""
    op.drop_column('mentor_notes', 'updated_at')
