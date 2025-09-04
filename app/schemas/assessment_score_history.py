from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime


class AssessmentScoreHistoryBase(BaseModel):
    assessment_id: str
    apprentice_id: str
    score_data: dict
    model_used: str = "gpt-4"
    triggered_by: str
    triggered_by_user_id: Optional[str] = None
    notes: Optional[str] = None


class AssessmentScoreHistoryCreate(AssessmentScoreHistoryBase):
    pass


class AssessmentScoreHistoryOut(AssessmentScoreHistoryBase):
    id: str
    scored_at: datetime
    model_config = {'from_attributes': True}
