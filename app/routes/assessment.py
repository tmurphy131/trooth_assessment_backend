from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import assessment as assessment_schema
from app.models import assessment as assessment_model, user as user_model, mentor_apprentice as mentor_model
from app.db import get_db
from app.services.auth import verify_token, get_current_user, is_premium_user
from app.services import ai_scoring
from app.services.email import send_assessment_email
from app.exceptions import ForbiddenException, NotFoundException
from app.models.user import User
from typing import List
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=assessment_schema.AssessmentOut)
def create_assessment(
    assessment_input: assessment_schema.AssessmentCreate,
    db: Session = Depends(get_db),
    decoded_token=Depends(verify_token)
):
    try:
        user_id = decoded_token["uid"]
        if user_id != assessment_input.user_id:
            raise ForbiddenException("User ID does not match authenticated user.")

        apprentice = db.query(user_model.User).filter(user_model.User.id == user_id).first()
        if not apprentice:
            raise NotFoundException("User not found.")

        mentor_links = db.query(mentor_model.MentorApprentice).filter_by(apprentice_id=user_id, active=True).all()
        if not mentor_links:
            raise HTTPException(status_code=400, detail="No active mentor relationship found.")

        ai_result = ai_scoring.score_assessment(assessment_input.answers)

        db_assessment = assessment_model.Assessment(
            id=str(uuid.uuid4()),
            title=assessment_input.title,
            user_id=user_id,
            score=ai_result.get("overall_score"),
            feedback=ai_result.get("summary_feedback")
        )
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)

        for link in mentor_links:
            mentor = db.query(user_model.User).filter_by(id=link.mentor_id).first()
            if not mentor or not mentor.email:
                continue
            send_assessment_email(
                to_email=mentor.email,
                apprentice_name=apprentice.name,
                assessment_title=assessment_input.title,
                score=ai_result.get("overall_score"),
                feedback_summary=ai_result.get("summary_feedback"),
                details=ai_result.get("details")
            )

        return db_assessment

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[assessment_schema.AssessmentOut])
def list_assessments(
    db: Session = Depends(get_db),
    decoded_token=Depends(verify_token)
):
    """List assessments for the authenticated user (apprentice view) or their apprentices (mentor view)."""
    try:
        user_id = decoded_token["uid"]
        
        # Check if user is a mentor or apprentice
        mentor_relationships = db.query(mentor_model.MentorApprentice).filter_by(mentor_id=user_id).all()
        apprentice_relationship = db.query(mentor_model.MentorApprentice).filter_by(apprentice_id=user_id, active=True).first()
        
        if mentor_relationships:
            # User is a mentor - show all apprentice assessments
            apprentice_ids = [rel.apprentice_id for rel in mentor_relationships]
            assessments = db.query(assessment_model.Assessment).filter(
                assessment_model.Assessment.apprentice_id.in_(apprentice_ids)
            ).order_by(assessment_model.Assessment.created_at.desc()).all()
        elif apprentice_relationship:
            # User is an apprentice - show only their assessments
            assessments = db.query(assessment_model.Assessment).filter_by(
                apprentice_id=user_id
            ).order_by(assessment_model.Assessment.created_at.desc()).all()
        else:
            # User has no relationships
            return []
        
        # Convert to response format
        result = []
        for assessment in assessments:
            # Get apprentice info
            apprentice = db.query(user_model.User).filter_by(id=assessment.apprentice_id).first()
            
            # Parse scores JSON
            scores_data = assessment.scores or {}
            
            # Ensure we have a valid apprentice name
            apprentice_name = "Unknown"
            if apprentice and apprentice.name:
                apprentice_name = apprentice.name
            elif apprentice and apprentice.email:
                apprentice_name = apprentice.email  # fallback to email
            
            assessment_out = assessment_schema.AssessmentOut(
                id=assessment.id,
                apprentice_id=assessment.apprentice_id,
                apprentice_name=apprentice_name,
                answers=assessment.answers,
                scores=scores_data,
                created_at=assessment.created_at
            )
            result.append(assessment_out)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assessment_id}/status")
