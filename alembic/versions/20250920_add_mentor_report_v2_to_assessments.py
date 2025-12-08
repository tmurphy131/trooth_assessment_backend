"""add mentor_report_v2 to assessments

Revision ID: 20250920_add_mentor_report_v2
Revises: 20250917_add_status_updated_at_to_assessments
Create Date: 2025-09-20
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250920_add_mentor_report_v2'
down_revision = '20250917_add_status_updated_at_to_assessments'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('assessments') as batch_op:
        batch_op.add_column(sa.Column('mentor_report_v2', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('assessments') as batch_op:
        batch_op.drop_column('mentor_report_v2')
