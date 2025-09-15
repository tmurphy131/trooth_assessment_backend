"""Add version column to assessment_templates

Revision ID: 20250913_add_version_to_assessment_templates
Revises: 20250913_add_unique_constraint_gift_definitions
Create Date: 2025-09-13 00:05:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250913_add_version_to_assessment_templates'
down_revision: Union[str, None] = '20250913_add_unique_constraint_gift_definitions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('assessment_templates', sa.Column('version', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('assessment_templates', 'version')
