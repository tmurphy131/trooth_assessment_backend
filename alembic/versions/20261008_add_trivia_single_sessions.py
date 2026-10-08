"""add server-run trivia single-player sessions + verified scores

Revision ID: 20261008_trivia_single_sessions
Revises: 20261003_trivia_competitions
Create Date: 2026-10-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261008_trivia_single_sessions'
down_revision = '20261003_trivia_competitions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # triviacategory / triviadifficulty already exist (a1b2c3d4e5f6) — reuse them,
    # never CREATE TYPE again. Only the session status type is new.
    triviacategory = postgresql.ENUM(
        'old_testament', 'new_testament', 'theology_doctrine', 'discipleship_living', 'random',
        name='triviacategory', create_type=False,
    )
    triviadifficulty = postgresql.ENUM(
        'beginner', 'challenger', 'expert',
        name='triviadifficulty', create_type=False,
    )
    triviasessionstatus = postgresql.ENUM(
        'active', 'awaiting_grace', 'finished',
        name='triviasessionstatus', create_type=False,
    )
    triviasessionstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'trivia_single_sessions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('category', triviacategory, nullable=False),
        sa.Column('difficulty', triviadifficulty, nullable=False),
        sa.Column('question_ids', sa.JSON(), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_question', sa.JSON(), nullable=True),
        sa.Column('current_served_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('grace_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('grace_tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('grace_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', triviasessionstatus, nullable=False, server_default='active'),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_trivia_single_sessions_user_id', 'trivia_single_sessions', ['user_id'])
    op.create_index('ix_trivia_single_sessions_status', 'trivia_single_sessions', ['status'])

    op.add_column(
        'trivia_single_scores',
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'trivia_single_scores',
        sa.Column('session_id', sa.String(), sa.ForeignKey('trivia_single_sessions.id'), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('trivia_single_scores', 'session_id')
    op.drop_column('trivia_single_scores', 'verified')
    op.drop_index('ix_trivia_single_sessions_status', table_name='trivia_single_sessions')
    op.drop_index('ix_trivia_single_sessions_user_id', table_name='trivia_single_sessions')
    op.drop_table('trivia_single_sessions')
    # Only the type this migration created — triviacategory/difficulty belong to a1b2c3d4e5f6
    postgresql.ENUM(name='triviasessionstatus').drop(op.get_bind(), checkfirst=True)
