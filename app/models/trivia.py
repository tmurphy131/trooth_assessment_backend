from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, UTC, timedelta
import enum
import uuid

from app.db import Base


class TriviaCategory(enum.Enum):
    old_testament = "old_testament"
    new_testament = "new_testament"
    theology_doctrine = "theology_doctrine"
    discipleship_living = "discipleship_living"
    random = "random"


class TriviaDifficulty(enum.Enum):
    beginner = "beginner"
    challenger = "challenger"
    expert = "expert"


class TriviaCorrectOption(enum.Enum):
    a = "a"
    b = "b"
    c = "c"
    d = "d"


class TriviaQuestionType(enum.Enum):
    multiple_choice = "multiple_choice"
    true_false = "true_false"


class TriviaChallengeStatus(enum.Enum):
    pending = "pending"        # awaiting accept/decline
    active = "active"          # accepted, in progress
    complete = "complete"      # both players finished
    expired = "expired"        # 7-day inactivity
    declined = "declined"
    cancelled = "cancelled"


class TriviaQuestion(Base):
    __tablename__ = "trivia_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(Enum(TriviaCategory), nullable=False, index=True)
    difficulty = Column(Enum(TriviaDifficulty), nullable=False, index=True)
    question_text = Column(String, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=True)  # null for true/false
    option_d = Column(String, nullable=True)  # null for true/false
    correct_option = Column(Enum(TriviaCorrectOption), nullable=False)
    question_type = Column(Enum(TriviaQuestionType), nullable=False, default=TriviaQuestionType.multiple_choice)
    is_approved = Column(Boolean, nullable=False, default=True)  # import script sets true
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TriviaChallenge(Base):
    __tablename__ = "trivia_challenges"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challenger_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    challenged_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(Enum(TriviaCategory), nullable=False)
    difficulty = Column(Enum(TriviaDifficulty), nullable=False)
    num_questions = Column(Integer, nullable=False)
    question_ids = Column(JSON, nullable=False)           # [int, ...]
    current_question_index = Column(Integer, nullable=False, default=0)
    status = Column(Enum(TriviaChallengeStatus), nullable=False, default=TriviaChallengeStatus.pending, index=True)
    challenger_score = Column(Integer, nullable=False, default=0)
    challenger_answers = Column(JSON, nullable=True)      # [{question_id, selected, correct, time_used_ms}]
    challenged_score = Column(Integer, nullable=False, default=0)
    challenged_answers = Column(JSON, nullable=True)      # same structure
    winner_id = Column(String, ForeignKey("users.id"), nullable=True)
    nudge_last_sent_by_challenger = Column(DateTime(timezone=True), nullable=True)
    nudge_last_sent_by_challenged = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC) + timedelta(days=7))
    last_activity_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    challenger = relationship("User", foreign_keys=[challenger_id])
    challenged = relationship("User", foreign_keys=[challenged_id])
    winner = relationship("User", foreign_keys=[winner_id])


class TriviaSingleScore(Base):
    __tablename__ = "trivia_single_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(Enum(TriviaCategory), nullable=False)
    difficulty = Column(Enum(TriviaDifficulty), nullable=False)
    score = Column(Integer, nullable=False)
    streak_length = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    grace_tokens_used = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user = relationship("User", foreign_keys=[user_id])


class TriviaBadge(Base):
    __tablename__ = "trivia_badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    badge_type = Column(String, nullable=False)   # e.g. "faithful_disciple"
    streak_at_earn = Column(Integer, nullable=False)
    earned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user = relationship("User", foreign_keys=[user_id])


BADGE_MILESTONES = {
    10: "faithful_disciple",
    20: "scripture_scholar",
    30: "bible_champion",
    40: "wisdom_seeker",
    50: "the_apostle",
    60: "the_prophet",
    70: "the_evangelist",
    80: "the_elder",
    90: "the_overcomer",
    100: "the_chosen",
}

BADGE_DISPLAY_NAMES = {
    "faithful_disciple": "Faithful Disciple",
    "scripture_scholar": "Scripture Scholar",
    "bible_champion": "Bible Champion",
    "wisdom_seeker": "Wisdom Seeker",
    "the_apostle": "The Apostle",
    "the_prophet": "The Prophet",
    "the_evangelist": "The Evangelist",
    "the_elder": "The Elder",
    "the_overcomer": "The Overcomer",
    "the_chosen": "The Chosen",
}
