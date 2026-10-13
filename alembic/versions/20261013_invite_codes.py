"""Invite codes: apprentice_invitations.code + invite_code_attempts (specs/006-invite-codes).

Revision ID: 20261013_invite_codes
Revises: 20261012_email_prefs
"""
import secrets

import sqlalchemy as sa
from alembic import op

revision = '20261013_invite_codes'
down_revision = '20261012_email_prefs'
branch_labels = None
depends_on = None

# Own copy of the generator on purpose: migrations must not import app code,
# which can change after this migration is written.
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_LENGTH = 8


def _new_code(used):
    while True:
        code = "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))
        if code not in used:
            used.add(code)
            return code


def upgrade():
    op.add_column('apprentice_invitations', sa.Column('code', sa.String(length=8), nullable=True))

    conn = op.get_bind()
    ids = [row[0] for row in conn.execute(sa.text("SELECT id FROM apprentice_invitations"))]
    used = set()
    for invitation_id in ids:
        conn.execute(
            sa.text("UPDATE apprentice_invitations SET code = :code WHERE id = :id"),
            {"code": _new_code(used), "id": invitation_id},
        )

    op.alter_column('apprentice_invitations', 'code', existing_type=sa.String(length=8), nullable=False)
    op.create_index('ix_apprentice_invitations_code', 'apprentice_invitations', ['code'], unique=True)

    op.create_table(
        'invite_code_attempts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invitation_id', sa.String(), nullable=True),
        sa.Column('succeeded', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_invite_code_attempts_user_created', 'invite_code_attempts', ['user_id', 'created_at'])


def downgrade():
    op.drop_index('ix_invite_code_attempts_user_created', table_name='invite_code_attempts')
    op.drop_table('invite_code_attempts')
    op.drop_index('ix_apprentice_invitations_code', table_name='apprentice_invitations')
    op.drop_column('apprentice_invitations', 'code')
