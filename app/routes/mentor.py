from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.services.auth import require_mentor
from app.db import get_db
from app.models.user import User
from app.models.mentor_apprentice import MentorApprentice
from app.models.assessment_draft import AssessmentDraft
from app.models.question import Question
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.schemas.assessment_draft import AssessmentDraftOut, QuestionItem
from app.models.user import User as UserModel
from app.schemas.apprentice_profile import ApprenticeProfileOut
from fastapi import Query
from datetime import datetime
from app.services.auth import get_current_user
from app.exceptions import ForbiddenException, NotFoundException

router = APIRouter()

@router.get("/my-apprentices", response_model=list[dict])
def list_apprentices(
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    apprentices = (
        db.query(MentorApprentice)
        .filter(MentorApprentice.mentor_id == current_user.id)
        .all()
    )

    apprentice_ids = [a.apprentice_id for a in apprentices]
    apprentice_users = (
        db.query(UserModel)
        .filter(UserModel.id.in_(apprentice_ids))
        .all()
    )

    return [
        {"id": u.id, "name": u.name, "email": u.email}
        for u in apprentice_users
    ]

@router.get("/apprentice/{apprentice_id}/draft", response_model=AssessmentDraftOut)
def get_apprentice_draft(
    apprentice_id: str,
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    # Check if this apprentice belongs to the current mentor
    mapping = db.query(MentorApprentice).filter_by(
        mentor_id=current_user.id, apprentice_id=apprentice_id
    ).first()
    if not mapping:
        raise ForbiddenException("Not authorized to view this apprentice")

    draft = (
        db.query(AssessmentDraft)
        .filter_by(apprentice_id=apprentice_id, is_submitted=False)
        .first()
    )
    if not draft:
        raise NotFoundException("No draft found for apprentice")

    # Get questions for this template
    questions = (
        db.query(Question)
        .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
        .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
        .order_by(AssessmentTemplateQuestion.order)
        .all()
    )
    questions_out = [QuestionItem.from_orm(q) for q in questions]

    # Return as AssessmentDraftOut
    return AssessmentDraftOut(
        id=draft.id,
        apprentice_id=draft.apprentice_id,
        template_id=draft.template_id,
        answers=draft.answers,
        last_question_id=draft.last_question_id,
        is_submitted=draft.is_submitted,
        questions=questions_out
    )

from app.models.assessment import Assessment
from app.schemas.assessment import AssessmentOut


@router.get("/apprentice/{apprentice_id}/submitted-assessments", response_model=list[AssessmentOut])
def get_submitted_assessments_for_apprentice(
    apprentice_id: str,
    category: str = Query(None),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    # Verify mentor-apprentice relationship
    mapping = db.query(MentorApprentice).filter_by(
        mentor_id=current_user.id,
        apprentice_id=apprentice_id
    ).first()
    if not mapping:
        raise ForbiddenException("Not authorized to view this apprentice")

    query = db.query(Assessment).filter_by(apprentice_id=apprentice_id)

    if category:
        query = query.filter(Assessment.category == category)
    if start_date:
        query = query.filter(Assessment.created_at >= start_date)
    if end_date:
        query = query.filter(Assessment.created_at <= end_date)

    assessments = query.order_by(Assessment.created_at.desc()).offset(skip).limit(limit).all()
    return assessments

@router.get("/assessment/{assessment_id}", response_model=AssessmentOut)
def get_assessment_detail(
    assessment_id: str,
    current_user: User = Depends(require_mentor),
    db: Session = Depends(get_db)
):
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise NotFoundException("Assessment not found")

    # Check mentor-apprentice relationship
    mapping = db.query(MentorApprentice).filter_by(
        mentor_id=current_user.id,
        apprentice_id=assessment.apprentice_id
    ).first()
    if not mapping:
        raise ForbiddenException("Not authorized to view this assessment")

    return assessment

from app.models.assessment_draft import AssessmentDraft
from app.models.user import User
from app.schemas.assessment_draft import AssessmentDraftOut
from fastapi import Query
from datetime import datetime

@router.get("/submitted-drafts", response_model=list[AssessmentDraftOut])
def get_submitted_drafts(
    apprentice_id: str = Query(default=None),
    start_date: datetime = Query(default=None),
    end_date: datetime = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    query = db.query(AssessmentDraft).join(
        MentorApprentice,
        MentorApprentice.apprentice_id == AssessmentDraft.apprentice_id
    ).filter(
        MentorApprentice.mentor_id == current_user.id,
        AssessmentDraft.is_submitted.is_(True)
    )

    if apprentice_id:
        query = query.filter(AssessmentDraft.apprentice_id == apprentice_id)
    if start_date:
        query = query.filter(AssessmentDraft.updated_at >= start_date)
    if end_date:
        query = query.filter(AssessmentDraft.updated_at <= end_date)

    drafts = query.all()
    
    # Build the response objects properly
    draft_responses = []
    for draft in drafts:
        # Get questions for this template with proper relationship loading
        template_questions = db.query(AssessmentTemplateQuestion)\
            .join(Question)\
            .filter(AssessmentTemplateQuestion.template_id == draft.template_id)\
            .order_by(AssessmentTemplateQuestion.order)\
            .all()
        
        questions = [
            QuestionItem(
                id=str(tq.question.id),
                text=tq.question.text,
                question_type=tq.question.question_type.value,
                options=[opt.option_text for opt in tq.question.options] if tq.question.options else [],
                category_id=str(tq.question.category_id) if tq.question.category_id else None
            ) for tq in template_questions
        ]
        
        draft_responses.append(AssessmentDraftOut(
            id=str(draft.id),
            apprentice_id=str(draft.apprentice_id),
            template_id=str(draft.template_id),
            answers=draft.answers,
            last_question_id=str(draft.last_question_id) if draft.last_question_id else None,
            is_submitted=draft.is_submitted,
            questions=questions
        ))
    
    return draft_responses

@router.get("/submitted-drafts/{draft_id}", response_model=AssessmentDraftOut)
def get_single_submitted_draft(
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    draft = db.query(AssessmentDraft).filter_by(id=draft_id, is_submitted=True).first()
    if not draft:
        raise NotFoundException("Submitted draft not found")

    # Make sure this mentor is linked to the apprentice
    mapping = db.query(MentorApprentice).filter_by(
        mentor_id=current_user.id,
        apprentice_id=draft.apprentice_id
    ).first()

    if not mapping:
        raise ForbiddenException("Not authorized to view this draft")

    # Get questions for this template
    template_questions = db.query(AssessmentTemplateQuestion)\
        .filter_by(template_id=draft.template_id)\
        .order_by(AssessmentTemplateQuestion.order)\
        .all()
    
    questions = [
        QuestionItem(
            id=str(tq.question.id),
            text=tq.question.text,
            question_type=tq.question.question_type.value,
            options=[opt.option_text for opt in tq.question.options] if tq.question.options else [],
            category_id=str(tq.question.category_id) if tq.question.category_id else None
        ) for tq in template_questions
    ]

    # Return as AssessmentDraftOut
    return AssessmentDraftOut(
        id=str(draft.id),
        user_id=str(draft.apprentice_id),
        assessment_template_id=str(draft.template_id),
        title=draft.title,
        answers=draft.answers,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        is_submitted=draft.is_submitted,
        submitted_at=draft.submitted_at,
        score=draft.score,
        questions=questions
    )

from fastapi.responses import StreamingResponse
import io
import csv
import json

@router.get("/submitted-drafts/export")
def export_submitted_drafts(
    format: str = Query(default="csv", enum=["csv", "json"]),
    apprentice_id: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor)
):
    query = db.query(
        AssessmentDraft,
        User.name,
        User.email
    ).join(
        User, AssessmentDraft.apprentice_id == User.id
    ).join(
        MentorApprentice,
        MentorApprentice.apprentice_id == AssessmentDraft.apprentice_id
    ).filter(
        MentorApprentice.mentor_id == current_user.id,
        AssessmentDraft.is_submitted.is_(True)
    )

    if apprentice_id:
        query = query.filter(AssessmentDraft.apprentice_id == apprentice_id)

    results = query.all()

    if format == "json":
        content = json.dumps([{
            "id": d.id,
            "apprentice_id": d.apprentice_id,
            "apprentice_name": name,
            "apprentice_email": email,
            "answers": d.answers,
            "last_question_id": d.last_question_id,
            "updated_at": d.updated_at.isoformat()
        } for d, name, email in results], indent=2)
        return StreamingResponse(io.StringIO(content), media_type="application/json", headers={
            "Content-Disposition": "attachment; filename=submitted_drafts.json"
        })

    # CSV export
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow([
        "id", "apprentice_id", "apprentice_name", "apprentice_email",
        "last_question_id", "updated_at", "answers"
    ])

    for d, name, email in results:
        writer.writerow([
            d.id,
            d.apprentice_id,
            name,
            email,
            d.last_question_id,
            d.updated_at.isoformat(),
            json.dumps(d.answers)
        ])

    csv_buffer.seek(0)
    return StreamingResponse(csv_buffer, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=submitted_drafts.csv"
    })

@router.get("/my-apprentices/{apprentice_id}", response_model=ApprenticeProfileOut)
def get_apprentice_profile(
    apprentice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check mentorship relationship
    link = db.query(MentorApprentice).filter_by(
        mentor_id=current_user.id,
        apprentice_id=apprentice_id
    ).first()

    if not link:
        raise ForbiddenException("Not authorized to access this apprentice")

    apprentice = db.query(User).filter_by(id=apprentice_id, role="apprentice").first()
    if not apprentice:
        raise NotFoundException("Apprentice not found")

    # Fetch stats
    total_assessments = db.query(AssessmentDraft).filter_by(
        apprentice_id=apprentice_id,
        is_submitted=True
    ).count()

    average_score = db.query(func.avg(AssessmentDraft.score)).filter_by(
        apprentice_id=apprentice_id,
        is_submitted=True
    ).scalar()

    last_submission = db.query(func.max(AssessmentDraft.updated_at)).filter_by(
        apprentice_id=apprentice_id,
        is_submitted=True
    ).scalar()

    return ApprenticeProfileOut(
        id=apprentice.id,
        name=apprentice.name,
        email=apprentice.email,
        join_date=apprentice.created_at if hasattr(apprentice, "created_at") else None,
        total_assessments=total_assessments,
        average_score=round(average_score, 2) if average_score else None,
        last_submission=last_submission
    )