"""merge heads

Revision ID: merge_291f_a345
Revises: 291f1327838b, a345d98395e5
Create Date: 2025-08-25 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_291f_a345'
down_revision: Union[str, Sequence[str], None] = ('291f1327838b', 'a345d98395e5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads: no schema changes, just unify branches."""
    # This is an empty merge migration; it only sets Alembic's head to the merge rev.
    pass


def downgrade() -> None:
    """Downgrade: non-trivial in merge; raise to avoid accidental downgrade."""
    raise RuntimeError("Cannot downgrade a merge migration safely")
