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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True
