from pydantic import BaseModel
from typing import Optional, Dict, List

class QuestionOptionItem(BaseModel):
    id: str
    text: str
    is_correct: bool
    order: int
    model_config = {'from_attributes': True}

class QuestionItem(BaseModel):
    id: str
    text: str
    question_type: str  # Changed from 'type' to match the model
    options: List[QuestionOptionItem] = []
    category_id: Optional[str] = None
    model_config = {'from_attributes': True}

    @classmethod
    def from_question(cls, question):
        """Create QuestionItem from Question model instance."""
        options = []
        if question.options:
            options = [
                QuestionOptionItem(
                    id=str(opt.id),
                    text=opt.option_text,
                    is_correct=opt.is_correct,
                    order=opt.order
                )
                for opt in sorted(question.options, key=lambda x: x.order)
            ]
        
        return cls(
            id=str(question.id),
            text=question.text,
            question_type=question.question_type.value,
            options=options,
            category_id=str(question.category_id) if question.category_id else None
        )

class AssessmentDraftCreate(BaseModel):
    answers: Optional[Dict[str, str]] = None
    last_question_id: Optional[str] = None
    # Some legacy tests omit template_id; treat it as optional and let the route choose a default
    template_id: Optional[str] = None

class AssessmentDraftUpdate(BaseModel):
    last_question_id: Optional[str] = None
    answers: Optional[Dict[str, str]] = None

class AssessmentDraftOut(BaseModel):
    id: str
    apprentice_id: str
    template_id: str
    answers: Optional[Dict[str, str]]
    last_question_id: Optional[str]
    is_submitted: bool
    questions: List[QuestionItem]
    model_config = {'from_attributes': True}

class AssessmentAnswerOut(BaseModel):
    question_id: str
    answer_text: Optional[str]
    model_config = {'from_attributes': True}
