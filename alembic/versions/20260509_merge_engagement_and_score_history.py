"""Merge engagement migrations with score history branch

Revision ID: 20260509_merge_engagement_and_score_history
Revises: 20260508_expand_email_tracking, 2f136a5c8971
Create Date: 2026-05-09

"""
from typing import Sequence, Union
from alembic import op

revision: str = '20260509_merge_engagement_and_score_history'
down_revision: Union[str, Sequence[str], None] = (
    '20260508_expand_email_tracking',
    '2f136a5c8971',
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
