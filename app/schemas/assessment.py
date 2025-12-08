from pydantic import BaseModel
from typing import Dict, Optional, Any, List
from datetime import datetime
from app.schemas.assessment_draft import QuestionOptionItem


class AssessmentCreate(BaseModel):
    title: str
    user_id: str
    # answers may contain numeric Likert values or free-text; accept Any
    answers: Dict[str, Any]

class QuestionFeedback(BaseModel):
    question: str
    answer: str
    correct: bool
    explanation: str

class AssessmentOut(BaseModel):
    id: str
    apprentice_id: str
    apprentice_name: str  # Add apprentice name for display
    template_id: Optional[str] = None
    category: Optional[str] = None
    template_name: Optional[str] = None
    # Accept mixed types in answers for backward compatibility with legacy submissions
    answers: Dict[str, Any]
    scores: Optional[Dict]  # Keep as flexible Dict to handle the full AI scoring structure
    # Include v2 mentor report blob when available so frontend can render without extra calls
    mentor_report_v2: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = {'from_attributes': True}


class MentorQuestionItemOut(BaseModel):
    id: str
    text: str
    question_type: str
    options: List[QuestionOptionItem] = []
    category_id: Optional[str] = None
    # Enriched with apprentice answer mapping
    apprentice_answer: Optional[str] = None
    chosen_option_id: Optional[str] = None


class ApprenticeRefOut(BaseModel):
    id: str
    name: str


class AssessmentDetailOut(AssessmentOut):
    questions: Optional[List[MentorQuestionItemOut]] = None
    apprentice: Optional[ApprenticeRefOut] = None
    submitted_at: Optional[datetime] = None

