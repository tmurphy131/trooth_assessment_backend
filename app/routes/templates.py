from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, case
from app.db import get_db
from app.models.assessment_template import AssessmentTemplate
from app.models.mentor_apprentice import MentorApprentice
from app.schemas.assessment_template import AssessmentTemplateOut
from app.services.auth import get_current_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/templates", tags=["Assessment Templates"])

# Define sort order: Master Trooth first, then other master assessments, then by date
def _get_template_sort_order():
    """Returns a case expression for sorting templates:
    1. Master Trooth Assessment (key starts with 'master_trooth') - highest priority
    2. Other master assessments (is_master_assessment = True)
    3. Regular assessments (by created_at desc)
    """
    return case(
        (AssessmentTemplate.key.like('master_trooth%'), 0),  # Master Trooth first
        (AssessmentTemplate.is_master_assessment == True, 1),  # Other global assessments
        else_=2  # Regular assessments
    )

@router.get("/published", response_model=list[AssessmentTemplateOut])
def get_published_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get published assessment templates based on user role and mentor-apprentice relationships."""
    
    sort_priority = _get_template_sort_order()
    
    if current_user.role == UserRole.apprentice:
        # For apprentices: Get the master assessment + templates from assigned mentors
        # plus globally-published templates (created_by is NULL) to allow org-wide/admin templates.
        mentor_relationships = db.query(MentorApprentice).filter(
            MentorApprentice.apprentice_id == current_user.id
        ).all()

        mentor_ids = [rel.mentor_id for rel in mentor_relationships] if mentor_relationships else []

        # Build query conditions using OR logic
        query_conditions = []

        # Always include master assessment
        query_conditions.append(AssessmentTemplate.is_master_assessment == True)

        # Include mentor-created assessments if apprentice has mentors
        if mentor_ids:
            query_conditions.append(
                (AssessmentTemplate.created_by.in_(mentor_ids)) &
                (AssessmentTemplate.is_master_assessment == False)
            )

        templates = (
            db.query(AssessmentTemplate)
            .filter(
                AssessmentTemplate.is_published == True,
                or_(*query_conditions)
            )
            .order_by(
                sort_priority,  # Master Trooth first, then other masters, then rest
                AssessmentTemplate.created_at.desc()
            )
            .all()
        )
        
    elif current_user.role in [UserRole.mentor, UserRole.admin]:
        # For mentors/admins: Get assessments based on their role
        if current_user.role == UserRole.mentor:
            # Mentors see: master assessment + their own assessments
            templates = (
                db.query(AssessmentTemplate)
                .filter(
                    AssessmentTemplate.is_published == True,
                    or_(
                        AssessmentTemplate.is_master_assessment == True,
                        AssessmentTemplate.created_by == current_user.id
                    )
                )
                .order_by(
                    sort_priority,  # Master Trooth first, then other masters, then rest
                    AssessmentTemplate.created_at.desc()
                )
                .all()
            )
        else:
            # Admins see all published templates
            templates = (
                db.query(AssessmentTemplate)
                .filter(AssessmentTemplate.is_published == True)
                .order_by(
                    sort_priority,  # Master Trooth first, then other masters, then rest
                    AssessmentTemplate.created_at.desc()
                )
                .all()
            )
    else:
        # For other roles, return empty list
        return []
    
    return templates
