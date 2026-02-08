"""Scheduled tasks endpoint for cron jobs (Cloud Scheduler).

These endpoints are meant to be called by Cloud Scheduler or similar
cron services to trigger periodic tasks like weekly tip notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import logging
import os
from datetime import datetime, UTC

from app.db import get_db
from app.models.user import User, UserRole
from app.services.push_notification import notify_weekly_tips_batch, PushNotificationService
from app.schemas.push_notification import PushNotificationPayload

logger = logging.getLogger(__name__)
router = APIRouter()

# Secret token for cron job authentication
# Set CRON_SECRET in environment to secure these endpoints
CRON_SECRET = os.getenv("CRON_SECRET", "dev-cron-secret-change-in-prod")


def verify_cron_secret(x_cron_secret: Optional[str] = Header(None)):
    """Verify the cron secret header for scheduled job authentication."""
    if x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")
    return True


@router.post("/weekly-tips")
def trigger_weekly_tips(
    db: Session = Depends(get_db),
    _verified: bool = Depends(verify_cron_secret)
):
    """Send weekly tip push notifications to all mentors and apprentices.
    
    This endpoint should be called once per week by Cloud Scheduler.
    
    Example Cloud Scheduler config:
    - Schedule: 0 9 * * 0 (Every Sunday at 9 AM)
    - Target: POST https://api.example.com/scheduled/weekly-tips
    - Headers: X-Cron-Secret: <your-secret>
    """
    # Get current week number (1-52)
    now = datetime.now()
    first_day = datetime(now.year, 1, 1)
    week_number = ((now - first_day).days // 7 % 52) + 1
    
    logger.info(f"Triggering weekly tips for week {week_number}")
    
    # Get all active mentors and apprentices
    mentors = db.query(User).filter(User.role == UserRole.mentor).all()
    apprentices = db.query(User).filter(User.role == UserRole.apprentice).all()
    
    mentor_ids = [m.id for m in mentors]
    apprentice_ids = [a.id for a in apprentices]
    
    # Weekly tip titles (these should match the frontend data)
    # In production, you might want to store these in the database
    mentor_tips = get_mentor_tip_for_week(week_number)
    apprentice_tips = get_apprentice_tip_for_week(week_number)
    
    result = notify_weekly_tips_batch(
        db=db,
        mentor_ids=mentor_ids,
        apprentice_ids=apprentice_ids,
        mentor_tip_title=mentor_tips,
        apprentice_tip_title=apprentice_tips
    )
    
    logger.info(f"Weekly tips sent: {result}")
    
    return {
        "message": "Weekly tips sent",
        "week_number": week_number,
        "mentor_count": len(mentor_ids),
        "apprentice_count": len(apprentice_ids),
        "result": result
    }


@router.post("/test-push/{user_id}")
def test_push_notification(
    user_id: str,
    db: Session = Depends(get_db),
    _verified: bool = Depends(verify_cron_secret)
):
    """Send a test push notification to a specific user (for debugging).
    
    Requires cron secret header for security.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    payload = PushNotificationPayload(
        title="Test Notification",
        body=f"Hello {user.name}! This is a test push notification from T[root]H.",
        data={"type": "test", "timestamp": datetime.now(UTC).isoformat()}
    )
    
    result = PushNotificationService.send_to_user(db, user_id, payload)
    
    return {
        "message": "Test notification sent",
        "user_id": user_id,
        "user_name": user.name,
        "result": result
    }


# Hardcoded tip titles (matches frontend data structure)
# In a more robust system, these would be in the database or shared config

