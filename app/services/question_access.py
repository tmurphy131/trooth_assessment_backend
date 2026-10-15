"""Who may see a question's correct answers, and who may change it (specs/010-question-ownership).

Answers and edit rights follow the question's creator, not the template that uses it: questions
are shared across templates (clones link the same rows), so the template owner can't decide.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.assessment_template import AssessmentTemplate
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.question import Question
from app.models.user import UserRole
from app.schemas.question import QuestionOut


def _is_admin(user) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return role == UserRole.admin.value


def can_see_answers(user, question: Question) -> bool:
    """Admins, and the question's creator. Shared questions (no creator) are admin-only."""
    return _is_admin(user) or (question.created_by is not None and question.created_by == user.id)


def manage_block_reason(db: Session, user, question: Question) -> Optional[str]:
    """None if the user may edit/delete the question, else "not_owner" or "used_elsewhere".

    A mentor may change only a question they created that is used solely by their own templates,
    so an edit never alters someone else's assessment.
    """
    if _is_admin(user):
        return None
    if question.created_by is None or question.created_by != user.id:
        return "not_owner"
    foreign_use = (
        db.query(AssessmentTemplate.id)
        .join(AssessmentTemplateQuestion, AssessmentTemplateQuestion.template_id == AssessmentTemplate.id)
        .filter(AssessmentTemplateQuestion.question_id == question.id)
        .filter((AssessmentTemplate.created_by.is_(None)) | (AssessmentTemplate.created_by != user.id))
        .first()
    )
    return "used_elsewhere" if foreign_use else None


def hide_answers(q: QuestionOut, as_false: bool) -> QuestionOut:
    """Copy of `q` without correct answers: False where a released screen needs a bool, else None."""
    value = False if as_false else None
    return q.model_copy(update={"options": [o.model_copy(update={"is_correct": value}) for o in q.options]})


def question_out(question: Question, user, as_false: bool = False) -> QuestionOut:
    out = QuestionOut.model_validate(question)
    return out if can_see_answers(user, question) else hide_answers(out, as_false)
