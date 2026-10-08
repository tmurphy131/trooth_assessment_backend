"""add daily trivia question, answers, streaks and streak rewards (spec 002)

Revision ID: 20261008_daily_trivia
Revises: 20261008_trivia_single_sessions
Create Date: 2026-10-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261008_daily_trivia'
down_revision = '20261008_trivia_single_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The trivia enums already exist (a1b2c3d4e5f6) — reuse them, never CREATE TYPE again.
    triviacategory = postgresql.ENUM(
        'old_testament', 'new_testament', 'theology_doctrine', 'discipleship_living', 'random',
        name='triviacategory', create_type=False,
    )
    triviadifficulty = postgresql.ENUM(
        'beginner', 'challenger', 'expert',
        name='triviadifficulty', create_type=False,
    )
    triviaquestiontype = postgresql.ENUM(
        'multiple_choice', 'true_false',
        name='triviaquestiontype', create_type=False,
    )
    rewardstatus = postgresql.ENUM(
        'pending', 'active', 'superseded', 'expired',
        name='dailytriviarewardstatus', create_type=False,
    )
    rewardstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'daily_trivia_questions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('question_id', sa.Integer(), sa.ForeignKey('trivia_questions.id'), nullable=False),
        sa.Column('category', triviacategory, nullable=False),
        sa.Column('difficulty', triviadifficulty, nullable=False),
        sa.Column('question_type', triviaquestiontype, nullable=False),
        sa.Column('question_text', sa.String(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=False),
        sa.Column('correct_option', sa.String(1), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_daily_trivia_questions_date', 'daily_trivia_questions', ['date'], unique=True)
    op.create_index('ix_daily_trivia_questions_question_id', 'daily_trivia_questions', ['question_id'])

    op.create_table(
        'daily_trivia_answers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('daily_question_id', sa.Integer(), sa.ForeignKey('daily_trivia_questions.id'), nullable=False),
        sa.Column('selected_option', sa.String(1), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('user_id', 'date', name='uq_daily_trivia_answer_user_date'),
    )
    op.create_index('ix_daily_trivia_answers_user_id', 'daily_trivia_answers', ['user_id'])

    op.create_table(
        'daily_trivia_streaks',
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('longest_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_answered_date', sa.Date(), nullable=True),
        sa.Column('streak_started_on', sa.Date(), nullable=True),
        sa.Column('freezes_available', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('perfect_run', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('freeze_dates', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('tiers_earned', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('last_reminded_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'daily_trivia_rewards',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('streak_started_on', sa.Date(), nullable=False),
        sa.Column('tier', sa.Integer(), nullable=False),
        sa.Column('percent', sa.Integer(), nullable=False),
        sa.Column('perfect', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('status', rewardstatus, nullable=False, server_default='pending'),
        sa.Column('discount_code', sa.String(), nullable=True),
        sa.Column('shopify_discount_id', sa.String(), nullable=True),
        sa.Column('replaces_reward_id', sa.Integer(), sa.ForeignKey('daily_trivia_rewards.id'), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('emailed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pushed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('user_id', 'streak_started_on', 'tier', name='uq_daily_trivia_reward_streak_tier'),
    )
    op.create_index('ix_daily_trivia_rewards_user_id', 'daily_trivia_rewards', ['user_id'])
    op.create_index('ix_daily_trivia_rewards_status', 'daily_trivia_rewards', ['status'])


def downgrade() -> None:
    op.drop_index('ix_daily_trivia_rewards_status', table_name='daily_trivia_rewards')
    op.drop_index('ix_daily_trivia_rewards_user_id', table_name='daily_trivia_rewards')
    op.drop_table('daily_trivia_rewards')
    op.drop_table('daily_trivia_streaks')
    op.drop_index('ix_daily_trivia_answers_user_id', table_name='daily_trivia_answers')
    op.drop_table('daily_trivia_answers')
    op.drop_index('ix_daily_trivia_questions_question_id', table_name='daily_trivia_questions')
    op.drop_index('ix_daily_trivia_questions_date', table_name='daily_trivia_questions')
    op.drop_table('daily_trivia_questions')
    # Only the type this migration created — the trivia enums belong to earlier revisions
    postgresql.ENUM(name='dailytriviarewardstatus').drop(op.get_bind(), checkfirst=True)
