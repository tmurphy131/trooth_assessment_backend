"""Engagement-email opt-out on users (specs/005-email-redesign).

Revision ID: 20261012_email_prefs
Revises: 20261011_scoring_state
"""
import sqlalchemy as sa
from alembic import op

revision = '20261012_email_prefs'
down_revision = '20261011_scoring_state'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('email_opt_out', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('email_pref_changed_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('email_pref_source', sa.String(length=16), nullable=True))


def downgrade():
    op.drop_column('users', 'email_pref_source')
    op.drop_column('users', 'email_pref_changed_at')
    op.drop_column('users', 'email_opt_out')
