"""add_created_by_to_assessment_templates

Revision ID: 1f5966bf6735
Revises: f5ec2f6ab712
Create Date: 2025-08-03 23:31:56.104425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f5966bf6735'
down_revision: Union[str, None] = 'f5ec2f6ab712'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add created_by column to assessment_templates table
    op.add_column('assessment_templates', sa.Column('created_by', sa.String(), nullable=True))
    
    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_assessment_templates_created_by_users',
        'assessment_templates', 
        'users',
        ['created_by'], 
        ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint
    op.drop_constraint('fk_assessment_templates_created_by_users', 'assessment_templates', type_='foreignkey')
    
    # Drop created_by column
    op.drop_column('assessment_templates', 'created_by')
