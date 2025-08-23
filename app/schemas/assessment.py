from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime


class AssessmentCreate(BaseModel):
    title: str
    user_id: str
    answers: Dict[str, str]  # e.g., {"Spiritual Growth": "I pray daily", ...}

class QuestionFeedback(BaseModel):
    question: str
    answer: str
    correct: bool
    explanation: str

class AssessmentOut(BaseModel):
    id: str
    apprentice_id: str
    apprentice_name: str  # Add apprentice name for display
    answers: Dict[str, str]
    scores: Optional[Dict]  # Keep as flexible Dict to handle the full AI scoring structure
    created_at: datetime

    class Config:
        from_attributes = True
