"""add_historical_context_fields

Revision ID: 74e5aeebece0
Revises: 20250920_add_mentor_report_v2
Create Date: 2025-11-18 22:26:02.592906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74e5aeebece0'
down_revision: Union[str, None] = '20250920_add_mentor_report_v2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add historical context tracking fields for assessments."""
    # Add previous_assessment_id to link assessment sequence
    op.add_column('assessments', sa.Column('previous_assessment_id', sa.String(), nullable=True))
    op.create_foreign_key('fk_assessment_previous', 'assessments', 'assessments', ['previous_assessment_id'], ['id'])
    op.create_index('ix_assessments_previous', 'assessments', ['previous_assessment_id'])
    
    # Add historical_summary JSON to store trend data from previous assessments
    op.add_column('assessments', sa.Column('historical_summary', sa.JSON(), nullable=True))
    
    # Add assessment_count to users for quick tracking (denormalized for performance)
    op.add_column('users', sa.Column('assessment_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    """Remove historical context tracking fields."""
    op.drop_column('users', 'assessment_count')
    op.drop_column('assessments', 'historical_summary')
    op.drop_index('ix_assessments_previous', 'assessments')
    op.drop_constraint('fk_assessment_previous', 'assessments', type_='foreignkey')
    op.drop_column('assessments', 'previous_assessment_id')
