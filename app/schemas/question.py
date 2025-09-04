from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class QuestionType(str, Enum):
    open_ended = "open_ended"
    multiple_choice = "multiple_choice"

class QuestionOptionCreate(BaseModel):
    option_text: str
    is_correct: bool = False
    order: int = 0

class QuestionOptionOut(BaseModel):
    id: str
    option_text: str
    is_correct: bool
    order: int
    model_config = {'from_attributes': True}

class CategoryCreate(BaseModel):
    name: str

class CategoryOut(BaseModel):
    id: str
    name: str
    model_config = {'from_attributes': True}

class QuestionCreate(BaseModel):
    text: str
    question_type: QuestionType = QuestionType.open_ended
    category_id: Optional[str] = None
    options: List[QuestionOptionCreate] = []

class QuestionOut(BaseModel):
    id: str
    text: str
    question_type: QuestionType
    category_id: Optional[str] = None
    options: List[QuestionOptionOut] = []
    model_config = {'from_attributes': True}

class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    question_type: Optional[QuestionType] = None
    category_id: Optional[str] = None
    options: Optional[List[QuestionOptionCreate]] = None