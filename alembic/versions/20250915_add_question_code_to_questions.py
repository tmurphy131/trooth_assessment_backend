"""Add question_code to questions

Revision ID: 20250915_add_question_code
Revises: f5ec2f6ab712
Create Date: 2025-09-15

Purpose:
    Introduces a stable, human-readable, immutable code for each question (initially used for the 72 Spiritual Gifts items).

Notes:
    Because Spiritual Gifts questions have not yet been seeded in production, we apply NOT NULL directly.
    If any environment unexpectedly already has rows that need backfill, temporarily adjust to nullable=True and perform backfill prior to enforcing NOT NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250915_add_question_code"
# Attach after the latest merge head to avoid creating a new branch.
down_revision: Union[str, None] = "merge_20250913_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding question_code column and unique constraint.

    Strategy:
      1. Add column nullable (to avoid NOT NULL violation on existing rows).
      2. Backfill codes for any existing questions (synthetic codes if none set).
      3. Enforce NOT NULL and unique constraint.

    Backfill scheme (only for pre-existing rows): QLEGACY0001, QLEGACY0002 ... in creation order.
    These will not collide with reserved assessment codes (Q01..Q72) which are shorter and zero-padded to 2 digits.
    """
    conn = op.get_bind()
    op.add_column("questions", sa.Column("question_code", sa.String(length=32), nullable=True))

    # Fetch existing rows lacking a code (all, since column new)
    # Order deterministically. Prefer created_at if it exists, otherwise fall back to id.
    inspector = sa.inspect(conn)
    question_cols = {c['name'] for c in inspector.get_columns('questions')}
    if 'created_at' in question_cols:
        ordering_sql = "created_at NULLS LAST, id"
    else:
        ordering_sql = "id"
    existing = conn.execute(sa.text(f"SELECT id FROM questions ORDER BY {ordering_sql}"))
    rows = [r[0] for r in existing]
    if rows:
        # Generate deterministic legacy codes
        updates = []
        for idx, qid in enumerate(rows, start=1):
            code = f"QLEGACY{idx:04d}"
            updates.append({"id": qid, "code": code})
        for u in updates:
            conn.execute(sa.text("UPDATE questions SET question_code = :code WHERE id = :id"), u)

    # Now enforce NOT NULL
    op.alter_column("questions", "question_code", existing_type=sa.String(length=32), nullable=False)
    # Add unique constraint
    op.create_unique_constraint("uq_questions_question_code", "questions", ["question_code"])


def downgrade() -> None:
    """Downgrade schema by removing question_code column and constraint.

    Warning: This will drop any legacy codes assigned; irreversible for data semantics.
    """
    op.drop_constraint("uq_questions_question_code", "questions", type_="unique")
    op.drop_column("questions", "question_code")
