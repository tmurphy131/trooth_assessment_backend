import random
from datetime import datetime, UTC, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, text

from app.models.trivia import (
    TriviaQuestion, TriviaChallenge, TriviaSingleScore, TriviaBadge,
    TriviaCategory, TriviaDifficulty, TriviaChallengeStatus,
    BADGE_MILESTONES, BADGE_DISPLAY_NAMES,
)
from app.models.user import User
from app.models.mentor_apprentice import MentorApprentice
from app.schemas.trivia import (
    BadgeOut, SingleGameResult, LeaderboardEntry,
    ChallengeListItem, ChallengeDetail, ChallengeQuestionState,
    TriviaQuestionOut, TriviaProfileOut,
)


# ---------- Scoring ----------

def compute_streak_multiplier(streak: int) -> int:
    if streak < 5:
        return 1
    elif streak < 10:
        return 2
    elif streak < 15:
        return 3
    elif streak < 20:
        return 4
    return 5


def compute_score_for_answers(answers: list[dict]) -> tuple[int, int]:
    """Returns (total_score, max_streak_length)."""
    streak = 0
    max_streak = 0
    score = 0
    for ans in answers:
        if ans["correct"]:
            streak += 1
            if streak > max_streak:
                max_streak = streak
            multiplier = compute_streak_multiplier(streak)
            score += 100 * multiplier
        else:
            streak = 0
    return score, max_streak


# ---------- Questions ----------

def draw_questions(
    db: Session,
    category: str,
    difficulty: str,
    count: int,
    exclude_ids: Optional[list[int]] = None,
) -> list[TriviaQuestion]:
    query = db.query(TriviaQuestion).filter(
        TriviaQuestion.is_approved == True,
        TriviaQuestion.difficulty == difficulty,
    )
    if category != "random":
        query = query.filter(TriviaQuestion.category == category)
    if exclude_ids:
        query = query.filter(TriviaQuestion.id.notin_(exclude_ids))

    questions = query.all()
    random.shuffle(questions)
    return questions[:count]


def _shuffle_options(q: TriviaQuestion) -> TriviaQuestion:
    """Return a transient copy of the question with shuffled option positions."""
    if q.question_type.value == "true_false":
        return q  # true/false always a=True, b=False — no shuffle needed

    options = [("a", q.option_a), ("b", q.option_b)]
    if q.option_c:
        options.append(("c", q.option_c))
    if q.option_d:
        options.append(("d", q.option_d))

    correct_text = getattr(q, f"option_{q.correct_option.value}")
    random.shuffle(options)

    # Rebuild a plain object we can mutate without touching the DB session
    from types import SimpleNamespace
    shuffled = SimpleNamespace(
        id=q.id,
        question_text=q.question_text,
        question_type=q.question_type,
        category=q.category,
        difficulty=q.difficulty,
        option_a=None, option_b=None, option_c=None, option_d=None,
        correct_option=None,
    )
    letter_map = ["a", "b", "c", "d"]
    for i, (_, text) in enumerate(options):
        setattr(shuffled, f"option_{letter_map[i]}", text)
        if text == correct_text:
            shuffled.correct_option = type("Opt", (), {"value": letter_map[i]})()

    return shuffled


# ---------- Single Player ----------

