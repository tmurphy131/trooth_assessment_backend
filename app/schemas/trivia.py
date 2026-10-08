from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models.trivia import TriviaCategory, TriviaDifficulty, TriviaChallengeStatus


# ---------- Questions ----------

class TriviaQuestionOut(BaseModel):
    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    question_type: str
    correct_option: Optional[str] = None  # legacy single-player draw only (removed at app 2.2.0)

    model_config = {'from_attributes': True}


class TriviaQuestionWithAnswer(TriviaQuestionOut):
    pass  # correct_option already on base


# ---------- Single Player ----------

class SingleAnswerIn(BaseModel):
    question_id: int
    selected: str           # a / b / c / d
    time_used_ms: int


class SingleGameSubmit(BaseModel):
    category: str
    difficulty: str
    answers: list[SingleAnswerIn]
    grace_tokens_used: int = 0


class BadgeOut(BaseModel):
    badge_type: str
    badge_display_name: str
    streak_at_earn: int
    earned_at: datetime

    model_config = {'from_attributes': True}


class SingleGameResult(BaseModel):
    score: int
    streak_length: int
    correct_count: int
    is_new_high_score: bool
    previous_best: Optional[int]
    leaderboard_rank: Optional[int]
    badges_earned: list[BadgeOut]


# ---------- Server-run single player sessions ----------

class SingleStartIn(BaseModel):
    category: TriviaCategory
    difficulty: TriviaDifficulty


class SessionAnswerIn(BaseModel):
    question_id: int
    selected: Optional[str] = None   # a / b / c / d; null when the player's timer ran out


class GraceIn(BaseModel):
    use: bool


class SessionQuestion(BaseModel):
    # Deliberately has no correct_option field
    index: int
    id: int
    question_text: str
    question_type: str
    option_a: str
    option_b: str
    option_c: Optional[str] = None
    option_d: Optional[str] = None


class LastAnswer(BaseModel):
    question_id: int
    selected: Optional[str] = None
    correct: bool
    correct_option: str
    timed_out: bool


class SingleSessionState(BaseModel):
    session_id: str
    status: str                       # active | awaiting_grace | finished
    score: int
    streak: int
    correct_count: int
    grace_tokens: int
    grace_tokens_used: int
    question_number: int              # 1-based number of `question`
    total_questions: int
    time_limit_ms: int
    question: Optional[SessionQuestion] = None
    last_answer: Optional[LastAnswer] = None
    grace_expires_in_ms: Optional[int] = None
    result: Optional[SingleGameResult] = None


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    display_name: str
    score: int
    streak_length: int


# ---------- Multiplayer ----------

class ChallengeCreate(BaseModel):
    challenged_email: EmailStr
    category: str
    difficulty: str
    num_questions: int   # 20, 25, or 30


class ChallengeAnswerIn(BaseModel):
    question_id: int
    selected: str
    time_used_ms: int


class ChallengeAnswerSubmit(BaseModel):
    answer: ChallengeAnswerIn


class ChallengeListItem(BaseModel):
    id: str
    challenger_name: str
    challenged_name: str
    category: str
    difficulty: str
    num_questions: int
    status: str
    current_question_index: int
    challenger_score: int
    challenged_score: int
    my_role: str           # "challenger" or "challenged"
    is_my_turn: bool       # true if I still need to answer current question
    created_at: datetime
    expires_at: datetime

    model_config = {'from_attributes': True}


class ChallengeQuestionState(BaseModel):
    question_index: int
    question: TriviaQuestionOut
    my_answer: Optional[str]          # null if not yet answered
    opponent_answer: Optional[str]    # null until both answered
    my_correct: Optional[bool]
    opponent_correct: Optional[bool]
    revealed: bool                    # true once both answered


class ChallengeDetail(BaseModel):
    id: str
    challenger_id: str
    challenger_name: str
    challenged_id: str
    challenged_name: str
    category: str
    difficulty: str
    num_questions: int
    status: str
    current_question_index: int
    challenger_score: int
    challenged_score: int
    winner_id: Optional[str]
    my_role: str
    is_my_turn: bool
    questions: list[ChallengeQuestionState]
    created_at: datetime
    expires_at: datetime

    model_config = {'from_attributes': True}


# ---------- Profile ----------

class TriviaProfileOut(BaseModel):
    user_id: str
    wins: int
    losses: int
    ties: int
    personal_best_score: Optional[int]
    badges: list[BadgeOut]


# ---------- Competition ----------

class CompetitionPrize(BaseModel):
    place: int
    amount: int                 # USD off the order
    label: str


class CompetitionStanding(BaseModel):
    rank: int
    user_id: str
    display_name: str
    score: int
    streak_length: int


class CompetitionWinnerOut(BaseModel):
    place: int
    display_name: str
    score: int
    is_me: bool = False


class CompetitionMyPrize(BaseModel):
    place: int
    label: str
    discount_code: str
    code_expires_at: Optional[datetime] = None
    shop_url: str


class CompetitionOut(BaseModel):
    slug: str
    name: str
    status: str                 # upcoming | active | ended
    difficulty: str
    starts_at: datetime
    ends_at: datetime
    server_now: datetime
    prizes: list[CompetitionPrize]
    standings: list[CompetitionStanding] = []
    my_rank: Optional[int] = None
    my_score: Optional[int] = None
    is_eligible: bool = True
    finalized: bool = False
    winners: list[CompetitionWinnerOut] = []
    my_prize: Optional[CompetitionMyPrize] = None