def check_assessment_status(
    assessment_id: str,
    db: Session = Depends(get_db),
    decoded_token=Depends(verify_token)
):
    """Lightweight status endpoint for client polling."""
    try:
        user_id = decoded_token["uid"]
        a = db.query(assessment_model.Assessment).filter_by(id=assessment_id).first()
        if not a:
            raise NotFoundException("Assessment not found.")
        # authorization: user is apprentice or mentor of apprentice
        mentor_rel = db.query(mentor_model.MentorApprentice).filter_by(mentor_id=user_id, apprentice_id=a.apprentice_id).first()
        is_apprentice = (user_id == a.apprentice_id)
        if not (mentor_rel or is_apprentice):
            raise ForbiddenException("Not allowed.")
        scores = a.scores or {}
        overall = scores.get('overall_score') if isinstance(scores, dict) else None
        return {
            "id": a.id,
            "status": getattr(a, 'status', None) or ("done" if a.scores else "processing"),
            "has_scores": bool(a.scores),
            "overall_score": overall,
            "updated_at": getattr(a, 'updated_at', None) or a.created_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/self", response_model=list[assessment_schema.AssessmentOut])
def list_own_assessments(
    db: Session = Depends(get_db),
    decoded_token=Depends(verify_token)
):
    """List all submitted assessments for the currently authenticated user (any role)."""
    user_id = decoded_token["uid"]
    rows = (
        db.query(assessment_model.Assessment)
        .filter_by(apprentice_id=user_id)
        .order_by(assessment_model.Assessment.created_at.desc())
        .all()
    )
    user = db.query(user_model.User).filter_by(id=user_id).first()
    user_name = (user.name or user.email) if user else "Unknown"
    return [
        assessment_schema.AssessmentOut(
            id=a.id,
            apprentice_id=a.apprentice_id,
            apprentice_name=user_name,
            template_id=a.template_id,
            answers=a.answers,
            scores=a.scores or {},
            created_at=a.created_at,
        )
        for a in rows
    ]


@router.get("/{assessment_id}/my-full-report", response_model=dict)
def get_own_full_report(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full AI report for the current user's own assessment (premium feature).

    Works for any role (apprentice or mentor). Returns 403 if not premium,
    404 if not found or not owned by this user.
    """
    from app.services.ai_scoring import generate_full_report, _build_v2_prompt_input
    from app.models.assessment_template_question import AssessmentTemplateQuestion
    from app.models.question import Question
    from app.models.category import Category
    from app.models.assessment_draft import AssessmentDraft
    from sqlalchemy.orm import joinedload
    from datetime import datetime, UTC

    if not is_premium_user(current_user):
        raise HTTPException(status_code=403, detail="Premium subscription required for full reports")

    # Resolve by Assessment.id first, then fall back to draft id
    assessment = db.query(assessment_model.Assessment).filter(
        assessment_model.Assessment.id == assessment_id,
        assessment_model.Assessment.apprentice_id == current_user.id,
    ).first()

    draft = None
    if assessment:
        draft = db.query(AssessmentDraft).filter(
            AssessmentDraft.template_id == assessment.template_id,
            AssessmentDraft.apprentice_id == current_user.id,
            AssessmentDraft.is_submitted == True,
        ).order_by(AssessmentDraft.updated_at.desc()).first()
    else:
        draft = db.query(AssessmentDraft).filter(
            AssessmentDraft.id == assessment_id,
            AssessmentDraft.apprentice_id == current_user.id,
        ).first()
        if draft:
            assessment = db.query(assessment_model.Assessment).filter_by(
                apprentice_id=current_user.id,
                template_id=draft.template_id,
            ).order_by(assessment_model.Assessment.created_at.desc()).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not draft.is_submitted:
        raise HTTPException(status_code=400, detail="Assessment not yet completed")

    # Return cached report if available
    scores = draft.score or {}
    cached = scores.get("full_report_v1")
    if not cached and assessment and assessment.scores:
        cached = assessment.scores.get("full_report_v1")
    if cached:
        return {"report": cached, "cached": True, "draft_id": draft.id,
                "generated_at": scores.get("full_report_generated_at")}

    # Build questions list
    template_questions = (
        db.query(AssessmentTemplateQuestion)
        .options(joinedload(AssessmentTemplateQuestion.question))
        .filter_by(template_id=draft.template_id)
        .order_by(AssessmentTemplateQuestion.order)
        .all()
    )
    questions_list = []
    for tq in template_questions:
        q = tq.question
        if not q:
            continue
        cat_name = "General"
        if q.category_id:
            cat = db.query(Category).filter_by(id=q.category_id).first()
            if cat:
                cat_name = cat.name
        q_dict = {
            "id": str(q.id),
            "text": q.text,
            "question_type": q.question_type.value if hasattr(q.question_type, "value") else str(q.question_type),
            "category": cat_name,
        }
        if q.options:
            q_dict["options"] = [
                {"id": str(opt.id), "text": opt.option_text, "is_correct": opt.is_correct}
                for opt in q.options
            ]
        questions_list.append(q_dict)

    # Gather previous assessments for trend context
    previous_drafts = (
        db.query(AssessmentDraft)
        .filter(
            AssessmentDraft.apprentice_id == current_user.id,
            AssessmentDraft.is_submitted == True,
            AssessmentDraft.id != draft.id,
        )
        .order_by(AssessmentDraft.updated_at.desc())
        .limit(5)
        .all()
    )
    previous_assessments = [
        {
            "date": pd.updated_at.isoformat() if pd.updated_at else None,
            "health_score": (pd.score or {}).get("mentor_blob_v2", {}).get("health_score"),
            "strengths": (pd.score or {}).get("mentor_blob_v2", {}).get("strengths", []),
            "gaps": (pd.score or {}).get("mentor_blob_v2", {}).get("gaps", []),
        }
        for pd in previous_drafts if pd.score
    ]

    user_info = {"id": str(current_user.id), "name": current_user.name or "User", "age": None, "church": None}
    payload, _ = _build_v2_prompt_input(
        apprentice=user_info,
        assessment_id=draft.id,
        template_id=str(draft.template_id),
        submitted_at=draft.updated_at.isoformat() if draft.updated_at else None,
        answers=draft.answers or {},
        questions=questions_list,
        previous_assessments=previous_assessments,
    )

    try:
        full_report = generate_full_report(payload, previous_assessments)
        # Cache in draft
        scores["full_report_v1"] = full_report
        scores["full_report_generated_at"] = datetime.now(UTC).isoformat()
        draft.score = scores
        # Cache in Assessment
        if assessment:
            a_scores = dict(assessment.scores or {})
            a_scores["full_report_v1"] = full_report
            a_scores["full_report_generated_at"] = datetime.now(UTC).isoformat()
            assessment.scores = a_scores
        db.commit()
        return {"report": full_report, "cached": False, "draft_id": draft.id,
                "generated_at": full_report.get("_meta", {}).get("generated_at")}
    except Exception as e:
        logger.error(f"Failed to generate full report for {assessment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate full report: {e}")


@router.get("/{assessment_id}", response_model=assessment_schema.AssessmentOut)
def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    decoded_token=Depends(verify_token)
):
    """Get a specific assessment with detailed feedback."""
    try:
        user_id = decoded_token["uid"]
        
        # Get the assessment
        assessment = db.query(assessment_model.Assessment).filter_by(id=assessment_id).first()
        if not assessment:
            raise NotFoundException("Assessment not found.")
        
        # Check access permissions
        mentor_relationship = db.query(mentor_model.MentorApprentice).filter_by(
            mentor_id=user_id, apprentice_id=assessment.apprentice_id
        ).first()

        # User must be either a mentor linked to this apprentice or the apprentice themselves
        if not (mentor_relationship or user_id == assessment.apprentice_id):
            raise ForbiddenException("You don't have permission to view this assessment.")
        
        # Get apprentice info
        apprentice = db.query(user_model.User).filter_by(id=assessment.apprentice_id).first()
        
        # Parse scores JSON
        scores_data = assessment.scores or {}
        
        # Ensure we have a valid apprentice name
        apprentice_name = "Unknown"
        if apprentice and apprentice.name:
            apprentice_name = apprentice.name
        elif apprentice and apprentice.email:
            apprentice_name = apprentice.email  # fallback to email
        
        assessment_out = assessment_schema.AssessmentOut(
            id=assessment.id,
            apprentice_id=assessment.apprentice_id,
            apprentice_name=apprentice_name,
            answers=assessment.answers,
            scores=scores_data,
            created_at=assessment.created_at
        )
        
        return assessment_out
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))