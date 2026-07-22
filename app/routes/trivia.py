from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, UTC, timedelta
from typing import Optional

from app.db import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.models.trivia import TriviaChallenge, TriviaChallengeStatus
from app.models.mentor_apprentice import MentorApprentice
from app.schemas.trivia import (
    TriviaQuestionOut, SingleGameSubmit, SingleGameResult,
    LeaderboardEntry, ChallengeCreate, ChallengeAnswerSubmit,
    ChallengeListItem, ChallengeDetail, TriviaProfileOut,
)
from app.services import trivia as trivia_svc
from app.services.push_notification import (
    notify_trivia_challenge_received,
    notify_trivia_question_unlocked,
    notify_trivia_challenge_result,
    notify_trivia_nudge,
    notify_trivia_challenge_expired,
)

router = APIRouter()


# ---------- Single Player ----------

@router.get("/questions/draw", response_model=list[TriviaQuestionOut])
def draw_questions(
    category: str = Query(...),
    difficulty: str = Query(...),
    count: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    questions = trivia_svc.draw_questions(db, category, difficulty, count)
    return [
        TriviaQuestionOut(
            id=q.id,
            question_text=q.question_text,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
            question_type=q.question_type.value if hasattr(q.question_type, 'value') else q.question_type,
            correct_option=q.correct_option.value if hasattr(q.correct_option, 'value') else q.correct_option,
        )
        for q in questions
    ]


@router.post("/single/submit", response_model=SingleGameResult)
def submit_single_game(
    body: SingleGameSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return trivia_svc.submit_single_game(
        db,
        user_id=current_user.id,
        category=body.category,
        difficulty=body.difficulty,
        answers=[a.model_dump() for a in body.answers],
        grace_tokens_used=body.grace_tokens_used,
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def get_leaderboard(
    category: Optional[str] = Query(default=None),
    difficulty: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return trivia_svc.get_leaderboard(db, category, difficulty, limit)


# ---------- Multiplayer ----------

@router.post("/challenges", response_model=ChallengeDetail)
def create_challenge(
    body: ChallengeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.num_questions not in (20, 25, 30):
        raise HTTPException(status_code=400, detail="num_questions must be 20, 25, or 30")

    challenge = trivia_svc.create_challenge(
        db,
        challenger_id=current_user.id,
        challenged_email=body.challenged_email,
        category=body.category,
        difficulty=body.difficulty,
        num_questions=body.num_questions,
    )

    # Notify challenged player
    challenged_user = db.query(User).filter(User.id == challenge.challenged_id).first()
    if challenged_user:
        notify_trivia_challenge_received(
            db,
            user_id=challenged_user.id,
            challenger_name=current_user.name or current_user.email,
            challenge_id=challenge.id,
        )

    return trivia_svc.get_challenge_detail(db, challenge.id, current_user.id)


@router.get("/challenges", response_model=list[ChallengeListItem])
def list_challenges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return trivia_svc.get_challenge_list(db, current_user.id)


@router.get("/challenges/{challenge_id}", response_model=ChallengeDetail)
def get_challenge(
    challenge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return trivia_svc.get_challenge_detail(db, challenge_id, current_user.id)


@router.post("/challenges/{challenge_id}/accept")
def accept_challenge(
    challenge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    challenge = db.query(TriviaChallenge).filter(TriviaChallenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.challenged_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the challenged player can accept")
    if challenge.status != TriviaChallengeStatus.pending:
        raise HTTPException(status_code=400, detail="Challenge is not pending")

    challenge.status = TriviaChallengeStatus.active
    challenge.last_activity_at = datetime.now(UTC)
    db.commit()
    return {"status": "accepted"}


@router.post("/challenges/{challenge_id}/decline")
def decline_challenge(
    challenge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    challenge = db.query(TriviaChallenge).filter(TriviaChallenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.challenged_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the challenged player can decline")
    if challenge.status != TriviaChallengeStatus.pending:
        raise HTTPException(status_code=400, detail="Challenge is not pending")

    challenge.status = TriviaChallengeStatus.declined
    db.commit()
    return {"status": "declined"}


@router.post("/challenges/{challenge_id}/answer")
def submit_answer(
    challenge_id: str,
    body: ChallengeAnswerSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = trivia_svc.submit_challenge_answer(
        db,
        challenge_id=challenge_id,
        user_id=current_user.id,
        question_id=body.answer.question_id,
        selected=body.answer.selected,
        time_used_ms=body.answer.time_used_ms,
    )

    challenge = db.query(TriviaChallenge).filter(TriviaChallenge.id == challenge_id).first()

    if result["question_unlocked"]:
        notify_trivia_question_unlocked(
            db,
            challenger_id=challenge.challenger_id,
            challenged_id=challenge.challenged_id,
            challenge_id=challenge_id,
            question_index=challenge.current_question_index - 1,
        )

    if result["challenge_complete"]:
        challenger = db.query(User).filter(User.id == challenge.challenger_id).first()
        challenged = db.query(User).filter(User.id == challenge.challenged_id).first()
        winner_id = challenge.winner_id
        for user in [challenger, challenged]:
            if user:
                if winner_id is None:
                    outcome = "tied"
                elif winner_id == user.id:
                    outcome = "won"
                else:
                    outcome = "lost"
                notify_trivia_challenge_result(
                    db,
                    user_id=user.id,
                    challenge_id=challenge_id,
                    result=outcome,
                )

    return result


@router.delete("/challenges/{challenge_id}")
def cancel_challenge(
    challenge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    challenge = db.query(TriviaChallenge).filter(TriviaChallenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.challenger_id != current_user.id and challenge.challenged_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not a participant")
    if challenge.status == TriviaChallengeStatus.cancelled:
        raise HTTPException(status_code=400, detail="Challenge is already cancelled")

    challenge.status = TriviaChallengeStatus.cancelled
    db.commit()
    return {"status": "cancelled"}


@router.post("/challenges/{challenge_id}/forfeit")
def forfeit_challenge(
    challenge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    challenge = db.query(TriviaChallenge).filter(TriviaChallenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    is_challenger = challenge.challenger_id == current_user.id
    is_challenged = challenge.challenged_id == current_user.id
    if not is_challenger and not is_challenged:
        raise HTTPException(status_code=403, detail="Not a participant")

    if challenge.status not in (TriviaChallengeStatus.active, TriviaChallengeStatus.pending):
        raise HTTPException(status_code=400, detail="Challenge cannot be quit")

    opponent_id = challenge.challenged_id if is_challenger else challenge.challenger_id

    # Game started = both players answered at least one question (index advanced past 0)
    game_started = challenge.status == TriviaChallengeStatus.active and challenge.current_question_index > 0

    if game_started:
        # Forfeit: quitter loses, opponent wins
        challenge.winner_id = opponent_id
        challenge.status = TriviaChallengeStatus.complete
    else:
        challenge.status = TriviaChallengeStatus.cancelled

    db.commit()

    if game_started:
        notify_trivia_challenge_result(db, user_id=opponent_id, challenge_id=challenge_id, result="won")

    return {"status": "forfeited", "counted": game_started}


@router.post("/challenges/{challenge_id}/nudge")
def nudge_opponent(
    challenge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    challenge = db.query(TriviaChallenge).filter(TriviaChallenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    is_challenger = challenge.challenger_id == current_user.id
    is_challenged = challenge.challenged_id == current_user.id
    if not is_challenger and not is_challenged:
        raise HTTPException(status_code=403, detail="Not a participant")

    now = datetime.now(UTC)
    last_nudge = challenge.nudge_last_sent_by_challenger if is_challenger else challenge.nudge_last_sent_by_challenged
    if last_nudge and (now - last_nudge) < timedelta(hours=24):
        raise HTTPException(status_code=429, detail="You can only nudge once per day")

    if is_challenger:
        challenge.nudge_last_sent_by_challenger = now
        opponent_id = challenge.challenged_id
    else:
        challenge.nudge_last_sent_by_challenged = now
        opponent_id = challenge.challenger_id

    db.commit()

    notify_trivia_nudge(
        db,
        user_id=opponent_id,
        nudger_name=current_user.name or current_user.email,
        challenge_id=challenge_id,
    )
    return {"status": "nudge_sent"}


# ---------- Profile ----------

@router.get("/profile/{user_id}", response_model=TriviaProfileOut)
def get_trivia_profile(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return trivia_svc.get_trivia_profile(db, user_id)


# ---------- Mentor/Apprentice connections for challenge creation ----------

@router.get("/connections")
def get_trivia_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return mentors and apprentices linked to current user for quick challenge creation."""
    from app.models.user import UserRole
    connections = []

    if current_user.role == UserRole.apprentice:
        # Get mentor(s)
        rows = db.query(MentorApprentice).filter(
            MentorApprentice.apprentice_id == current_user.id,
            MentorApprentice.active == True,
        ).all()
        for r in rows:
            mentor = db.query(User).filter(User.id == r.mentor_id).first()
            if mentor:
                connections.append({"user_id": mentor.id, "name": mentor.name, "email": mentor.email, "relation": "mentor"})
    else:
        # Get apprentice(s)
        rows = db.query(MentorApprentice).filter(
            MentorApprentice.mentor_id == current_user.id,
            MentorApprentice.active == True,
        ).all()
        for r in rows:
            apprentice = db.query(User).filter(User.id == r.apprentice_id).first()
            if apprentice:
                connections.append({"user_id": apprentice.id, "name": apprentice.name, "email": apprentice.email, "relation": "apprentice"})

    # Also return recent opponents (past challenges, unique)
    past_challenges = db.query(TriviaChallenge).filter(
        (TriviaChallenge.challenger_id == current_user.id) | (TriviaChallenge.challenged_id == current_user.id),
        TriviaChallenge.status != TriviaChallengeStatus.pending,
    ).order_by(TriviaChallenge.created_at.desc()).limit(20).all()

    seen_ids = {c["user_id"] for c in connections}
    recent_opponents = []
    for c in past_challenges:
        opp_id = c.challenged_id if c.challenger_id == current_user.id else c.challenger_id
        if opp_id not in seen_ids:
            opp = db.query(User).filter(User.id == opp_id).first()
            if opp:
                recent_opponents.append({"user_id": opp.id, "name": opp.name, "email": opp.email, "relation": "recent_opponent"})
                seen_ids.add(opp_id)

    return {"connections": connections, "recent_opponents": recent_opponents}
