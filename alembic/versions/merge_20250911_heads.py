"""Merge heads: resources and apprentice_name

Revision ID: merge_20250911_heads
Revises: 20250911_add_mentor_resources, 20250908_add_apprentice_name
Create Date: 2025-09-11

"""
from typing import Sequence, Union

from alembic import op  # noqa: F401  (kept for consistency, even if unused)
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = 'merge_20250911_heads'
down_revision: Union[str, tuple[str, ...], None] = (
    '20250911_add_mentor_resources',
    '20250908_add_apprentice_name',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op merge migration to unify heads."""
    pass


def downgrade() -> None:
    """No-op on downgrade as this is just a merge point."""
    pass
