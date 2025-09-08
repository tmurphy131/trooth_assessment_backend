"""add apprentice_name column to agreements

Revision ID: 20250908_add_apprentice_name
Revises: 20250902_add_agreements
Create Date: 2025-09-08
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250908_add_apprentice_name'
down_revision = '20250902_add_agreements'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('agreements') as batch_op:
        batch_op.add_column(sa.Column('apprentice_name', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('agreements') as batch_op:
        batch_op.drop_column('apprentice_name')
