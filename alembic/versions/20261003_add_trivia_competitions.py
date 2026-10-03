"""add trivia competitions + winners, seed the 60-day launch competition

Revision ID: 20261003_trivia_competitions
Revises: 20261002_prayer_entries
Create Date: 2026-10-03

"""
from datetime import datetime
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa

revision = '20261003_trivia_competitions'
down_revision = '20261002_prayer_entries'
branch_labels = None
depends_on = None

ET = ZoneInfo("America/New_York")


def upgrade() -> None:
    competitions = op.create_table(
        'trivia_competitions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('difficulty', sa.String(), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('prizes', sa.JSON(), nullable=False),
        sa.Column('code_valid_days', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'trivia_competition_winners',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('competition_id', sa.Integer(), sa.ForeignKey('trivia_competitions.id'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('place', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('discount_code', sa.String(), nullable=True),
        sa.Column('shopify_discount_id', sa.String(), nullable=True),
        sa.Column('code_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('emailed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pushed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('competition_id', 'user_id', name='uq_trivia_competition_winner'),
    )
    op.create_index(
        'ix_trivia_competition_winners_competition_id',
        'trivia_competition_winners', ['competition_id'],
    )

    # Nov 1 00:00 ET → Dec 31 00:00 ET is exactly 60 days (Nov 1 – Dec 30 inclusive)
    op.bulk_insert(competitions, [{
        'slug': 'launch-2026',
        'name': '60-Day Launch Competition',
        'difficulty': 'challenger',
        'starts_at': datetime(2026, 11, 1, tzinfo=ET),
        'ends_at': datetime(2026, 12, 31, tzinfo=ET),
        'prizes': [
            # Fixed amounts: Shopify can't natively cap a % code at one item, so
            # 1st covers the priciest item ($58.99 hoodie) outright.
            {'place': 1, 'amount': 59, 'label': '$59 off — any merch item free'},
            {'place': 2, 'amount': 30, 'label': '$30 off ONLY BLV merch'},
            {'place': 3, 'amount': 15, 'label': '$15 off ONLY BLV merch'},
        ],
        'code_valid_days': 90,
        'created_at': datetime.now(ET),
    }])


def downgrade() -> None:
    op.drop_index('ix_trivia_competition_winners_competition_id', table_name='trivia_competition_winners')
    op.drop_table('trivia_competition_winners')
    op.drop_table('trivia_competitions')
