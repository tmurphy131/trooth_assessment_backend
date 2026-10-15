"""Question ownership: questions.created_by + one-time attribution (specs/010-question-ownership).

Revision ID: 20261014_question_owner
Revises: 20261013_invite_codes
"""
import sqlalchemy as sa
from alembic import op

revision = '20261014_question_owner'
down_revision = '20261013_invite_codes'
branch_labels = None
depends_on = None

# Attribute a question to a mentor only when it's unambiguous: every template using it was
# created by that one mentor, and none of them is the Master assessment. Shared, unused or
# multi-owner questions stay NULL (admin-managed). Idempotent: only fills NULLs.
BACKFILL_SQL = """
UPDATE questions
SET created_by = sub.owner
FROM (
    SELECT atq.question_id, MIN(t.created_by) AS owner
    FROM assessment_template_questions atq
    JOIN assessment_templates t ON t.id = atq.template_id
    GROUP BY atq.question_id
    HAVING COUNT(*) = COUNT(t.created_by)
       AND COUNT(DISTINCT t.created_by) = 1
       AND SUM(CASE WHEN t.is_master_assessment THEN 1 ELSE 0 END) = 0
) AS sub
JOIN users u ON u.id = sub.owner AND u.role = 'mentor'
WHERE questions.id = sub.question_id
  AND questions.created_by IS NULL
"""


def upgrade():
    op.add_column('questions', sa.Column('created_by', sa.String(), nullable=True))
    op.create_foreign_key('fk_questions_created_by_users', 'questions', 'users',
                          ['created_by'], ['id'], ondelete='SET NULL')
    op.create_index('ix_questions_created_by', 'questions', ['created_by'])
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(BACKFILL_SQL)


def downgrade():
    op.drop_index('ix_questions_created_by', table_name='questions')
    op.drop_constraint('fk_questions_created_by_users', 'questions', type_='foreignkey')
    op.drop_column('questions', 'created_by')
