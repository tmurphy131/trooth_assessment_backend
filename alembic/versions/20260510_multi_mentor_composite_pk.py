"""support_multiple_mentors_per_apprentice

Revision ID: 20260510_multi_mentor
Revises: 20260509_merge_engagement_and_score_history
Create Date: 2026-05-10

Changes mentor_apprentice primary key from sole apprentice_id to composite
(apprentice_id, mentor_id), enabling an apprentice to have multiple active
mentor relationships simultaneously.
"""
from typing import Sequence, Union
from alembic import op

revision: str = '20260510_multi_mentor'
down_revision: Union[str, Sequence[str], None] = '20260509_merge_engagement_and_score_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the single-column PK on apprentice_id.
    # Existing data is safe — old schema guaranteed one row per apprentice,
    # so no duplicate (apprentice_id, mentor_id) pairs can exist.
    op.execute("ALTER TABLE mentor_apprentice DROP CONSTRAINT mentor_apprentice_pkey")
    op.create_primary_key(
        "mentor_apprentice_pkey",
        "mentor_apprentice",
        ["apprentice_id", "mentor_id"],
    )


def downgrade() -> None:
    op.execute("ALTER TABLE mentor_apprentice DROP CONSTRAINT mentor_apprentice_pkey")
    # Remove any duplicate apprentice rows before restoring single-column PK.
    op.execute("""
        DELETE FROM mentor_apprentice a
        USING mentor_apprentice b
        WHERE a.apprentice_id = b.apprentice_id
          AND a.mentor_id > b.mentor_id
    """)
    op.create_primary_key(
        "mentor_apprentice_pkey",
        "mentor_apprentice",
        ["apprentice_id"],
    )
