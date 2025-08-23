from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.auth import require_mentor_or_admin, get_current_user, require_admin
from app.models.assessment_template import AssessmentTemplate
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.question import Question
from app.models.user import User, UserRole
from app.schemas.assessment_template import (
    AssessmentTemplateCreate, AssessmentTemplateUpdate, AssessmentTemplateOut,
    AddQuestionToTemplate, FullTemplateView, TemplateWithFullQuestions
)
from uuid import uuid4
from app.schemas.user import UserOut

router = APIRouter(prefix="/templates", tags=["Admin Templates"])

@router.post("", response_model=AssessmentTemplateOut)
def create_template(data: AssessmentTemplateCreate, db: Session = Depends(get_db), current_user = Depends(require_mentor_or_admin)):
    template_data = data.dict()
    template_data['created_by'] = current_user.id
    template = AssessmentTemplate(**template_data)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

@router.put("/{template_id}", response_model=AssessmentTemplateOut)
def update_template(
    template_id: str, 
    data: AssessmentTemplateUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(AssessmentTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if this is a master assessment and user is admin
    if template.is_master_assessment and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403, 
            detail="Only administrators can modify the Master Trooth Assessment"
        )
    
    # For regular templates, require mentor or admin permissions
    if current_user.role not in [UserRole.mentor, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Mentors can only edit their own templates (except master assessment)
    if (current_user.role == UserRole.mentor and 
        not template.is_master_assessment and 
        template.created_by != current_user.id):
        raise HTTPException(status_code=403, detail="You can only edit your own templates")
    
    # Update only provided fields
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    return template

@router.delete("/{template_id}")
def delete_template(
    template_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    template = db.query(AssessmentTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Prevent deletion of master assessment
    if template.is_master_assessment:
        raise HTTPException(
            status_code=403, 
            detail="The Master Trooth Assessment cannot be deleted"
        )
    
    # For regular templates, require mentor or admin permissions
    if current_user.role not in [UserRole.mentor, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Mentors can only delete their own templates
    if (current_user.role == UserRole.mentor and 
        template.created_by != current_user.id):
        raise HTTPException(status_code=403, detail="You can only delete your own templates")
    
    # Delete associated questions first
    db.query(AssessmentTemplateQuestion).filter_by(template_id=template_id).delete()
    
    # Delete the template
    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully"}

@router.post("/{template_id}/questions")
def add_question_to_template(
    template_id: str,
    item: AddQuestionToTemplate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Confirm template exists
    template = db.query(AssessmentTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if this is a master assessment and user is admin
    if template.is_master_assessment and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403, 
            detail="Only administrators can modify the Master Trooth Assessment"
        )
    
    # For regular templates, require mentor or admin permissions
    if current_user.role not in [UserRole.mentor, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Mentors can only edit their own templates (except master assessment)
    if (current_user.role == UserRole.mentor and 
        not template.is_master_assessment and 
        template.created_by != current_user.id):
        raise HTTPException(status_code=403, detail="You can only edit your own templates")
    
    # Confirm question exists
    if not db.query(Question).filter_by(id=item.question_id).first():
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Check for duplicate
    existing = db.query(AssessmentTemplateQuestion).filter_by(
        template_id=template_id, question_id=item.question_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Question already in template")

    link = AssessmentTemplateQuestion(
        template_id=template_id,
        question_id=item.question_id,
        order=item.order
    )
    db.add(link)
    db.commit()
    return {"message": "Question added"}

@router.delete("/{template_id}/questions/{question_id}")
def remove_question_from_template(
    template_id: str,
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Confirm template exists
    template = db.query(AssessmentTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if this is a master assessment and user is admin
    if template.is_master_assessment and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403, 
            detail="Only administrators can modify the Master Trooth Assessment"
        )
    
    # For regular templates, require mentor or admin permissions
    if current_user.role not in [UserRole.mentor, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Mentors can only edit their own templates (except master assessment)
    if (current_user.role == UserRole.mentor and 
        not template.is_master_assessment and 
        template.created_by != current_user.id):
        raise HTTPException(status_code=403, detail="You can only edit your own templates")
    
    # Find the link
    link = db.query(AssessmentTemplateQuestion).filter_by(
        template_id=template_id, question_id=question_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Question not found in template")
    
    db.delete(link)
    db.commit()
    return {"message": "Question removed from template"}

@router.get("", response_model=list[AssessmentTemplateOut], dependencies=[Depends(require_mentor_or_admin)])
def list_templates(db: Session = Depends(get_db)):
    return db.query(AssessmentTemplate).all()

@router.get("/{template_id}", response_model=TemplateWithFullQuestions, dependencies=[Depends(require_mentor_or_admin)])
def get_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(AssessmentTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get questions with full details
    links = db.query(AssessmentTemplateQuestion).filter_by(template_id=template_id).order_by(
        AssessmentTemplateQuestion.order
    ).all()

    questions = []
    for link in links:
        question = db.query(Question).filter_by(id=link.question_id).first()
        if question:
            questions.append(question)

    return TemplateWithFullQuestions(
        id=template.id,
        name=template.name,
        description=template.description,
        is_published=template.is_published,
        questions=questions
    )

@router.post("/{template_id}/clone", response_model=AssessmentTemplateOut)
def clone_assessment_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_mentor_or_admin)
):
    template = db.query(AssessmentTemplate).filter(AssessmentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Create new template as a clone
    new_template = AssessmentTemplate(
        id=str(uuid4()),
        name=f"{template.name} (Clone)",
        description=template.description,
        is_published=False,  # Cloned templates start as drafts
        created_by=current_user.id  # Set the current user as creator
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    # Clone all questions associated with the original template
    template_questions = db.query(AssessmentTemplateQuestion).filter_by(template_id=template_id).all()
    for tq in template_questions:
        new_link = AssessmentTemplateQuestion(
            template_id=new_template.id,
            question_id=tq.question_id,
            order=tq.order
        )
        db.add(new_link)
    
    db.commit()
    
    return new_template

@router.post("/{template_id}/publish", response_model=AssessmentTemplateOut, dependencies=[Depends(require_mentor_or_admin)])
def publish_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    template = db.query(AssessmentTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if template.is_published:
        raise HTTPException(status_code=400, detail="Template is already published")
    
    # Check if template has at least one question
    question_count = db.query(AssessmentTemplateQuestion).filter_by(template_id=template_id).count()
    if question_count == 0:
        raise HTTPException(status_code=400, detail="Cannot publish template without questions")
    
    template.is_published = True
    db.commit()
    db.refresh(template)
    
    return template

@router.post("/{template_id}/unpublish", response_model=AssessmentTemplateOut, dependencies=[Depends(require_mentor_or_admin)])
def unpublish_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user)
):
    template = db.query(AssessmentTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if not template.is_published:
        raise HTTPException(status_code=400, detail="Template is not published")
    
    template.is_published = False
    db.commit()
    db.refresh(template)
    
    return template