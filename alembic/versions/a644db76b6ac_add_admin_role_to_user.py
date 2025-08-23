"""Add admin role to User

Revision ID: a644db76b6ac
Revises: 70420600a9a9
Create Date: 2025-06-25 02:53:07.825473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a644db76b6ac'
down_revision: Union[str, None] = '70420600a9a9'

def upgrade() -> None:
    # Create enum type explicitly
    user_role_enum = sa.Enum('apprentice', 'mentor', 'admin', name='userrole')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # Change column type using USING clause for PostgreSQL
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole;")

def downgrade() -> None:
    op.alter_column('users', 'role',
        existing_type=sa.Enum('apprentice', 'mentor', 'admin', name='userrole'),
        type_=sa.VARCHAR(),
        existing_nullable=False
    )
    op.execute("DROP TYPE userrole;")

    # ### end Alembic commands ###
