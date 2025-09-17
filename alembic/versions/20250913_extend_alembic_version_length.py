"""Extend alembic_version.version_num length

Revision ID: 20250913_extend_alembic_version_length
Revises: merge_20250911_heads
Create Date: 2025-09-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20250913_extend_alembic_version_length'
down_revision: Union[str, None] = 'merge_20250911_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Some existing DBs may already have alembic_version.version_num as VARCHAR(32).
    # We enlarge to 128 to accommodate long revision ids (e.g., timestamp-based) safely.
    with op.batch_alter_table('alembic_version') as batch_op:
        batch_op.alter_column('version_num', type_=sa.String(length=128))


def downgrade() -> None:
    # Shrinking back is unsafe if longer ids present; raise.
    raise RuntimeError('Downgrade not supported for alembic_version length change')
