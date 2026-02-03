"""change assessment_draft score column from Float to JSON

Revision ID: 08d60ff3eee2
Revises: 
Create Date: 2026-02-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '08d60ff3eee2'
down_revision = '20260131_add_subscription_tier'  # Latest merge head
branch_labels = None
depends_on = None


def upgrade():
    # Change score column from Float to JSON
    # First drop the Float column, then add JSON column
    # This will lose existing Float scores, but they were likely not meaningful
    # since the code was already trying to store JSON data
    
    # Using PostgreSQL-specific USING clause to handle the conversion
    op.execute('''
        ALTER TABLE assessment_drafts 
        ALTER COLUMN score TYPE JSON 
        USING CASE 
            WHEN score IS NULL THEN NULL 
            ELSE ('{"legacy_score": ' || score::text || '}')::json 
        END
    ''')


def downgrade():
    # Convert back to Float (will lose JSON data)
    op.execute('''
        ALTER TABLE assessment_drafts 
        ALTER COLUMN score TYPE FLOAT 
        USING NULL
    ''')
