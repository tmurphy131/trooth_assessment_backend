"""Add generic template columns to assessment_templates

Revision ID: 20250916_add_generic_template_columns
Revises: 20250915_add_question_code
Create Date: 2025-09-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250916_add_generic_template_columns"
down_revision: Union[str, None] = "20250915_add_question_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding generic template columns used for scoring/reporting."""
    op.add_column("assessment_templates", sa.Column("key", sa.String(), nullable=True))
    op.add_column("assessment_templates", sa.Column("scoring_strategy", sa.String(), nullable=True))
    op.add_column("assessment_templates", sa.Column("rubric_json", sa.JSON(), nullable=True))
    op.add_column("assessment_templates", sa.Column("report_template", sa.String(), nullable=True))
    op.add_column("assessment_templates", sa.Column("pdf_renderer", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema by removing the generic template columns."""
    op.drop_column("assessment_templates", "pdf_renderer")
    op.drop_column("assessment_templates", "report_template")
    op.drop_column("assessment_templates", "rubric_json")
    op.drop_column("assessment_templates", "scoring_strategy")
    op.drop_column("assessment_templates", "key")
