"""Daily trivia question and streaks — contract: specs/002-daily-trivia/contracts/daily-trivia-api.md."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas.daily_trivia import DailyTodayOut, DailyAnswerIn, DailyAnswerOut, StreakStateOut
from app.services import daily_trivia as daily_svc
from app.services.auth import get_current_user

router = APIRouter()


@router.get("/today", response_model=DailyTodayOut)
def get_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return daily_svc.get_today(db, current_user)


@router.post("/today/answer", response_model=DailyAnswerOut)
def answer_today(
    body: DailyAnswerIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, reward_id = daily_svc.submit_answer(db, current_user, body.question_date, body.option)
    if reward_id is not None:
        # Shopify + email run after the response; the hourly cron retries anything left over
        background_tasks.add_task(daily_svc.process_reward_in_new_session, db.get_bind(), reward_id)
    return response


@router.get("/streak", response_model=StreakStateOut)
def get_streak(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return daily_svc.get_streak_state(db, current_user)
