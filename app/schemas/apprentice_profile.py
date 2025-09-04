from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApprenticeProfileOut(BaseModel):
    id: str
    name: str
    email: str
    join_date: Optional[datetime]
    total_assessments: int
    average_score: Optional[float]
    last_submission: Optional[datetime]
    model_config = {'from_attributes': True}
