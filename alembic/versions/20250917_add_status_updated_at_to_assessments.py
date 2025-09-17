"""Add status and updated_at columns to assessments

Revision ID: 20250917_add_status_updated_at_to_assessments
Revises: 20250916_add_generic_template_columns
Create Date: 2025-09-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250917_add_status_updated_at_to_assessments"
down_revision: Union[str, None] = "20250916_add_generic_template_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding status and updated_at to assessments."""
    op.add_column("assessments", sa.Column("status", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("updated_at", sa.DateTime(), nullable=True))



def downgrade() -> None:
    """Downgrade schema by removing status and updated_at from assessments."""
    op.drop_column("assessments", "updated_at")
    op.drop_column("assessments", "status")