def submit_single_game(
    db: Session,
    user_id: str,
    category: str,
    difficulty: str,
    answers: list[dict],
    grace_tokens_used: int,
) -> SingleGameResult:
    # Grade each answer
    graded = []
    for ans in answers:
        q = db.query(TriviaQuestion).filter(TriviaQuestion.id == ans["question_id"]).first()
        graded.append({
            "question_id": ans["question_id"],
            "selected": ans["selected"],
            "correct": q is not None and q.correct_option.value == ans["selected"],
            "time_used_ms": ans["time_used_ms"],
        })

    score, streak_length = compute_score_for_answers(graded)
    correct_count = sum(1 for g in graded if g["correct"])

    # Persist score
    record = TriviaSingleScore(
        user_id=user_id,
        category=TriviaCategory(category),
        difficulty=TriviaDifficulty(difficulty),
        score=score,
        streak_length=streak_length,
        correct_count=correct_count,
        grace_tokens_used=grace_tokens_used,
    )
    db.add(record)
    db.flush()

    # Personal best
    previous_best = (
        db.query(func.max(TriviaSingleScore.score))
        .filter(
            TriviaSingleScore.user_id == user_id,
            TriviaSingleScore.id != record.id,
        )
        .scalar()
    )
    is_new_high_score = previous_best is None or score > previous_best

    # Leaderboard rank (best score per user)
    rank_query = db.execute(
        text("""
        SELECT rank FROM (
            SELECT user_id, MAX(score) AS best,
                   RANK() OVER (ORDER BY MAX(score) DESC) AS rank
            FROM trivia_single_scores
            GROUP BY user_id
        ) sub
        WHERE user_id = :uid
        """),
        {"uid": user_id}
    ).fetchone()
    leaderboard_rank = rank_query[0] if rank_query else None

    # Badges — check milestones at each 10-streak interval up through streak_length
    badges_earned = []
    for milestone, badge_type in BADGE_MILESTONES.items():
        if streak_length >= milestone:
            already = db.query(TriviaBadge).filter(
                TriviaBadge.user_id == user_id,
                TriviaBadge.badge_type == badge_type,
            ).first()
            if not already:
                new_badge = TriviaBadge(
                    user_id=user_id,
                    badge_type=badge_type,
                    streak_at_earn=milestone,
                )
                db.add(new_badge)
                badges_earned.append(BadgeOut(
                    badge_type=badge_type,
                    badge_display_name=BADGE_DISPLAY_NAMES[badge_type],
                    streak_at_earn=milestone,
                    earned_at=new_badge.earned_at or datetime.now(UTC),
                ))

    db.commit()

    return SingleGameResult(
        score=score,
        streak_length=streak_length,
        correct_count=correct_count,
        is_new_high_score=is_new_high_score,
        previous_best=previous_best,
        leaderboard_rank=leaderboard_rank,
        badges_earned=badges_earned,
    )


def get_leaderboard(
    db: Session,
    category: Optional[str],
    difficulty: Optional[str],
    limit: int = 50,
) -> list[LeaderboardEntry]:
    query = db.query(
        TriviaSingleScore.user_id,
        func.max(TriviaSingleScore.score).label("best_score"),
        func.max(TriviaSingleScore.streak_length).label("best_streak"),
    ).filter(TriviaSingleScore.score > 0)

    if category and category != "random":
        query = query.filter(TriviaSingleScore.category == TriviaCategory(category))
    if difficulty:
        query = query.filter(TriviaSingleScore.difficulty == TriviaDifficulty(difficulty))

    rows = (
        query.group_by(TriviaSingleScore.user_id)
        .order_by(func.max(TriviaSingleScore.score).desc())
        .limit(limit)
        .all()
    )

    entries = []
    for i, row in enumerate(rows):
        user = db.query(User).filter(User.id == row.user_id).first()
        name = user.name if user else "Unknown"
        entries.append(LeaderboardEntry(
            rank=i + 1,
            user_id=row.user_id,
            display_name=name,
            score=row.best_score,
            streak_length=row.best_streak,
        ))
    return entries


# ---------- Multiplayer ----------

