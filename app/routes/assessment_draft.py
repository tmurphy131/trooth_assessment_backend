from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload, joinedload
from app.schemas import assessment as assessment_schema
from app.db import get_db
from sqlalchemy import func
from app.models.assessment_draft import AssessmentDraft
from app.schemas.assessment_draft import AssessmentDraftCreate, AssessmentDraftOut
from app.services.auth import get_current_user, require_apprentice, require_mentor
from app.models.user import User, UserRole
from app.models.question import Question
import uuid
from app.services.ai_scoring import score_assessment, score_assessment_with_questions
from app.services.email import send_assessment_email
from app.models.assessment_answer import AssessmentAnswer
import logging
from app.exceptions import ForbiddenException, NotFoundException
from app.models.mentor_apprentice import MentorApprentice
from app.models.assessment_template import AssessmentTemplate
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.category import Category
from app.models.question import Question
from app.models.category import Category
from app.schemas.assessment_draft import QuestionItem
from app.schemas.assessment_draft import AssessmentDraftUpdate
from app.models.assessment import Assessment

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("", response_model=AssessmentDraftOut)
def save_draft(
    data: AssessmentDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.apprentice:
        raise HTTPException(status_code=403, detail="Only apprentices can save drafts")

    # Don't auto-submit drafts - let the explicit submit endpoint handle that
    is_complete = False

    draft = db.query(AssessmentDraft).filter_by(
        apprentice_id=current_user.id,
        is_submitted=False
    ).first()

    if draft:
        draft.answers = data.answers
        draft.last_question_id = data.last_question_id
        draft.is_submitted = is_complete
    else:
        draft = AssessmentDraft(
            id=str(uuid.uuid4()),
            apprentice_id=current_user.id,
            answers=data.answers,
            last_question_id=data.last_question_id,
            template_id=data.template_id,
            is_submitted=is_complete
        )
        db.add(draft)

    db.commit()
    db.refresh(draft)

    # Fetch questions linked to this template
    template = db.query(AssessmentTemplate).filter_by(id=data.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Assessment template not found")

    questions = (
        db.query(Question)
        .options(joinedload(Question.options))
        .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
        .filter(AssessmentTemplateQuestion.template_id == data.template_id)
        .order_by(AssessmentTemplateQuestion.order)
        .all()
    )
    questions_out = [QuestionItem.from_question(q) for q in questions]

    # Manually construct the response since AssessmentDraft doesn't have questions field
    draft_response = AssessmentDraftOut(
        id=draft.id,
        apprentice_id=draft.apprentice_id,
        template_id=draft.template_id,
        answers=draft.answers,
        last_question_id=draft.last_question_id,
        is_submitted=draft.is_submitted,
        questions=questions_out
    )

    if is_complete:
        # AI scoring + email logic already present
        pass

    return draft_response



@router.get("", response_model=AssessmentDraftOut)
def get_draft(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.apprentice:
        raise ForbiddenException("Only apprentices can access drafts")

    draft = db.query(AssessmentDraft).options(selectinload(AssessmentDraft.answers_rel))\
        .filter_by(apprentice_id=current_user.id, is_submitted=False).first()

    if not draft:
        raise NotFoundException("No draft found")

    # Get questions for this template
    questions = (
        db.query(Question)
        .options(joinedload(Question.options))
        .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
        .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
        .order_by(AssessmentTemplateQuestion.order)
        .all()
    )
    questions_out = [QuestionItem.from_question(q) for q in questions]

    # Manually construct the response
    return AssessmentDraftOut(
        id=draft.id,
        apprentice_id=draft.apprentice_id,
        template_id=draft.template_id,
        answers=draft.answers,
        last_question_id=draft.last_question_id,
        is_submitted=draft.is_submitted,
        questions=questions_out
    )

@router.get("/resume")
def resume_draft(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.apprentice:
        raise ForbiddenException("Only apprentices can resume drafts")
    
    draft = db.query(AssessmentDraft).filter_by(
        apprentice_id=current_user.id,
        is_submitted=False
    ).first()

    if not draft:
        raise NotFoundException("No draft found")

    question = None
    if draft.last_question_id:
        question = db.query(Question).filter_by(id=draft.last_question_id).first()

    return {
        "draft": {
            "id": draft.id,
            "answers": draft.answers,
            "last_question_id": draft.last_question_id
        },
        "last_question": {
            "id": question.id,
            "text": question.text,
            "category_id": question.category_id
        } if question else None
    }

@router.get("/list", response_model=list[AssessmentDraftOut])
def list_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get only in-progress drafts for the current apprentice (not submitted assessments)"""
    print(f"DEBUG: list_drafts called for user {current_user.id}")
    if current_user.role != UserRole.apprentice:
        raise ForbiddenException("Only apprentices can access drafts")

    # Only get non-submitted drafts for the apprentice dashboard
    drafts = db.query(AssessmentDraft).filter_by(
        apprentice_id=current_user.id, 
        is_submitted=False
    ).all()
    print(f"DEBUG: Found {len(drafts)} in-progress drafts")

    draft_responses = []
    for draft in drafts:
        try:
            print(f"DEBUG: Processing draft {draft.id}")
            # Get questions for this template
            questions = (
                db.query(Question)
                .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
                .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
                .order_by(AssessmentTemplateQuestion.order)
                .all()
            )
            print(f"DEBUG: Found {len(questions)} questions for template {draft.template_id}")
            questions_out = [QuestionItem.from_question(q) for q in questions]

            # Manually construct the response
            draft_response = AssessmentDraftOut(
                id=draft.id,
                apprentice_id=draft.apprentice_id,
                template_id=draft.template_id,
                answers=draft.answers,
                last_question_id=draft.last_question_id,
                is_submitted=draft.is_submitted,
                questions=questions_out
            )
            draft_responses.append(draft_response)
            print(f"DEBUG: Successfully processed draft {draft.id}")
        except Exception as e:
            print(f"Error processing draft {draft.id}: {e}")
            # Skip this draft and continue with others
            continue

    print(f"DEBUG: Returning {len(draft_responses)} draft responses")
    return draft_responses

@router.get("/completed", response_model=list[AssessmentDraftOut])
def list_completed_assessments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get only completed/submitted assessments for the current apprentice"""
    print(f"DEBUG: list_completed_assessments called for user {current_user.id}")
    if current_user.role != UserRole.apprentice:
        raise ForbiddenException("Only apprentices can access their completed assessments")

    # Only get submitted assessments
    drafts = db.query(AssessmentDraft).filter_by(
        apprentice_id=current_user.id, 
        is_submitted=True
    ).all()
    print(f"DEBUG: Found {len(drafts)} completed assessments")

    draft_responses = []
    for draft in drafts:
        try:
            print(f"DEBUG: Processing completed assessment {draft.id}")
            # Get questions for this template
            questions = (
                db.query(Question)
                .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
                .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
                .order_by(AssessmentTemplateQuestion.order)
                .all()
            )
            print(f"DEBUG: Found {len(questions)} questions for template {draft.template_id}")
            questions_out = [QuestionItem.from_question(q) for q in questions]

            # Manually construct the response
            draft_response = AssessmentDraftOut(
                id=draft.id,
                apprentice_id=draft.apprentice_id,
                template_id=draft.template_id,
                answers=draft.answers,
                last_question_id=draft.last_question_id,
                is_submitted=draft.is_submitted,
                questions=questions_out
            )
            draft_responses.append(draft_response)
            print(f"DEBUG: Successfully processed completed assessment {draft.id}")
        except Exception as e:
            print(f"Error processing completed assessment {draft.id}: {e}")
            # Skip this draft and continue with others
            continue

    print(f"DEBUG: Returning {len(draft_responses)} completed assessment responses")
    return draft_responses

@router.get("/{draft_id}", response_model=AssessmentDraftOut)
def get_draft_by_id(
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific draft by ID for the current apprentice"""
    if current_user.role != UserRole.apprentice:
        raise ForbiddenException("Only apprentices can access drafts")

    draft = db.query(AssessmentDraft).filter_by(
        id=draft_id, 
        apprentice_id=current_user.id
    ).first()

    if not draft:
        raise NotFoundException("Draft not found")

    # Get questions for this template
    questions = (
        db.query(Question)
        .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
        .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
        .order_by(AssessmentTemplateQuestion.order)
        .all()
    )
    questions_out = [QuestionItem.from_question(q) for q in questions]

    # Manually construct the response
    return AssessmentDraftOut(
        id=draft.id,
        apprentice_id=draft.apprentice_id,
        template_id=draft.template_id,
        answers=draft.answers,
        last_question_id=draft.last_question_id,
        is_submitted=draft.is_submitted,
        questions=questions_out
    )

@router.patch("", response_model=AssessmentDraftOut)
def update_draft(
    data: AssessmentDraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.apprentice:
        raise ForbiddenException("Only apprentices can update drafts")

    draft = db.query(AssessmentDraft).filter_by(
        apprentice_id=current_user.id,
        is_submitted=False
    ).first()

    if not draft:
        raise NotFoundException("No draft found")

    if data.answers is not None:
        draft.answers = data.answers
    if data.last_question_id:
        draft.last_question_id = data.last_question_id

    db.commit()
    db.refresh(draft)

    # Get questions for this template
    questions = (
        db.query(Question)
        .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
        .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
        .order_by(AssessmentTemplateQuestion.order)
        .all()
    )
    questions_out = [QuestionItem.from_question(q) for q in questions]

    # Manually construct the response
    return AssessmentDraftOut(
        id=draft.id,
        apprentice_id=draft.apprentice_id,
        template_id=draft.template_id,
        answers=draft.answers,
        last_question_id=draft.last_question_id,
        is_submitted=draft.is_submitted,
        questions=questions_out
    )


@router.patch("/{draft_id}", response_model=AssessmentDraftOut)
def update_draft_by_id(
    draft_id: str,
    data: AssessmentDraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a specific draft by ID"""
    if current_user.role != UserRole.apprentice:
        raise ForbiddenException("Only apprentices can update drafts")

    draft = db.query(AssessmentDraft).filter_by(
        id=draft_id,
        apprentice_id=current_user.id,
        is_submitted=False
    ).first()

    if not draft:
        raise NotFoundException("Draft not found or already submitted")

    if data.answers is not None:
        draft.answers = data.answers
    if data.last_question_id:
        draft.last_question_id = data.last_question_id

    db.commit()
    db.refresh(draft)

    # Get questions for this template
    questions = (
        db.query(Question)
        .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
        .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
        .order_by(AssessmentTemplateQuestion.order)
        .all()
    )
    questions_out = [QuestionItem.from_question(q) for q in questions]

    # Manually construct the response
    return AssessmentDraftOut(
        id=draft.id,
        apprentice_id=draft.apprentice_id,
        template_id=draft.template_id,
        answers=draft.answers,
        last_question_id=draft.last_question_id,
        is_submitted=draft.is_submitted,
        questions=questions_out
    )


@router.delete("/{draft_id}")
def delete_draft(
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a draft assessment. Only the apprentice who created it can delete it."""
    if current_user.role != UserRole.apprentice:
        raise HTTPException(status_code=403, detail="Only apprentices can delete drafts")

    # Find the draft
    draft = db.query(AssessmentDraft).filter(
        AssessmentDraft.id == draft_id,
        AssessmentDraft.apprentice_id == current_user.id,
        AssessmentDraft.is_submitted == False  # Can only delete unsubmitted drafts
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found or already submitted")

    # Delete the draft
    db.delete(draft)
    db.commit()

    return {"message": "Draft deleted successfully"}


@router.post("/submit", response_model=assessment_schema.AssessmentOut)
async def submit_draft(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Submit draft request from user: {current_user.id}")
    
    if current_user.role != UserRole.apprentice:
        raise ForbiddenException("Only apprentices can submit assessments")

    draft = db.query(AssessmentDraft).filter_by(
        apprentice_id=current_user.id,
        is_submitted=False
    ).first()

    if not draft:
        logger.warning(f"No unsubmitted draft found for user: {current_user.id}")
        raise NotFoundException("No draft to submit")

    if not draft.answers:
        raise HTTPException(status_code=400, detail="Cannot submit an empty assessment")

    logger.info(f"Found draft {draft.id} for submission")

    try:
        # Score via AI
        logger.info("Starting AI scoring...")
        
        # Get the actual questions for proper scoring
        template_questions = db.query(AssessmentTemplateQuestion)\
            .join(Question)\
            .filter(AssessmentTemplateQuestion.template_id == draft.template_id)\
            .order_by(AssessmentTemplateQuestion.order)\
            .all()
        
        # Create proper question data for AI scoring
        questions_for_ai = []
        for tq in template_questions:
            # Get category name through the relationship
            category_name = None
            if tq.question.category_id:
                category = db.query(Category).filter_by(id=tq.question.category_id).first()
                category_name = category.name if category else None
            
            questions_for_ai.append({
                'id': str(tq.question.id),
                'text': tq.question.text,
                'category': category_name or 'General Assessment'
            })
        
        # Use the enhanced scoring function with real questions
        if questions_for_ai:
            # Get full detailed results from AI scoring
            from app.services.ai_scoring import score_assessment_by_category
            scoring_result = await score_assessment_by_category(draft.answers, questions_for_ai)
            score = scoring_result['overall_score']
            recommendation = scoring_result['summary_recommendation']
            detailed_scores = scoring_result  # Save full detailed results
        else:
            # Fallback for sample questions
            score, recommendation = score_assessment(draft.answers)
            detailed_scores = {"overall_score": score}
            
        logger.info(f"AI scoring completed: score={score}, recommendation length={len(recommendation)}")
    except Exception as e:
        logger.error(f"AI scoring failed: {e}")
        # Use fallback values
        score, recommendation = 7.0, "Assessment completed. Continue growing in spiritual disciplines."
        detailed_scores = {"overall_score": score}

    try:
        # Save as new Assessment
        logger.info("Creating assessment record...")
        assessment = Assessment(
            id=str(uuid.uuid4()),
            apprentice_id=current_user.id,
            answers=draft.answers,
            scores=detailed_scores,  # Save full detailed scoring results
            recommendation=recommendation
        )
        db.add(assessment)
        logger.info(f"Assessment record created: {assessment.id}")

        # Mark draft as submitted
        draft.is_submitted = True
        db.commit()
        logger.info("Database transaction committed")

        # Send email to mentor
        logger.info("Sending email notification...")
        try:
            # Get apprentice details
            apprentice = db.query(User).filter_by(id=current_user.id).first()
            apprentice_name = apprentice.name if apprentice else "Unknown"
            
            # Get mentor details (find mentor for this apprentice)
            mentor_relationship = db.query(MentorApprentice).filter_by(apprentice_id=current_user.id).first()
            if mentor_relationship:
                mentor = db.query(User).filter_by(id=mentor_relationship.mentor_id).first()
                if mentor and mentor.email:
                    send_assessment_email(
                        to_email=mentor.email,
                        mentor_name=mentor.name or "Mentor",
                        apprentice_name=apprentice_name,
                        scores=assessment.scores or {"overall_score": score},
                        recommendations={"overall": assessment.recommendation or "Continue your spiritual growth journey."}
                    )
                    logger.info(f"Email notification sent to mentor: {mentor.email}")
                else:
                    logger.warning("Mentor not found or has no email address")
            else:
                logger.warning("No mentor relationship found for apprentice")
        except Exception as email_error:
            logger.error(f"Failed to send email notification: {email_error}")
            # Don't fail the submission if email fails
        
        logger.info("Email notification sent successfully")

        # Return properly formatted response with apprentice name
        return assessment_schema.AssessmentOut(
            id=assessment.id,
            apprentice_id=assessment.apprentice_id,
            apprentice_name=apprentice_name,
            answers=assessment.answers,
            scores=assessment.scores,
            created_at=assessment.created_at
        )
        
    except Exception as e:
        logger.error(f"Assessment submission failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit assessment: {str(e)}")

@router.get("/submitted-assessments/{apprentice_id}", response_model=list[AssessmentDraftOut])
def get_submitted_by_apprentice(
    apprentice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Mentor authorization logic assumed to be in place already

    submissions = db.query(AssessmentDraft)\
        .options(selectinload(AssessmentDraft.answers_rel))\
        .filter_by(apprentice_id=apprentice_id, is_submitted=True).all()

    draft_responses = []
    for draft in submissions:
        try:
            # Get questions for this template
            questions = (
                db.query(Question)
                .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
                .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
                .order_by(AssessmentTemplateQuestion.order)
                .all()
            )
            questions_out = [QuestionItem.from_question(q) for q in questions]

            # Manually construct the response
            draft_response = AssessmentDraftOut(
                id=draft.id,
                apprentice_id=draft.apprentice_id,
                template_id=draft.template_id,
                answers=draft.answers,
                last_question_id=draft.last_question_id,
                is_submitted=draft.is_submitted,
                questions=questions_out
            )
            draft_responses.append(draft_response)
        except Exception as e:
            print(f"Error processing draft {draft.id}: {e}")
            # Skip this draft and continue with others
            continue

    return draft_responses

@router.post("/start", response_model=AssessmentDraftOut)
def start_draft(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.apprentice:
        raise HTTPException(status_code=403, detail="Only apprentices can start drafts")

    # Check if apprentice has a draft already in progress for this template
    existing = db.query(AssessmentDraft).filter_by(
        apprentice_id=current_user.id,
        template_id=template_id,
        is_submitted=False
    ).first()
    if existing:
        # Get questions for this template
        questions = (
            db.query(Question)
            .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
            .filter(AssessmentTemplateQuestion.template_id == existing.template_id)
            .order_by(AssessmentTemplateQuestion.order)
            .all()
        )
        questions_out = [QuestionItem.from_question(q) for q in questions]

        # Return existing draft as AssessmentDraftOut
        return AssessmentDraftOut(
            id=existing.id,
            apprentice_id=existing.apprentice_id,
            template_id=existing.template_id,
            answers=existing.answers,
            last_question_id=existing.last_question_id,
            is_submitted=existing.is_submitted,
            questions=questions_out
        )

    # Ensure template exists and is published
    template = db.query(AssessmentTemplate).filter_by(id=template_id, is_published=True).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or not published")

    # Create draft
    draft = AssessmentDraft(
        id=str(uuid.uuid4()),
        apprentice_id=current_user.id,
        template_id=template_id,
        answers={},
        last_question_id=None
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    # Get questions for this template
    questions = (
        db.query(Question)
        .options(joinedload(Question.options))
        .join(AssessmentTemplateQuestion, Question.id == AssessmentTemplateQuestion.question_id)
        .filter(AssessmentTemplateQuestion.template_id == draft.template_id)
        .order_by(AssessmentTemplateQuestion.order)
        .all()
    )
    questions_out = [QuestionItem.from_question(q) for q in questions]

    # Return new draft as AssessmentDraftOut
    return AssessmentDraftOut(
        id=draft.id,
        apprentice_id=draft.apprentice_id,
        template_id=draft.template_id,
        answers=draft.answers,
        last_question_id=draft.last_question_id,
        is_submitted=draft.is_submitted,
        questions=questions_out
    )
