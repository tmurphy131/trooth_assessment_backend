"""Add unique constraint to spiritual_gift_definitions

Revision ID: 20250913_add_unique_constraint_gift_definitions
Revises: merge_20250911_heads
Create Date: 2025-09-13 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250913_add_unique_constraint_gift_definitions'
down_revision: Union[str, None] = '20250913_extend_alembic_version_length'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create table if it does not already exist (deployment env may have missed earlier additive migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'spiritual_gift_definitions' not in inspector.get_table_names():
        op.create_table(
            'spiritual_gift_definitions',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('gift_slug', sa.String(length=64), nullable=False),
            sa.Column('display_name', sa.String(length=120), nullable=False),
            sa.Column('short_summary', sa.String(length=500), nullable=True),
            sa.Column('full_definition', sa.Text(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1')),
            sa.Column('locale', sa.String(length=8), nullable=False, server_default=sa.text("'en'")),
        )
    # Add unique constraint (idempotent check: only if not already present)
    existing = [uc['name'] for uc in inspector.get_unique_constraints('spiritual_gift_definitions')]
    if 'uq_gift_slug_version_locale' not in existing:
        op.create_unique_constraint(
            'uq_gift_slug_version_locale',
            'spiritual_gift_definitions',
            ['gift_slug', 'version', 'locale']
        )


def downgrade() -> None:
    op.drop_constraint('uq_gift_slug_version_locale', 'spiritual_gift_definitions', type_='unique')