def create_challenge(
    db: Session,
    challenger_id: str,
    challenged_email: str,
    category: str,
    difficulty: str,
    num_questions: int,
) -> TriviaChallenge:
    challenged = db.query(User).filter(User.email == challenged_email).first()
    if not challenged:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No user found with that email")

    questions = draw_questions(db, category, difficulty, num_questions)
    question_ids = [q.id for q in questions]

    challenge = TriviaChallenge(
        challenger_id=challenger_id,
        challenged_id=challenged.id,
        category=TriviaCategory(category),
        difficulty=TriviaDifficulty(difficulty),
        num_questions=num_questions,
        question_ids=question_ids,
        challenger_answers=[],
        challenged_answers=[],
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge


def _get_challenge_or_404(db: Session, challenge_id: str) -> TriviaChallenge:
    challenge = db.query(TriviaChallenge).filter(TriviaChallenge.id == challenge_id).first()
    if not challenge:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge


def submit_challenge_answer(
    db: Session,
    challenge_id: str,
    user_id: str,
    question_id: int,
    selected: str,
    time_used_ms: int,
) -> dict:
    challenge = _get_challenge_or_404(db, challenge_id)

    if challenge.status not in (TriviaChallengeStatus.active,):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Challenge is not active")

    is_challenger = challenge.challenger_id == user_id
    is_challenged = challenge.challenged_id == user_id
    if not is_challenger and not is_challenged:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not a participant")

    q = db.query(TriviaQuestion).filter(TriviaQuestion.id == question_id).first()
    is_correct = q is not None and q.correct_option.value == selected

    answer_entry = {
        "question_id": question_id,
        "question_index": challenge.current_question_index,
        "selected": selected,
        "correct": is_correct,
        "time_used_ms": time_used_ms,
    }

    # Append to the appropriate answers list
    if is_challenger:
        answers = list(challenge.challenger_answers or [])
        answers_for_index = [a for a in answers if a.get("question_index") == challenge.current_question_index]
        if answers_for_index:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Already answered this question")
        answers.append(answer_entry)
        challenge.challenger_answers = answers
        # Recompute score
        challenge.challenger_score, _ = compute_score_for_answers(
            [a for a in answers if a["correct"] or not a["correct"]]
        )
    else:
        answers = list(challenge.challenged_answers or [])
        answers_for_index = [a for a in answers if a.get("question_index") == challenge.current_question_index]
        if answers_for_index:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Already answered this question")
        answers.append(answer_entry)
        challenge.challenged_answers = answers
        challenge.challenged_score, _ = compute_score_for_answers(
            [a for a in answers if a["correct"] or not a["correct"]]
        )

    challenge.last_activity_at = datetime.now(UTC)

    # Check if both players have answered the current question
    challenger_answered = any(
        a.get("question_index") == challenge.current_question_index
        for a in (challenge.challenger_answers or [])
    )
    challenged_answered = any(
        a.get("question_index") == challenge.current_question_index
        for a in (challenge.challenged_answers or [])
    )

    both_answered = challenger_answered and challenged_answered
    question_unlocked = False

    if both_answered:
        challenge.current_question_index += 1
        question_unlocked = True

        # Check if challenge is complete
        if challenge.current_question_index >= challenge.num_questions:
            challenge.status = TriviaChallengeStatus.complete
            # Determine winner
            if challenge.challenger_score > challenge.challenged_score:
                challenge.winner_id = challenge.challenger_id
            elif challenge.challenged_score > challenge.challenger_score:
                challenge.winner_id = challenge.challenged_id
            # else tie — winner_id stays null

    db.commit()
    return {"question_unlocked": question_unlocked, "challenge_complete": challenge.status == TriviaChallengeStatus.complete}


def get_challenge_list(db: Session, user_id: str) -> list[ChallengeListItem]:
    challenges = db.query(TriviaChallenge).filter(
        (TriviaChallenge.challenger_id == user_id) | (TriviaChallenge.challenged_id == user_id),
        TriviaChallenge.status.in_([
            TriviaChallengeStatus.pending,
            TriviaChallengeStatus.active,
            TriviaChallengeStatus.complete,
        ])
    ).order_by(TriviaChallenge.last_activity_at.desc()).all()

    result = []
    for c in challenges:
        challenger = db.query(User).filter(User.id == c.challenger_id).first()
        challenged = db.query(User).filter(User.id == c.challenged_id).first()
        my_role = "challenger" if c.challenger_id == user_id else "challenged"
        my_answers = c.challenger_answers if my_role == "challenger" else c.challenged_answers
        answered_current = any(
            a.get("question_index") == c.current_question_index
            for a in (my_answers or [])
        )
        is_my_turn = c.status == TriviaChallengeStatus.active and not answered_current

        result.append(ChallengeListItem(
            id=c.id,
            challenger_name=challenger.name if challenger else "Unknown",
            challenged_name=challenged.name if challenged else "Unknown",
            category=c.category.value,
            difficulty=c.difficulty.value,
            num_questions=c.num_questions,
            status=c.status.value,
            current_question_index=c.current_question_index,
            challenger_score=c.challenger_score,
            challenged_score=c.challenged_score,
            my_role=my_role,
            is_my_turn=is_my_turn,
            created_at=c.created_at,
            expires_at=c.expires_at,
        ))
    return result


def get_challenge_detail(db: Session, challenge_id: str, user_id: str) -> ChallengeDetail:
    c = _get_challenge_or_404(db, challenge_id)
    challenger = db.query(User).filter(User.id == c.challenger_id).first()
    challenged = db.query(User).filter(User.id == c.challenged_id).first()
    my_role = "challenger" if c.challenger_id == user_id else "challenged"

    question_states = []
    for idx, q_id in enumerate(c.question_ids):
        if idx > c.current_question_index:
            break  # not yet revealed
        q = db.query(TriviaQuestion).filter(TriviaQuestion.id == q_id).first()
        if not q:
            continue

        ch_ans = next((a for a in (c.challenger_answers or []) if a.get("question_index") == idx), None)
        cd_ans = next((a for a in (c.challenged_answers or []) if a.get("question_index") == idx), None)
        revealed = ch_ans is not None and cd_ans is not None

        if my_role == "challenger":
            my_answer = ch_ans["selected"] if ch_ans else None
            my_correct = ch_ans["correct"] if ch_ans else None
            opponent_answer = cd_ans["selected"] if (cd_ans and revealed) else None
            opponent_correct = cd_ans["correct"] if (cd_ans and revealed) else None
        else:
            my_answer = cd_ans["selected"] if cd_ans else None
            my_correct = cd_ans["correct"] if cd_ans else None
            opponent_answer = ch_ans["selected"] if (ch_ans and revealed) else None
            opponent_correct = ch_ans["correct"] if (ch_ans and revealed) else None

        question_states.append(ChallengeQuestionState(
            question_index=idx,
            question=TriviaQuestionOut(
                id=q.id,
                question_text=q.question_text,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
                question_type=q.question_type.value,
            ),
            my_answer=my_answer,
            opponent_answer=opponent_answer,
            my_correct=my_correct,
            opponent_correct=opponent_correct,
            revealed=revealed,
        ))

    my_answers = c.challenger_answers if my_role == "challenger" else c.challenged_answers
    answered_current = any(
        a.get("question_index") == c.current_question_index
        for a in (my_answers or [])
    )
    is_my_turn = c.status == TriviaChallengeStatus.active and not answered_current

    return ChallengeDetail(
        id=c.id,
        challenger_id=c.challenger_id,
        challenger_name=challenger.name if challenger else "Unknown",
        challenged_id=c.challenged_id,
        challenged_name=challenged.name if challenged else "Unknown",
        category=c.category.value,
        difficulty=c.difficulty.value,
        num_questions=c.num_questions,
        status=c.status.value,
        current_question_index=c.current_question_index,
        challenger_score=c.challenger_score,
        challenged_score=c.challenged_score,
        winner_id=c.winner_id,
        my_role=my_role,
        is_my_turn=is_my_turn,
        questions=question_states,
        created_at=c.created_at,
        expires_at=c.expires_at,
    )


def get_trivia_profile(db: Session, user_id: str) -> TriviaProfileOut:
    completed = db.query(TriviaChallenge).filter(
        (TriviaChallenge.challenger_id == user_id) | (TriviaChallenge.challenged_id == user_id),
        TriviaChallenge.status == TriviaChallengeStatus.complete,
    ).all()

    wins = sum(1 for c in completed if c.winner_id == user_id)
    losses = sum(1 for c in completed if c.winner_id is not None and c.winner_id != user_id)
    ties = sum(1 for c in completed if c.winner_id is None)

    personal_best = db.query(func.max(TriviaSingleScore.score)).filter(
        TriviaSingleScore.user_id == user_id
    ).scalar()

    badges = db.query(TriviaBadge).filter(TriviaBadge.user_id == user_id).all()
    badge_out = [
        BadgeOut(
            badge_type=b.badge_type,
            badge_display_name=BADGE_DISPLAY_NAMES.get(b.badge_type, b.badge_type),
            streak_at_earn=b.streak_at_earn,
            earned_at=b.earned_at,
        )
        for b in badges
    ]

    return TriviaProfileOut(
        user_id=user_id,
        wins=wins,
        losses=losses,
        ties=ties,
        personal_best_score=personal_best,
        badges=badge_out,
    )


def expire_stale_challenges(db: Session) -> int:
    now = datetime.now(UTC)
    expired = db.query(TriviaChallenge).filter(
        TriviaChallenge.status.in_([TriviaChallengeStatus.pending, TriviaChallengeStatus.active]),
        TriviaChallenge.last_activity_at < now - timedelta(days=7),
    ).all()

    for c in expired:
        c.status = TriviaChallengeStatus.expired

    db.commit()
    return len(expired)
