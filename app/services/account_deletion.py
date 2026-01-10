"""
Account Deletion Service

Handles permanent deletion of user accounts and all associated data.
This is an irreversible operation that removes:
- For Apprentices: assessments, drafts, agreements, resources, mentor relationships
- For Mentors: agreements, invitations, resources, apprentice relationships, notes
"""

from sqlalchemy.orm import Session
from sqlalchemy import delete, text, inspect, or_
import logging

from app.models.user import User, UserRole
from app.models.assessment import Assessment
from app.models.assessment_draft import AssessmentDraft
from app.models.assessment_answer import AssessmentAnswer
from app.models.agreement import Agreement, AgreementToken
from app.models.mentor_apprentice import MentorApprentice
from app.models.mentor_resource import MentorResource
from app.models.mentor_note import MentorNote
from app.models.apprentice_invitation import ApprenticeInvitation
from app.models.notification import Notification
from app.models.assessment_score_history import AssessmentScoreHistory
from app.models.email_send_event import EmailSendEvent

logger = logging.getLogger(__name__)


def _table_exists(db: Session, table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        inspector = inspect(db.bind)
        return table_name in inspector.get_table_names()
    except Exception as e:
        logger.warning(f"Could not check if table {table_name} exists: {e}")
        return False


def _safe_delete(db: Session, model, filter_condition, table_name: str) -> int:
    """
    Safely delete records from a table, handling cases where the table doesn't exist.
    Returns the count of deleted records.
    """
    try:
        if not _table_exists(db, table_name):
            logger.info(f"Table {table_name} does not exist, skipping deletion")
            return 0
        count = db.query(model).filter(filter_condition).delete(synchronize_session=False)
        return count
    except Exception as e:
        logger.warning(f"Could not delete from {table_name}: {e}")
        return 0


def _safe_delete_by_ids(db: Session, model, id_column, ids: list, table_name: str) -> int:
    """
    Safely delete records by ID list from a table, handling cases where the table doesn't exist.
    Returns the count of deleted records.
    """
    if not ids:
        return 0
    try:
        if not _table_exists(db, table_name):
            logger.info(f"Table {table_name} does not exist, skipping deletion")
            return 0
        count = db.query(model).filter(id_column.in_(ids)).delete(synchronize_session=False)
        return count
    except Exception as e:
        logger.warning(f"Could not delete from {table_name}: {e}")
        return 0


def get_account_deletion_summary(db: Session, user: User) -> dict:
    """
    Get a summary of what will be deleted when the account is closed.
    Returns counts of all associated data.
    """
    summary = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "items_to_delete": {}
    }
    
    def safe_count(model, filter_condition, table_name: str) -> int:
        """Safely count records, returning 0 if table doesn't exist."""
        try:
            if not _table_exists(db, table_name):
                return 0
            return db.query(model).filter(filter_condition).count()
        except Exception as e:
            logger.warning(f"Could not count {table_name}: {e}")
            return 0
    
    if user.role == UserRole.apprentice or str(user.role) == "apprentice":
        # Count apprentice-specific data
        # Agreements: Include both linked by ID and by email (pending invites)
        agreement_count = safe_count(
            Agreement, 
            or_(Agreement.apprentice_id == user.id, Agreement.apprentice_email == user.email), 
            "agreements"
        )
        summary["items_to_delete"] = {
            "assessments": safe_count(Assessment, Assessment.apprentice_id == user.id, "assessments"),
            "assessment_drafts": safe_count(AssessmentDraft, AssessmentDraft.apprentice_id == user.id, "assessment_drafts"),
            "agreements": agreement_count,
            "pending_invitations": safe_count(ApprenticeInvitation, ApprenticeInvitation.apprentice_email == user.email, "apprentice_invitations"),
            "shared_resources": safe_count(MentorResource, MentorResource.apprentice_id == user.id, "mentor_resources"),
            "mentor_relationships": safe_count(MentorApprentice, MentorApprentice.apprentice_id == user.id, "mentor_apprentice"),
        }
        
    elif user.role == UserRole.mentor or str(user.role) == "mentor":
        # Count mentor-specific data
        summary["items_to_delete"] = {
            "agreements": safe_count(Agreement, Agreement.mentor_id == user.id, "agreements"),
            "pending_invitations": safe_count(ApprenticeInvitation, ApprenticeInvitation.mentor_id == user.id, "apprentice_invitations"),
            "resources": safe_count(MentorResource, MentorResource.mentor_id == user.id, "mentor_resources"),
            "mentor_notes": safe_count(MentorNote, MentorNote.mentor_id == user.id, "mentor_notes"),
            "apprentice_relationships": safe_count(MentorApprentice, MentorApprentice.mentor_id == user.id, "mentor_apprentice"),
        }
    
    # Common to both roles
    summary["items_to_delete"]["notifications"] = safe_count(Notification, Notification.user_id == user.id, "notifications")
    
    return summary