# Complete list of 52 mentor weekly tips
MENTOR_WEEKLY_TIPS = {
    # Q1: Weeks 1-13 - Building Foundation
    1: "Start with Prayer",
    2: "Listen More Than You Speak",
    3: "Ask 'How Can I Help?'",
    4: "Share Your Struggles",
    5: "Celebrate Small Wins",
    6: "Be Consistent",
    7: "Ask Open-Ended Questions",
    8: "Practice Patience",
    9: "Set Clear Expectations",
    10: "Encourage Scripture Reading",
    11: "Respect Boundaries",
    12: "Model What You Teach",
    13: "Check Your Motives",
    # Q2: Weeks 14-26 - Growing Deeper
    14: "Embrace Silence",
    15: "Address the Heart",
    16: "Encourage Community",
    17: "Give Honest Feedback",
    18: "Learn Their Story",
    19: "Pray Specifically",
    20: "Challenge Comfort Zones",
    21: "Admit When You're Wrong",
    22: "Focus on Progress, Not Perfection",
    23: "Use Stories and Examples",
    24: "Encourage Journaling",
    25: "Create Accountability",
    26: "Take a Mid-Year Check",
    # Q3: Weeks 27-39 - Deepening Impact
    27: "Discuss Spiritual Gifts",
    28: "Address Doubt Honestly",
    29: "Encourage Service",
    30: "Navigate Conflict Wisely",
    31: "Encourage Rest",
    32: "Discuss Temptation",
    33: "Develop Decision-Making Skills",
    34: "Celebrate Obedience",
    35: "Explore Calling",
    36: "Address Comparison",
    37: "Practice Gratitude",
    38: "Discuss Money",
    39: "Encourage Worship",
    # Q4: Weeks 40-52 - Looking Forward
    40: "Discuss Relationships",
    41: "Face Fear Together",
    42: "Plan for Growth",
    43: "Discuss Hard Seasons",
    44: "Encourage Evangelism",
    45: "Invest in Their Potential",
    46: "Build Independence",
    47: "Prepare Them to Mentor",
    48: "Express Appreciation",
    49: "Discuss Legacy",
    50: "Review the Journey",
    51: "Look Ahead with Hope",
    52: "Reflect on the Year",
}

# Complete list of 52 apprentice weekly tips
APPRENTICE_WEEKLY_TIPS = {
    # Q1: Weeks 1-13 - Foundations
    1: "Show Up Consistently",
    2: "Come with Questions",
    3: "Be Honest About Struggles",
    4: "Follow Through",
    5: "Start Your Day with God",
    6: "Write It Down",
    7: "Embrace Discomfort",
    8: "Celebrate Small Wins",
    9: "Practice Gratitude",
    10: "Guard Your Inputs",
    11: "Learn to Wait",
    12: "Find Your Tribe",
    13: "Rest Is Holy",
    # Q2: Weeks 14-26 - Growing Deeper
    14: "Memorize Scripture",
    15: "Pray Specifically",
    16: "Confession Brings Freedom",
    17: "Learn from Failure",
    18: "Serve Someone",
    19: "Forgive Quickly",
    20: "Fight Comparison",
    21: "Embrace Silence",
    22: "Your Words Matter",
    23: "Doubt Is Not the Enemy",
    24: "Choose Your Influences",
    25: "Give Generously",
    26: "Check Your Heart",
    # Q3: Weeks 27-39 - Living It Out
    27: "Be the Same Everywhere",
    28: "Handle Conflict Well",
    29: "Protect Your Purity",
    30: "Tell Your Story",
    31: "Worship Beyond Sunday",
    32: "Trust the Process",
    33: "Take Thoughts Captive",
    34: "Don't Go It Alone",
    35: "Use Your Gifts",
    36: "Love the Hard People",
    37: "Stay Humble",
    38: "Run Your Race",
    39: "Keep Showing Up",
    # Q4: Weeks 40-52 - Finishing Strong
    40: "Look for God's Hand",
    41: "Finish What You Start",
    42: "Invest in Eternity",
    43: "Stay Curious",
    44: "Build Daily Rhythms",
    45: "Say Thank You",
    46: "Let Go of Perfection",
    47: "Prepare for Hard Times",
    48: "Share What You're Learning",
    49: "Dream Big Dreams",
    50: "Celebrate Progress",
    51: "Set Goals for Growth",
    52: "Keep Going",
}


def get_mentor_tip_for_week(week_number: int) -> str:
    """Get mentor tip title for the given week number."""
    return MENTOR_WEEKLY_TIPS.get(week_number, f"Week {week_number} Tip")


def get_apprentice_tip_for_week(week_number: int) -> str:
    """Get apprentice tip title for the given week number."""
    return APPRENTICE_WEEKLY_TIPS.get(week_number, f"Week {week_number} Tip")
