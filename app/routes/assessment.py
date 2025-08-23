from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import assessment as assessment_schema
from app.models import assessment as assessment_model, user as user_model, mentor_apprentice as mentor_model
from app.db import get_db
from app.services.auth import verify_token
from app.services import ai_scoring
from app.services.email import send_assessment_email
from app.exceptions import ForbiddenException, NotFoundException
from typing import List
import uuid

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

        mentor_link = db.query(mentor_model.MentorApprentice).filter_by(apprentice_id=user_id).first()
        if not mentor_link:
            raise HTTPException(status_code=400, detail="No mentor relationship found.")

        mentor = db.query(user_model.User).filter_by(id=mentor_link.mentor_id).first()
        if not mentor:
            raise NotFoundException("Mentor not found.")

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
        apprentice_relationship = db.query(mentor_model.MentorApprentice).filter_by(apprentice_id=user_id).first()
        
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
        apprentice_relationship = db.query(mentor_model.MentorApprentice).filter_by(
            apprentice_id=user_id
        ).first()
        
        # User must be either the mentor of this apprentice or the apprentice themselves
        if not (mentor_relationship or (apprentice_relationship and apprentice_relationship.apprentice_id == assessment.apprentice_id)):
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