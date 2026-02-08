from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.question import QuestionOut

class AssessmentTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None

class AssessmentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None

class AssessmentTemplateOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_published: bool
    is_master_assessment: bool = False
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    category_ids: List[str] = []  # populated at response time (from linked questions' categories if any)
    # Premium gating: True if this assessment requires premium subscription
    is_locked: bool = False
    key: Optional[str] = None  # Assessment key for identification
    model_config = {'from_attributes': True}

class AddQuestionToTemplate(BaseModel):
    question_id: str
    order: int

class FullTemplateView(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_published: bool
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    questions: List[AddQuestionToTemplate]

class TemplateWithFullQuestions(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_published: bool
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    questions: List[QuestionOut]
    model_config = {'from_attributes': True}
