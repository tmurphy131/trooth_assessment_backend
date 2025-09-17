"""Merge heads after spiritual gifts additions

Revision ID: merge_20250913_heads
Revises: 20250913_add_email_send_events_table, merge_20250911_heads
Create Date: 2025-09-13
"""
from typing import Sequence, Union

# Alembic revision identifiers
revision: str = 'merge_20250913_heads'
down_revision: Union[str, tuple[str, ...], None] = (
    '20250913_add_email_send_events_table',
    'merge_20250911_heads',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # No schema changes; this is a merge point to unify divergent heads.
    pass

def downgrade() -> None:
    # Downgrading merge points is not supported safely.
    raise RuntimeError("Cannot downgrade merge revision merge_20250913_heads")
