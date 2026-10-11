"""durable scoring state on assessments (spec 004-reliable-ai-reports)

Revision ID: 20261011_scoring_state
Revises: 20261008_daily_trivia
Create Date: 2026-10-11

"""
from alembic import op
import sqlalchemy as sa

revision = '20261011_scoring_state'
down_revision = '20261008_daily_trivia'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('assessments', sa.Column('scoring_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('assessments', sa.Column('scoring_queued_at', sa.DateTime(), nullable=True))
    op.add_column('assessments', sa.Column('scoring_lease_until', sa.DateTime(), nullable=True))
    op.add_column('assessments', sa.Column('scoring_completed_at', sa.DateTime(), nullable=True))
    op.add_column('assessments', sa.Column('failure_reason', sa.String(length=300), nullable=True))
    op.add_column('assessments', sa.Column('full_report_status', sa.String(length=16), nullable=True))
    op.add_column('assessments', sa.Column('full_report_claimed_at', sa.DateTime(), nullable=True))

    op.execute("UPDATE assessments SET scoring_queued_at = created_at WHERE scoring_queued_at IS NULL")
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(
            "UPDATE assessments SET full_report_status = 'ready' "
            "WHERE scores IS NOT NULL AND (scores::jsonb ? 'full_report_v1')"
        )


def downgrade() -> None:
    for column in ('full_report_claimed_at', 'full_report_status', 'failure_reason', 'scoring_completed_at',
                   'scoring_lease_until', 'scoring_queued_at', 'scoring_attempts'):
        op.drop_column('assessments', column)
