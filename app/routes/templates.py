from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, case
from app.db import get_db
from app.models.assessment_template import AssessmentTemplate
from app.models.mentor_apprentice import MentorApprentice
from app.schemas.assessment_template import AssessmentTemplateOut
from app.services.auth import get_current_user, is_premium_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/templates", tags=["Assessment Templates"])

# =============================================================================
# Free Assessment Configuration
# =============================================================================
# These assessment keys are available to all users, even without premium subscription.
# The Master T[root]H Assessment and Spiritual Gifts are always free.
# To make additional assessments free, add their keys here.
FREE_ASSESSMENT_KEYS = {
    "master_trooth_v1",
    "master_trooth_assessment",
    "master_trooth",  # Match any key starting with master_trooth
    "spiritual_gifts_v1",
    "spiritual_gifts",
}


def is_assessment_free(template: AssessmentTemplate) -> bool:
    """Check if an assessment is free (available to non-premium users).
    
    An assessment is free if:
    1. Its key exactly matches a FREE_ASSESSMENT_KEYS entry, OR
    2. Its key starts with a FREE_ASSESSMENT_KEYS entry (e.g., master_trooth_v2)
    """
    if not template.key:
        return False
    
    template_key = template.key.lower()
    
    # Exact match
    if template_key in FREE_ASSESSMENT_KEYS:
        return True
    
    # Prefix match (for versioned assessments)
    for free_key in FREE_ASSESSMENT_KEYS:
        if template_key.startswith(free_key):
            return True
    
    return False

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
    
    # Add is_locked field based on premium status
    user_is_premium = is_premium_user(current_user)
    
    result = []
    for template in templates:
        # A template is locked if:
        # 1. User is NOT premium, AND
        # 2. The assessment is NOT free
        is_locked = not user_is_premium and not is_assessment_free(template)
        
        # Convert to dict and add is_locked
        template_dict = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "is_published": template.is_published,
            "is_master_assessment": template.is_master_assessment,
            "created_at": template.created_at,
            "created_by": template.created_by,
            "category_ids": [],  # Populated below if needed
            "is_locked": is_locked,
            "key": template.key,
        }
        result.append(template_dict)
    
    return result
