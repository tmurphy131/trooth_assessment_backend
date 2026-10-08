"""Request/response shapes for daily trivia — see specs/002-daily-trivia/contracts/daily-trivia-api.md."""
from datetime import date, datetime
from typing import Optional, Literal

from pydantic import BaseModel


class DailyQuestionOut(BaseModel):
    # Deliberately no correct_option — it is only revealed in DailyAnswerResultOut
    date: date
    category: str
    category_label: str
    difficulty: str
    difficulty_label: str
    question_type: str
    question_text: str
    option_a: str
    option_b: str
    option_c: Optional[str] = None
    option_d: Optional[str] = None


class DailyAnswerResultOut(BaseModel):
    selected_option: str
    correct: bool
    correct_option: str
    answered_at: datetime


class RewardOut(BaseModel):
    id: int
    tier: int
    percent: int
    perfect: bool
    status: str
    discount_code: Optional[str] = None
    expires_at: Optional[datetime] = None
    shop_url: str


class NextMilestoneOut(BaseModel):
    tier: int
    days_remaining: int
    percent: int
    percent_if_perfect: int


class CalendarDayOut(BaseModel):
    date: date
    status: Literal["correct", "wrong", "freeze"]


class StreakStateOut(BaseModel):
    current_streak: int
    longest_streak: int
    freezes_available: int
    max_freezes: int
    perfect_run: bool
    answered_today: bool
    streak_started_on: Optional[date] = None
    calendar: list[CalendarDayOut]
    next_milestone: Optional[NextMilestoneOut] = None
    active_reward: Optional[RewardOut] = None


class DailyTodayOut(BaseModel):
    question: DailyQuestionOut
    answer: Optional[DailyAnswerResultOut] = None
    streak: StreakStateOut


class DailyAnswerIn(BaseModel):
    question_date: date
    option: Literal["a", "b", "c", "d"]


class DailyAnswerOut(BaseModel):
    question: DailyQuestionOut
    answer: DailyAnswerResultOut
    streak: StreakStateOut
    freezes_used: int
    streak_reset: bool
    freeze_earned: bool
    new_reward: Optional[RewardOut] = None


class TimezoneIn(BaseModel):
    timezone: str


class TimezoneOut(BaseModel):
    timezone: str


class DailyCronOut(BaseModel):
    reminded: int
    rewards_processed: int
    rewards_expired: int
    errors: list[dict]
