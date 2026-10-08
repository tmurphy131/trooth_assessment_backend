"""Daily trivia question, per-user answers, streaks and streak rewards (spec 002)."""
from sqlalchemy import (
    Column, String, Integer, Boolean, Date, DateTime, Enum, JSON, ForeignKey, UniqueConstraint,
)
from datetime import datetime, UTC
import enum

from app.db import Base
from app.models.trivia import TriviaCategory, TriviaDifficulty, TriviaQuestionType


class DailyTriviaRewardStatus(enum.Enum):
    pending = "pending"          # earned, code not created yet
    active = "active"            # code created; the user's current reward
    superseded = "superseded"    # replaced by a higher tier
    expired = "expired"          # past expires_at


class DailyTriviaQuestion(Base):
    """The one question everyone gets for a calendar date, with its option order fixed."""
    __tablename__ = "daily_trivia_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    question_id = Column(Integer, ForeignKey("trivia_questions.id"), nullable=False, index=True)
    category = Column(Enum(TriviaCategory), nullable=False)
    difficulty = Column(Enum(TriviaDifficulty), nullable=False)
    question_type = Column(Enum(TriviaQuestionType), nullable=False)
    question_text = Column(String, nullable=False)
    options = Column(JSON, nullable=False)           # {"a": str, "b": str, "c": str|None, "d": str|None}
    correct_option = Column(String(1), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class DailyTriviaAnswer(Base):
    __tablename__ = "daily_trivia_answers"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_trivia_answer_user_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)              # the user's local date
    daily_question_id = Column(Integer, ForeignKey("daily_trivia_questions.id"), nullable=False)
    selected_option = Column(String(1), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class DailyTriviaStreak(Base):
    """One row per user. Freezes are applied lazily on the next answer (research R4)."""
    __tablename__ = "daily_trivia_streaks"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    last_answered_date = Column(Date, nullable=True)
    streak_started_on = Column(Date, nullable=True)
    freezes_available = Column(Integer, nullable=False, default=0)
    perfect_run = Column(Boolean, nullable=False, default=True)
    freeze_dates = Column(JSON, nullable=False, default=list)   # ISO dates covered by a freeze
    tiers_earned = Column(JSON, nullable=False, default=list)   # milestones reached this streak
    last_reminded_date = Column(Date, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))


class DailyTriviaReward(Base):
    __tablename__ = "daily_trivia_rewards"
    __table_args__ = (
        UniqueConstraint("user_id", "streak_started_on", "tier", name="uq_daily_trivia_reward_streak_tier"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    streak_started_on = Column(Date, nullable=False)
    tier = Column(Integer, nullable=False)
    percent = Column(Integer, nullable=False)
    perfect = Column(Boolean, nullable=False, default=False)
    status = Column(Enum(DailyTriviaRewardStatus), nullable=False,
                    default=DailyTriviaRewardStatus.pending, index=True)
    discount_code = Column(String, nullable=True)
    shopify_discount_id = Column(String, nullable=True)
    replaces_reward_id = Column(Integer, ForeignKey("daily_trivia_rewards.id"), nullable=True)  # code it superseded
    issued_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    superseded_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    emailed_at = Column(DateTime(timezone=True), nullable=True)
    pushed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