def delete_apprentice_account(db: Session, user_id: str, user_email: str = None) -> dict:
    """
    Delete an apprentice account and all associated data.
    
    Deletes in order (to respect foreign key constraints):
    1. Assessment answers (through drafts)
    2. Assessment score history
    3. Assessment drafts
    4. Mentor notes (on assessments)
    5. Email send events (references assessments)
    6. Assessments
    7. Agreement tokens
    8. Agreements (by ID and by email - for pending agreements)
    9. Apprentice invitations sent to this email
    10. Mentor resources shared with this apprentice
    11. Mentor-apprentice relationships
    12. Notifications
    13. User record
    """
    deleted_counts = {}
    
    try:
        # 1. Delete assessment answers (via drafts)
        draft_ids = [d.id for d in db.query(AssessmentDraft.id).filter(AssessmentDraft.apprentice_id == user_id).all()]
        if draft_ids:
            count = _safe_delete_by_ids(db, AssessmentAnswer, AssessmentAnswer.assessment_id, draft_ids, "assessment_answers")
            deleted_counts["assessment_answers"] = count
        
        # 2. Delete assessment score history and mentor notes
        assessment_ids = [a.id for a in db.query(Assessment.id).filter(Assessment.apprentice_id == user_id).all()]
        if assessment_ids:
            count = _safe_delete_by_ids(db, AssessmentScoreHistory, AssessmentScoreHistory.assessment_id, assessment_ids, "assessment_score_history")
            deleted_counts["score_history"] = count
            
            # Also delete mentor notes on these assessments
            count = _safe_delete_by_ids(db, MentorNote, MentorNote.assessment_id, assessment_ids, "mentor_notes")
            deleted_counts["mentor_notes"] = count
        
        # 3. Delete assessment drafts
        count = _safe_delete(db, AssessmentDraft, AssessmentDraft.apprentice_id == user_id, "assessment_drafts")
        deleted_counts["assessment_drafts"] = count
        
        # 4. Delete email send events that reference these assessments
        # Must be deleted BEFORE assessments due to foreign key constraint
        if assessment_ids:
            count = _safe_delete_by_ids(db, EmailSendEvent, EmailSendEvent.assessment_id, assessment_ids, "email_send_events")
            deleted_counts["email_send_events"] = count
        
        # 5. Delete assessments
        count = _safe_delete(db, Assessment, Assessment.apprentice_id == user_id, "assessments")
        deleted_counts["assessments"] = count
        
        # 6. Delete agreement tokens (for agreements where apprentice is involved - by ID or email)
        # Build condition for agreements associated with this apprentice
        agreement_filter = Agreement.apprentice_id == user_id
        if user_email:
            agreement_filter = or_(Agreement.apprentice_id == user_id, Agreement.apprentice_email == user_email)
        
        agreement_ids = [a.id for a in db.query(Agreement.id).filter(agreement_filter).all()]
        if agreement_ids:
            count = _safe_delete_by_ids(db, AgreementToken, AgreementToken.agreement_id, agreement_ids, "agreement_tokens")
            deleted_counts["agreement_tokens"] = count
        
        # 7. Delete agreements (by ID and by email for pending agreements)
        count = _safe_delete(db, Agreement, agreement_filter, "agreements")
        deleted_counts["agreements"] = count
        
        # 8. Delete apprentice invitations sent to this email
        if user_email:
            count = _safe_delete(db, ApprenticeInvitation, ApprenticeInvitation.apprentice_email == user_email, "apprentice_invitations")
            deleted_counts["apprentice_invitations"] = count
        
        # 9. Delete mentor resources shared with this apprentice
        count = _safe_delete(db, MentorResource, MentorResource.apprentice_id == user_id, "mentor_resources")
        deleted_counts["mentor_resources"] = count
        
        # 10. Delete mentor-apprentice relationships
        count = _safe_delete(db, MentorApprentice, MentorApprentice.apprentice_id == user_id, "mentor_apprentice")
        deleted_counts["mentor_relationships"] = count
        
        # 11. Delete notifications
        count = _safe_delete(db, Notification, Notification.user_id == user_id, "notifications")
        deleted_counts["notifications"] = count
        
        # 12. Delete the user (this table must exist)
        count = db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        deleted_counts["user"] = count
        
        db.commit()
        logger.info(f"Successfully deleted apprentice account {user_id} and all associated data: {deleted_counts}")
        
        return {
            "success": True,
            "deleted_counts": deleted_counts
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete apprentice account {user_id}: {str(e)}")
        raise


def delete_mentor_account(db: Session, user_id: str) -> dict:
    """
    Delete a mentor account and all associated data.
    
    Deletes in order (to respect foreign key constraints):
    1. Mentor notes
    2. Agreement tokens
    3. Agreements (where mentor is the creator)
    4. Mentor resources
    5. Apprentice invitations
    6. Mentor-apprentice relationships
    7. Email send events (where mentor is sender)
    8. Notifications
    9. Mentor profile
    10. User record
    
    Note: This does NOT delete apprentice assessments - those belong to the apprentice.
    """
    deleted_counts = {}
    
    try:
        # 1. Delete mentor notes authored by this mentor
        count = _safe_delete(db, MentorNote, MentorNote.mentor_id == user_id, "mentor_notes")
        deleted_counts["mentor_notes"] = count
        
        # 2. Delete agreement tokens for agreements created by this mentor
        agreement_ids = [a.id for a in db.query(Agreement.id).filter(Agreement.mentor_id == user_id).all()]
        if agreement_ids:
            count = _safe_delete_by_ids(db, AgreementToken, AgreementToken.agreement_id, agreement_ids, "agreement_tokens")
            deleted_counts["agreement_tokens"] = count
        
        # 3. Delete agreements created by this mentor
        count = _safe_delete(db, Agreement, Agreement.mentor_id == user_id, "agreements")
        deleted_counts["agreements"] = count
        
        # 4. Delete mentor resources
        count = _safe_delete(db, MentorResource, MentorResource.mentor_id == user_id, "mentor_resources")
        deleted_counts["mentor_resources"] = count
        
        # 5. Delete apprentice invitations
        count = _safe_delete(db, ApprenticeInvitation, ApprenticeInvitation.mentor_id == user_id, "apprentice_invitations")
        deleted_counts["apprentice_invitations"] = count
        
        # 6. Delete mentor-apprentice relationships
        count = _safe_delete(db, MentorApprentice, MentorApprentice.mentor_id == user_id, "mentor_apprentice")
        deleted_counts["mentor_relationships"] = count
        
        # 7. Delete email send events where this mentor is the sender
        count = _safe_delete(db, EmailSendEvent, EmailSendEvent.sender_user_id == user_id, "email_send_events")
        deleted_counts["email_send_events"] = count
        
        # 8. Delete notifications
        count = _safe_delete(db, Notification, Notification.user_id == user_id, "notifications")
        deleted_counts["notifications"] = count
        
        # 9. Delete mentor profile (if exists)
        try:
            from app.models.mentor_profile import MentorProfile
            count = _safe_delete(db, MentorProfile, MentorProfile.mentor_id == user_id, "mentor_profiles")
            deleted_counts["mentor_profile"] = count
        except Exception as e:
            logger.warning(f"Could not delete mentor profile: {e}")
        
        # 10. Delete the user (this table must exist)
        count = db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        deleted_counts["user"] = count
        
        db.commit()
        logger.info(f"Successfully deleted mentor account {user_id} and all associated data: {deleted_counts}")
        
        return {
            "success": True,
            "deleted_counts": deleted_counts
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete mentor account {user_id}: {str(e)}")
        raise


def delete_user_account(db: Session, user: User) -> dict:
    """
    Main entry point for account deletion.
    Routes to the appropriate deletion function based on user role.
    """
    role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    
    if role == "apprentice":
        return delete_apprentice_account(db, user.id, user.email)
    elif role == "mentor":
        return delete_mentor_account(db, user.id)
    else:
        raise ValueError(f"Cannot delete account with role: {role}")
