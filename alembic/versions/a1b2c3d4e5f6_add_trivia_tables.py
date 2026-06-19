"""add trivia tables

Revision ID: a1b2c3d4e5f6
Revises: 20260510_multi_mentor
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = '20260510_multi_mentor'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Define enums with create_type=False so op.create_table() doesn't attempt
    # a second CREATE TYPE — we call .create(checkfirst=True) manually below.
    triviacategory = postgresql.ENUM(
        'old_testament', 'new_testament', 'theology_doctrine', 'discipleship_living', 'random',
        name='triviacategory', create_type=False,
    )
    triviadifficulty = postgresql.ENUM(
        'beginner', 'challenger', 'expert',
        name='triviadifficulty', create_type=False,
    )
    triviacorrectoption = postgresql.ENUM(
        'a', 'b', 'c', 'd',
        name='triviacorrectoption', create_type=False,
    )
    triviaquestiontype = postgresql.ENUM(
        'multiple_choice', 'true_false',
        name='triviaquestiontype', create_type=False,
    )
    triviachallengestatus = postgresql.ENUM(
        'pending', 'active', 'complete', 'expired', 'declined', 'cancelled',
        name='triviachallengestatus', create_type=False,
    )

    # Create each enum type exactly once, skipping if it already exists.
    triviacategory.create(op.get_bind(), checkfirst=True)
    triviadifficulty.create(op.get_bind(), checkfirst=True)
    triviacorrectoption.create(op.get_bind(), checkfirst=True)
    triviaquestiontype.create(op.get_bind(), checkfirst=True)
    triviachallengestatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'trivia_questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category', triviacategory, nullable=False),
        sa.Column('difficulty', triviadifficulty, nullable=False),
        sa.Column('question_text', sa.String(), nullable=False),
        sa.Column('option_a', sa.String(), nullable=False),
        sa.Column('option_b', sa.String(), nullable=False),
        sa.Column('option_c', sa.String(), nullable=True),
        sa.Column('option_d', sa.String(), nullable=True),
        sa.Column('correct_option', triviacorrectoption, nullable=False),
        sa.Column('question_type', triviaquestiontype, nullable=False, server_default='multiple_choice'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trivia_questions_category', 'trivia_questions', ['category'])
    op.create_index('ix_trivia_questions_difficulty', 'trivia_questions', ['difficulty'])

    op.create_table(
        'trivia_challenges',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('challenger_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('challenged_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('category', triviacategory, nullable=False),
        sa.Column('difficulty', triviadifficulty, nullable=False),
        sa.Column('num_questions', sa.Integer(), nullable=False),
        sa.Column('question_ids', sa.JSON(), nullable=False),
        sa.Column('current_question_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', triviachallengestatus, nullable=False, server_default='pending'),
        sa.Column('challenger_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('challenger_answers', sa.JSON(), nullable=True),
        sa.Column('challenged_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('challenged_answers', sa.JSON(), nullable=True),
        sa.Column('winner_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('nudge_last_sent_by_challenger', sa.DateTime(timezone=True), nullable=True),
        sa.Column('nudge_last_sent_by_challenged', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trivia_challenges_challenger_id', 'trivia_challenges', ['challenger_id'])
    op.create_index('ix_trivia_challenges_challenged_id', 'trivia_challenges', ['challenged_id'])
    op.create_index('ix_trivia_challenges_status', 'trivia_challenges', ['status'])

    op.create_table(
        'trivia_single_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('category', triviacategory, nullable=False),
        sa.Column('difficulty', triviadifficulty, nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('streak_length', sa.Integer(), nullable=False),
        sa.Column('correct_count', sa.Integer(), nullable=False),
        sa.Column('grace_tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trivia_single_scores_user_id', 'trivia_single_scores', ['user_id'])

    op.create_table(
        'trivia_badges',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('badge_type', sa.String(), nullable=False),
        sa.Column('streak_at_earn', sa.Integer(), nullable=False),
        sa.Column('earned_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trivia_badges_user_id', 'trivia_badges', ['user_id'])


def downgrade() -> None:
    op.drop_table('trivia_badges')
    op.drop_table('trivia_single_scores')
    op.drop_table('trivia_challenges')
    op.drop_table('trivia_questions')

    op.execute("DROP TYPE IF EXISTS triviachallengestatus")
    op.execute("DROP TYPE IF EXISTS triviaquestiontype")
    op.execute("DROP TYPE IF EXISTS triviacorrectoption")
    op.execute("DROP TYPE IF EXISTS triviadifficulty")
    op.execute("DROP TYPE IF EXISTS triviacategory")
