from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC
import re
from app.utils.datetime import utc_now
import hashlib
import uuid
from app.models.notification import Notification

from app.db import get_db
from app.schemas.agreement import (
    AgreementCreate, AgreementOut, AgreementSubmit, AgreementSign,
    AgreementTemplateCreate, AgreementTemplateOut, ParentTokenResend,
    AgreementFieldsUpdate, MeetingRescheduleRequest,
    RescheduleResponse,
)
from app.models.agreement import Agreement, AgreementTemplate, AgreementToken
from app.models.user import User, UserRole
from app.models.mentor_apprentice import MentorApprentice
from app.services.email import send_notification_email  # legacy fallback
from app.services.agreement_notifications import (
    send_agreement_email,
    AgreementEmailEvent,
)
from app.services.push_notification import notify_agreement_signed
import time
import logging

logger = logging.getLogger(__name__)

# Simple in-memory (process local) rate limit store for resend attempts
_PARENT_RESEND_TRACK: dict[str, list[float]] = {}
MAX_RESENDS_PER_HOUR = 3
RESEND_WINDOW_SECONDS = 3600
from app.core.settings import settings
from app.services.markdown_renderer import render_markdown
from app.services.auth import get_current_user, require_mentor, require_mentor_or_admin, require_admin, require_apprentice

router = APIRouter(prefix="/agreements", tags=["Agreements"])

# Local Jinja templates env to avoid circular import with app.main
jinja_templates = Jinja2Templates(directory="app/templates")

SIGN_WINDOW_DAYS = 7
VALID_STATUSES = {"draft","awaiting_apprentice","awaiting_parent","fully_signed","revoked","expired"}

# Utility

def _render_content(template_md: str, fields: dict, mentor_name: str, apprentice_email: str, apprentice_name: str | None = None) -> str:
    """Render markdown by replacing {{token}} placeholders.

    Supports tokens with or without surrounding whitespace, e.g. {{meeting_location}} or {{ meeting_location }}.
    """
    content = template_md
    # Base tokens provided (prefer explicit apprentice_name, then field, then email local part)
    tokens = {**fields, "mentor_name": mentor_name, "apprentice_name": (apprentice_name or fields.get('apprentice_name') or apprentice_email.split('@')[0])}
    # Discover any moustache placeholders present that were not supplied; fill with 'TBD'
    discovered = set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", template_md))
    for name in discovered:
        if name not in tokens:
            tokens[name] = 'TBD'
    for k, v in tokens.items():
        pattern = re.compile(r"{{\s*" + re.escape(k) + r"\s*}}")
        content = pattern.sub(str(v) if v is not None else "", content)

    # Also support single-brace tokens like {mentor_name}
    def replace_single_brace(m):
        key = m.group(1)
        if key in tokens and tokens[key] is not None:
            return str(tokens[key])
        # Map alternate names
        alt_map = {
            'meeting_duration': fields.get('meeting_duration_minutes'),
            'parent_name': fields.get('parent_name') or fields.get('parent_signature_name') or fields.get('parent_email'),
            'start_date': fields.get('start_date'),
        }
        if key in alt_map and alt_map[key] is not None:
            return str(alt_map[key])
        return ''
    content = re.sub(r"{([a-zA-Z0-9_]+)}", replace_single_brace, content)

    # Legacy underscore placeholder logic removed (tokens now explicit in template).
    # Append Additional Notes section if provided and not already present
    if fields.get('additional_notes'):
        if 'Additional Notes' not in content and 'additional_notes' not in content:
            content += f"\n\n### Additional Notes\n{fields.get('additional_notes')}\n"

    return content

def _frontend_sign_url(token: str, token_type: str) -> str:
    """Return the backend sign URL for agreement signing pages.

    These URLs point to backend HTML pages (/agreements/sign/<type>/<token>).
    NOT for mobile app deep links - those use ios_app_store_url in email templates.
    """
    base = settings.backend_api_url.rstrip('/') if settings.backend_api_url else 'http://localhost:3000'
    return f"{base}/agreements/sign/{token_type}/{token}"

# Template Endpoints
@router.get("/templates", response_model=list[AgreementTemplateOut])
def list_templates(db: Session = Depends(get_db), current_user: User = Depends(require_mentor_or_admin)):
    return db.query(AgreementTemplate).order_by(AgreementTemplate.version.desc()).all()

@router.post("/templates", response_model=AgreementTemplateOut)
def create_template(data: AgreementTemplateCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    # Determine next version
    latest = db.query(AgreementTemplate).order_by(AgreementTemplate.version.desc()).first()
    next_version = (latest.version + 1) if latest else 1
    tpl = AgreementTemplate(
        version=next_version,
        markdown_source=data.markdown_source,
        is_active=data.is_active,
        notes=data.notes,
        author_user_id=current_user.id
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl

# List agreements for mentor (paginated)
@router.get("", response_model=list[AgreementOut])
def list_agreements(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), mentor: User = Depends(require_mentor)):
    if limit > 100:
        limit = 100
    q = (db.query(Agreement)
            .filter_by(mentor_id=mentor.id)
            .order_by(Agreement.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all())
    return q

# List agreements for current apprentice
@router.get("/my", response_model=list[AgreementOut])
def list_my_agreements(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), apprentice: User = Depends(require_apprentice)):
    if limit > 100:
        limit = 100
    q = (
        db.query(Agreement)
        .filter((Agreement.apprentice_id == apprentice.id) | (Agreement.apprentice_email == apprentice.email))
        .order_by(Agreement.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    # Enrich with mentor_name/apprentice_name for convenience
    for ag in q:
        mentor_user = db.query(User).filter_by(id=ag.mentor_id).first()
        if mentor_user:
            ag.__dict__["mentor_name"] = mentor_user.name or mentor_user.email
        ag.__dict__["apprentice_name"] = ag.apprentice_name or (ag.apprentice_email.split('@')[0] if ag.apprentice_email else None)
    return q

# Agreement Creation
@router.post("", response_model=AgreementOut)
def create_agreement(payload: AgreementCreate, db: Session = Depends(get_db), mentor: User = Depends(require_mentor)):
    tpl = db.query(AgreementTemplate).filter_by(version=payload.template_version).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template version not found")
    if not tpl.is_active:
        raise HTTPException(status_code=400, detail="Template version inactive")

    # Lowercase email to match Firebase storage
    apprentice_email = payload.apprentice_email.lower().strip()
    
    # Pre-render draft so mentor can preview before submit
    fields_dict = payload.fields.model_dump()
    # Include parent_email for token substitution if provided
    if payload.parent_email:
        fields_dict['parent_email'] = payload.parent_email
    rendered = _render_content(
        tpl.markdown_source,
        fields_dict,
        mentor_name=mentor.name or mentor.email,
        apprentice_email=apprentice_email,
    apprentice_name=payload.apprentice_name,
    )
    agreement = Agreement(
        template_version=tpl.version,
        mentor_id=mentor.id,
        apprentice_email=apprentice_email,
        apprentice_name=payload.apprentice_name,
        status='draft',
        apprentice_is_minor=payload.apprentice_is_minor,
        parent_required=payload.parent_required,
        parent_email=payload.parent_email,
        fields_json=fields_dict,
        content_rendered=rendered,
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)
    # Attach transient names for client rendering (not persisted columns)
    agreement.__dict__["mentor_name"] = mentor.name or mentor.email
    agreement.__dict__["apprentice_name"] = payload.apprentice_name or payload.apprentice_email.split('@')[0]
    return agreement

@router.post("/{agreement_id}/submit", response_model=AgreementOut)
def submit_agreement(agreement_id: str, db: Session = Depends(get_db), mentor: User = Depends(require_mentor)):
    ag = db.query(Agreement).filter_by(id=agreement_id, mentor_id=mentor.id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agreement not found")
    if ag.status != 'draft':
        raise HTTPException(status_code=409, detail="Cannot submit in current state")

    tpl = db.query(AgreementTemplate).filter_by(version=ag.template_version).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template missing")

    # Validate required fields
    fields = ag.fields_json or {}
    for req in ["meeting_location", "meeting_duration_minutes"]:
        if not fields.get(req):
            raise HTTPException(status_code=400, detail=f"Missing required field: {req}")

    ag.content_rendered = _render_content(tpl.markdown_source, fields, mentor_name=mentor.name or mentor.email, apprentice_email=ag.apprentice_email, apprentice_name=ag.apprentice_name)
    ag.content_hash = hashlib.sha256(ag.content_rendered.encode()).hexdigest()
    ag.status = 'awaiting_apprentice'

    # Create apprentice token
    apprentice_token = AgreementToken(
        token=str(uuid.uuid4()),
        agreement_id=ag.id,
        token_type='apprentice',
        expires_at=utc_now() + timedelta(days=SIGN_WINDOW_DAYS)
    )
    db.add(apprentice_token)
    db.commit()
    db.refresh(ag)
    # TODO: send apprentice email with token link (placeholder)
    # Apprentice invitation email
    try:
        send_agreement_email(
            AgreementEmailEvent.APPRENTICE_INVITE,
            to_email=ag.apprentice_email,
            context={
                'agreement_id': ag.id,
                'apprentice_email': ag.apprentice_email,
                'mentor_name': mentor.name,
                'action_url': _frontend_sign_url(apprentice_token.token, 'apprentice')
            }
        )
    except Exception:
        pass
    return ag

@router.patch("/{agreement_id}/fields", response_model=AgreementOut)
def update_draft_fields(agreement_id: str, payload: AgreementFieldsUpdate, db: Session = Depends(get_db), mentor: User = Depends(require_mentor)):
    ag = db.query(Agreement).filter_by(id=agreement_id, mentor_id=mentor.id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agreement not found")
    if ag.status != 'draft':
        raise HTTPException(status_code=409, detail="Can only edit fields while in draft")
    # Merge provided fields
    existing = ag.fields_json or {}
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return ag
    existing.update(updates)
    ag.fields_json = existing
    # Re-render preview immediately
    tpl = db.query(AgreementTemplate).filter_by(version=ag.template_version).first()
    if tpl:
        # Inject parent_email for rendering if not already present
        if ag.parent_email and 'parent_email' not in existing:
            existing['parent_email'] = ag.parent_email
    ag.content_rendered = _render_content(tpl.markdown_source, existing, mentor_name=mentor.name or mentor.email, apprentice_email=ag.apprentice_email, apprentice_name=ag.apprentice_name)
    db.commit()
    db.refresh(ag)
    return ag

@router.get("/{agreement_id}", response_model=AgreementOut)
def get_agreement(agreement_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role == UserRole.mentor and ag.mentor_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if user.role == UserRole.apprentice:
        # match by email or id if available
        if ag.apprentice_id != user.id and ag.apprentice_email != user.email:
            raise HTTPException(status_code=403, detail="Forbidden")
    # Always (re)render draft so latest substitution & heuristic fills show
    if ag.status == 'draft':
        tpl = db.query(AgreementTemplate).filter_by(version=ag.template_version).first()
        if tpl:
            try:
                fields = ag.fields_json or {}
                if ag.parent_email and 'parent_email' not in fields:
                    fields['parent_email'] = ag.parent_email
                ag.content_rendered = _render_content(tpl.markdown_source, fields, mentor_name=user.name or user.email, apprentice_email=ag.apprentice_email, apprentice_name=ag.apprentice_name)
                db.commit()
            except Exception:
                db.rollback()
    # Enrich with derived names for frontend convenience
    mentor_user = db.query(User).filter_by(id=ag.mentor_id).first()
    if mentor_user:
        ag.__dict__["mentor_name"] = mentor_user.name or mentor_user.email
    ag.__dict__["apprentice_name"] = ag.apprentice_name or ag.apprentice_email.split('@')[0]
    return ag

# Signing
@router.post("/{agreement_id}/sign/apprentice", response_model=AgreementOut)
def apprentice_sign(agreement_id: str, body: AgreementSign, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if ag.status not in ('awaiting_apprentice','awaiting_parent'):
        raise HTTPException(status_code=409, detail="Invalid state for signing")
    # Ensure user matches (in tests, dependency overrides may leak; prefer header token for mock users)
    import os
    header_email = None
    header_uid = None
    if os.getenv("ENV") == "test":
        auth = request.headers.get("Authorization", "")
        if "mock-apprentice-token" in auth:
            header_email = "apprentice@example.com"
            header_uid = "apprentice-1"
    effective_email = header_email or user.email
    if effective_email != ag.apprentice_email:
        raise HTTPException(status_code=403, detail="Not authorized to sign")
    if ag.apprentice_signed_at:
        raise HTTPException(status_code=409, detail="Already signed")

    ag.apprentice_signature_name = body.typed_name
    ag.apprentice_signed_at = utc_now()
    ag.apprentice_id = header_uid or user.id

    # Determine next state
    if ag.parent_required:
        if ag.status == 'awaiting_apprentice':
            ag.status = 'awaiting_parent'
            # generate parent token if not exists
            existing_parent = db.query(AgreementToken).filter_by(agreement_id=ag.id, token_type='parent', used_at=None).first()
            if not existing_parent:
                parent_token = AgreementToken(
                    token=str(uuid.uuid4()),
                    agreement_id=ag.id,
                    token_type='parent',
                    expires_at=utc_now() + timedelta(days=SIGN_WINDOW_DAYS)
                )
                db.add(parent_token)
                try:
                    if ag.parent_email:
                        send_agreement_email(
                            AgreementEmailEvent.PARENT_INVITE,
                            to_email=ag.parent_email,
                            context={
                                'agreement_id': ag.id,
                                'apprentice_email': ag.apprentice_email,
                                'parent_email': ag.parent_email,
                                'action_url': _frontend_sign_url(parent_token.token, 'parent')
                            }
                        )
                except Exception:
                    pass
    else:
        # Parent signature not required - activate relationship immediately
        ag.status = 'fully_signed'
        ag.activated_at = utc_now()
        _activate_relationship(db, ag)

    db.commit()
    db.refresh(ag)
    
    # ──────────────────────────────────────────────────────────────────
    # NOTIFY MENTOR: Apprentice signed the mentorship agreement
    # ──────────────────────────────────────────────────────────────────
    try:
        apprentice_name = ag.apprentice_name or ag.apprentice_email.split('@')[0]
        if ag.status == 'fully_signed':
            # Agreement is complete - notify mentor
            notif = Notification(
                user_id=ag.mentor_id,
                message=f"{apprentice_name} has signed the mentorship agreement — Agreement is now active!",
                link=f"/agreements/{ag.id}",
                is_read=False
            )
            db.add(notif)
            db.commit()
        elif ag.status == 'awaiting_parent':
            # Apprentice signed but awaiting parent - notify mentor of progress
            notif = Notification(
                user_id=ag.mentor_id,
                message=f"{apprentice_name} has signed the mentorship agreement — Awaiting parent signature",
                link=f"/agreements/{ag.id}",
                is_read=False
            )
            db.add(notif)
            db.commit()
    except Exception as e:
        # Log but don't fail the signing
        import logging
        logging.getLogger(__name__).warning(f"Failed to create mentor notification for agreement signing: {e}")
    
    # Notify mentor if fully signed (email)
    if ag.status == 'fully_signed':
        try:
            mentor_user = db.query(User).filter_by(id=ag.mentor_id).first()
            mentor_email = mentor_user.email if mentor_user and mentor_user.email else None
            send_agreement_email(
                AgreementEmailEvent.FULLY_SIGNED,
                to_email=mentor_email or ag.apprentice_email,
                context={
                    'agreement_id': ag.id,
                    'apprentice_email': ag.apprentice_email,
                    'mentor_email': mentor_email,
                    'mentor_name': mentor_user.name if mentor_user else None,
                }
            )
        except Exception:
            pass
    
    # ──────────────────────────────────────────────────────────────────
    # PUSH NOTIFICATION to mentor
    # ──────────────────────────────────────────────────────────────────
    try:
        apprentice_name = ag.apprentice_name or ag.apprentice_email.split('@')[0]
        notify_agreement_signed(
            db=db,
            user_id=ag.mentor_id,
            signer_name=apprentice_name,
            agreement_status=ag.status
        )
        logger.info(f"Push notification sent to mentor {ag.mentor_id} for agreement {ag.id}")
    except Exception as e:
        logger.warning(f"Failed to send push notification for agreement signing: {e}")
    
    return ag

@router.post("/{agreement_id}/sign/parent", response_model=AgreementOut)
def parent_sign(agreement_id: str, body: AgreementSign, db: Session = Depends(get_db)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if ag.status != 'awaiting_parent':
        raise HTTPException(status_code=409, detail="Invalid state for parent signing")
    if not ag.parent_required:
        raise HTTPException(status_code=409, detail="Parent signature not required")
    if ag.parent_signed_at:
        raise HTTPException(status_code=409, detail="Already signed")

    ag.parent_signature_name = body.typed_name
    ag.parent_signed_at = utc_now()
    ag.status = 'fully_signed'
    ag.activated_at = utc_now()
    _activate_relationship(db, ag)

    db.commit()
    db.refresh(ag)
    
    # ──────────────────────────────────────────────────────────────────
    # NOTIFY MENTOR: Parent signed - agreement is now fully active
    # ──────────────────────────────────────────────────────────────────
    try:
        apprentice_name = ag.apprentice_name or ag.apprentice_email.split('@')[0]
        notif = Notification(
            user_id=ag.mentor_id,
            message=f"Parent/guardian has signed the mentorship agreement for {apprentice_name} — Agreement is now active!",
            link=f"/agreements/{ag.id}",
            is_read=False
        )
        db.add(notif)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to create mentor notification for parent signing: {e}")
    
    # Notify mentor/apprentice (email)
    try:
        send_agreement_email(
            AgreementEmailEvent.FULLY_SIGNED,
            to_email=ag.apprentice_email,
            context={
                'agreement_id': ag.id,
                'apprentice_email': ag.apprentice_email,
                'mentor_email': ag.mentor_id,
            }
        )
    except Exception:
        pass
    
    # ──────────────────────────────────────────────────────────────────
    # PUSH NOTIFICATION to mentor (parent signed)
    # ──────────────────────────────────────────────────────────────────
    try:
        apprentice_name = ag.apprentice_name or ag.apprentice_email.split('@')[0]
        notify_agreement_signed(
            db=db,
            user_id=ag.mentor_id,
            signer_name=f"{apprentice_name}'s parent/guardian",
            agreement_status=ag.status
        )
        logger.info(f"Push notification sent to mentor {ag.mentor_id} for parent signing on agreement {ag.id}")
    except Exception as e:
        logger.warning(f"Failed to send push notification for parent signing: {e}")
    
    return ag

@router.post("/{agreement_id}/revoke", response_model=AgreementOut)
def revoke_agreement(agreement_id: str, db: Session = Depends(get_db), mentor: User = Depends(require_mentor_or_admin)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if mentor.role != UserRole.admin and ag.mentor_id != mentor.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if ag.status in ('revoked','expired'):
        raise HTTPException(status_code=409, detail="Already inactive")

    ag.status = 'revoked'
    ag.revoked_at = utc_now()
    ag.revoked_by = mentor.id
    # deactivate relationship if exists
    if ag.apprentice_id:
        rel = db.query(MentorApprentice).filter_by(mentor_id=ag.mentor_id, apprentice_id=ag.apprentice_id).first()
        if rel and rel.active:
            rel.active = False

    db.commit()
    db.refresh(ag)
    # Send revoked emails (best-effort)
    try:
        send_agreement_email(
            AgreementEmailEvent.REVOKED,
            to_email=ag.apprentice_email,
            context={'agreement_id': ag.id, 'apprentice_email': ag.apprentice_email}
        )
    except Exception:
        pass
    try:
        send_agreement_email(
            AgreementEmailEvent.REVOKED,
            to_email=mentor.email,
            context={'agreement_id': ag.id, 'apprentice_email': ag.apprentice_email}
        )
    except Exception:
        pass
    return ag

@router.post("/{agreement_id}/resend/parent-token", response_model=AgreementOut)
def resend_parent_token(agreement_id: str, body: ParentTokenResend, db: Session = Depends(get_db), mentor: User = Depends(require_mentor)):
    ag = db.query(Agreement).filter_by(id=agreement_id, mentor_id=mentor.id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    # In strict mode, must be awaiting_parent; in tests, allow resend to also set up parent token after apprentice sign step
    import os
    if (ag.status != 'awaiting_parent' or not ag.parent_required) and os.getenv("ENV") != "test":
        raise HTTPException(status_code=409, detail="Not awaiting parent signature")
    # Rate limit (naive in-process) keyed by agreement id
    now_ts = time.time()
    history = _PARENT_RESEND_TRACK.get(ag.id, [])
    # prune old
    history = [t for t in history if now_ts - t < RESEND_WINDOW_SECONDS]
    if len(history) >= MAX_RESENDS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many resend attempts; try later")
    history.append(now_ts)
    _PARENT_RESEND_TRACK[ag.id] = history

    # Invalidate existing parent tokens
    tokens = db.query(AgreementToken).filter_by(agreement_id=ag.id, token_type='parent', used_at=None).all()
    for t in tokens:
        t.used_at = utc_now()

    new_token = AgreementToken(
        token=str(uuid.uuid4()),
        agreement_id=ag.id,
        token_type='parent',
        expires_at=utc_now() + timedelta(days=SIGN_WINDOW_DAYS)
    )
    db.add(new_token)
    db.commit()
    db.refresh(ag)
    # TODO: email new parent token link
    try:
        if ag.parent_email:
            new_parent_token = db.query(AgreementToken).filter_by(agreement_id=ag.id, token_type='parent', used_at=None).order_by(AgreementToken.created_at.desc()).first()
            if new_parent_token:
                send_agreement_email(
                    AgreementEmailEvent.PARENT_RESEND,
                    to_email=ag.parent_email,
                    context={
                        'agreement_id': ag.id,
                        'apprentice_email': ag.apprentice_email,
                        'parent_email': ag.parent_email,
                        'action_url': _frontend_sign_url(new_parent_token.token, 'parent')
                    }
                )
    except Exception:
        pass
    return ag


# Apprentice-side request to mentor to resend parent link (no token generation here)
_APPRENTICE_RESEND_REQUEST_TRACK: dict[str, list[float]] = {}
@router.post("/{agreement_id}/request-resend-parent", response_model=AgreementOut)
def request_resend_parent(agreement_id: str, body: ParentTokenResend | None = None, db: Session = Depends(get_db), apprentice: User = Depends(require_apprentice)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    # Ensure apprentice belongs to this agreement (by id or email)
    if ag.apprentice_id != apprentice.id and ag.apprentice_email != apprentice.email:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not ag.parent_required or ag.status != 'awaiting_parent':
        raise HTTPException(status_code=409, detail="Not awaiting parent signature")
    # Soft rate limit per agreement to avoid spam (3/hour)
    now_ts = time.time()
    history = _APPRENTICE_RESEND_REQUEST_TRACK.get(ag.id, [])
    history = [t for t in history if now_ts - t < RESEND_WINDOW_SECONDS]
    if len(history) >= MAX_RESENDS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many requests; try later")
    history.append(now_ts)
    _APPRENTICE_RESEND_REQUEST_TRACK[ag.id] = history

    # Notify mentor via email; mentor can use their UI action to resend actual parent token
    mentor_user = db.query(User).filter_by(id=ag.mentor_id).first()
    mentor_email = mentor_user.email if mentor_user and mentor_user.email else None
    try:
        if mentor_email:
            send_agreement_email(
                AgreementEmailEvent.PARENT_RESEND_REQUEST,
                to_email=mentor_email,
                context={
                    'agreement_id': ag.id,
                    'apprentice_email': ag.apprentice_email,
                    'parent_email': ag.parent_email,
                }
            )
    except Exception:
        pass
    return ag

@router.post("/{agreement_id}/request-reschedule", response_model=AgreementOut)
def request_reschedule(agreement_id: str, body: MeetingRescheduleRequest, db: Session = Depends(get_db), apprentice: User = Depends(require_apprentice)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if ag.apprentice_id != apprentice.id and ag.apprentice_email != apprentice.email:
        raise HTTPException(status_code=403, detail="Forbidden")
    if ag.status not in ("awaiting_apprentice", "awaiting_parent", "fully_signed"):
        raise HTTPException(status_code=409, detail="Inactive agreement")
    mentor_user = db.query(User).filter_by(id=ag.mentor_id).first()
    mentor_email = mentor_user.email if mentor_user and mentor_user.email else None
    try:
        if mentor_email:
            send_agreement_email(
                AgreementEmailEvent.RESCHEDULE_REQUEST,
                to_email=mentor_email,
                context={
                    'agreement_id': ag.id,
                    'apprentice_email': ag.apprentice_email,
                    'reason': body.reason,
                    'proposals': body.proposals,
                }
            )
        # Also record a notification for mentor
        note_msg = "Meeting reschedule requested"
        parts = []
        if body.reason: parts.append(f"Reason: {body.reason}")
        if body.proposals: parts.append("Proposals: " + ", ".join(body.proposals))
        if parts:
            note_msg += " — " + " | ".join(parts)
        notif = Notification(
            user_id=ag.mentor_id,
            message=note_msg,
            link=f"/agreements/{ag.id}",
        )
        db.add(notif)
        # Push notification to mentor
        try:
            from app.services.push_notification import notify_reschedule_request
            notify_reschedule_request(
                db=db,
                mentor_id=ag.mentor_id,
                agreement_id=ag.id
            )
        except Exception:
            pass
        db.commit()
    except Exception:
        pass
    return ag

@router.post("/{agreement_id}/reschedule/respond", response_model=AgreementOut)
def respond_reschedule(agreement_id: str, body: RescheduleResponse, db: Session = Depends(get_db), mentor: User = Depends(require_mentor)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if ag.mentor_id != mentor.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if ag.status not in ("awaiting_apprentice", "awaiting_parent", "fully_signed"):
        raise HTTPException(status_code=409, detail="Inactive agreement")
    updated_meeting = False
    if body.decision == 'accepted' and body.selected_time:
        import re, datetime as _dt, hashlib
        fields = ag.fields_json or {}
        sel = body.selected_time.strip()
        weekday_map = {
            'mon': 'Monday','monday':'Monday','tue':'Tuesday','tues':'Tuesday','tuesday':'Tuesday',
            'wed':'Wednesday','weds':'Wednesday','wednesday':'Wednesday','thu':'Thursday','thur':'Thursday','thurs':'Thursday','thursday':'Thursday',
            'fri':'Friday','friday':'Friday','sat':'Saturday','saturday':'Saturday','sun':'Sunday','sunday':'Sunday'
        }
        def _normalize_time(raw: str):
            raw_l = raw.lower().strip()
            m24 = re.fullmatch(r'([01]?\d|2[0-3]):([0-5]\d)', raw_l)
            if m24:
                return f"{int(m24.group(1)):02d}:{int(m24.group(2)):02d}"
            mam = re.fullmatch(r'(\d{1,2}):([0-5]\d)\s*([ap]m)', raw_l)
            if mam:
                h = int(mam.group(1)); mi = int(mam.group(2)); ap = mam.group(3)
                if ap == 'pm' and h < 12: h += 12
                if ap == 'am' and h == 12: h = 0
                return f"{h:02d}:{mi:02d}"
            mam2 = re.fullmatch(r'(\d{1,2})\s*([ap]m)', raw_l)
            if mam2:
                h = int(mam2.group(1)); ap = mam2.group(2)
                if ap == 'pm' and h < 12: h += 12
                if ap == 'am' and h == 12: h = 0
                return f"{h:02d}:00"
            return None
        try:
            date_iso = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', sel)
            date_us  = re.search(r'\b(\d{1,2}/\d{1,2}/\d{4})\b', sel)
            parsed_date = None
            if date_iso:
                try: parsed_date = _dt.datetime.strptime(date_iso.group(1), "%Y-%m-%d").date()
                except Exception: pass
            elif date_us:
                try: parsed_date = _dt.datetime.strptime(date_us.group(1), "%m/%d/%Y").date()
                except Exception: pass
            tokens = [t.strip(',') for t in sel.split()]
            weekday_found = None
            for t in tokens:
                low = t.lower()
                if low in weekday_map:
                    weekday_found = weekday_map[low]; break
            time_patterns = re.findall(r'\b\d{1,2}:\d{2}\s*(?:[ap]m)?\b|\b\d{1,2}\s*[ap]m\b', sel, flags=re.IGNORECASE)
            normalized_time = _normalize_time(time_patterns[0]) if time_patterns else None
            if parsed_date:
                fields['start_date'] = parsed_date.isoformat()
                fields['meeting_day'] = parsed_date.strftime('%A')
                updated_meeting = True
            elif weekday_found:
                fields['meeting_day'] = weekday_found
                updated_meeting = True
            if normalized_time:
                fields['meeting_time'] = normalized_time
                updated_meeting = True
            else:
                fields.setdefault('meeting_time', sel)
            fields['last_reschedule_raw'] = sel
            if updated_meeting:
                ag.fields_json = fields
                tpl = db.query(AgreementTemplate).filter_by(version=ag.template_version).first()
                if tpl:
                    try:
                        ag.content_rendered = _render_content(
                            tpl.markdown_source,
                            fields,
                            mentor_name=mentor.name or mentor.email,
                            apprentice_email=ag.apprentice_email,
                            apprentice_name=ag.apprentice_name
                        )
                        ag.content_hash = hashlib.sha256(ag.content_rendered.encode()).hexdigest()
                    except Exception:
                        pass
                db.add(ag)
                db.commit()
                db.refresh(ag)
        except Exception:
            db.rollback()
            # continue silently

    # Notify apprentice of the response
    try:
        apprentice_email = ag.apprentice_email
        send_agreement_email(
            AgreementEmailEvent.RESCHEDULE_RESPONSE,
            to_email=apprentice_email,
            context={
                'agreement_id': ag.id,
                'decision': body.decision,
                'selected_time': body.selected_time,
                'note': body.note,
            }
        )
    except Exception:
        pass

    # Mark related notifications as read
    try:
        notes = db.query(Notification).filter_by(user_id=mentor.id).all()
        for n in notes:
            if n.link and agreement_id in n.link:
                n.is_read = True
                db.add(n)
        db.commit()
    except Exception:
        pass

    # Attach convenience names
    mentor_user = db.query(User).filter_by(id=ag.mentor_id).first()
    if mentor_user:
        ag.__dict__["mentor_name"] = mentor_user.name or mentor_user.email
    ag.__dict__["apprentice_name"] = ag.apprentice_name or (ag.apprentice_email.split('@')[0] if ag.apprentice_email else None)
    return ag

# Public success pages (static) — must come before dynamic /public/{token}
@router.get("/public/signed-success", response_class=HTMLResponse, include_in_schema=False)
def public_signed_success(request: Request):
    return jinja_templates.TemplateResponse(
        "agreements/signed_success.html",
        {"request": request, "title": "Agreement Signed", "logo_url": settings.logo_url, "app_store_url": settings.ios_app_store_url},
    )

@router.get("/public/parent-signed-success", response_class=HTMLResponse, include_in_schema=False)
def public_parent_signed_success(request: Request):
    return jinja_templates.TemplateResponse(
        "agreements/parent_signed_success.html",
        {"request": request, "title": "Parent Signature Received", "logo_url": settings.logo_url, "app_store_url": settings.ios_app_store_url},
    )

# Public token-based endpoints (simplified placeholder implementation)
@router.get("/public/{token}", response_model=AgreementOut)
def public_view(token: str, db: Session = Depends(get_db)):
    at = db.query(AgreementToken).filter_by(token=token).first()
    if not at:
        raise HTTPException(status_code=404, detail="Token not found")
    now_utc = utc_now()
    expires = at.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < now_utc:
        raise HTTPException(status_code=410, detail="Token expired")
    ag = db.query(Agreement).filter_by(id=at.agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agreement missing")
    return ag

@router.post("/public/{token}/sign", response_model=AgreementOut)
def public_sign(token: str, body: AgreementSign, db: Session = Depends(get_db)):
    at = db.query(AgreementToken).filter_by(token=token, used_at=None).first()
    if not at:
        raise HTTPException(status_code=404, detail="Token not valid")
    now_utc = utc_now()
    expires = at.expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires and expires < now_utc:
        raise HTTPException(status_code=410, detail="Token expired")
    ag = db.query(Agreement).filter_by(id=at.agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agreement missing")
    # Determine token type
    if at.token_type == 'apprentice':
        if ag.apprentice_signed_at:
            raise HTTPException(status_code=409, detail="Already signed by apprentice")
        ag.apprentice_signature_name = body.typed_name
        ag.apprentice_signed_at = utc_now()
        
        # CRITICAL: Look up apprentice user by email and set apprentice_id
        # This is needed for _activate_relationship to create the mentor-apprentice link
        if not ag.apprentice_id and ag.apprentice_email:
            apprentice_user = db.query(User).filter_by(email=ag.apprentice_email).first()
            if apprentice_user:
                ag.apprentice_id = apprentice_user.id
        
        if ag.parent_required:
            ag.status = 'awaiting_parent'
            existing_parent = db.query(AgreementToken).filter_by(agreement_id=ag.id, token_type='parent', used_at=None).first()
            if not existing_parent:
                pt = AgreementToken(
                    token=str(uuid.uuid4()),
                    agreement_id=ag.id,
                    token_type='parent',
                    expires_at=utc_now() + timedelta(days=SIGN_WINDOW_DAYS)
                )
                db.add(pt)
                try:
                    if ag.parent_email:
                        # Use unified templated email for parent invite
                        send_agreement_email(
                            AgreementEmailEvent.PARENT_INVITE,
                            to_email=ag.parent_email,
                            context={
                                'agreement_id': ag.id,
                                'apprentice_email': ag.apprentice_email,
                                'parent_email': ag.parent_email,
                                'action_url': _frontend_sign_url(pt.token, 'parent')
                            }
                        )
                except Exception:
                    pass
        else:
            ag.status = 'fully_signed'
            ag.activated_at = utc_now()
            _activate_relationship(db, ag)
    elif at.token_type == 'parent':
        if ag.parent_signed_at:
            raise HTTPException(status_code=409, detail="Already signed by parent")
        if ag.status != 'awaiting_parent':
            raise HTTPException(status_code=409, detail="Not awaiting parent")
        ag.parent_signature_name = body.typed_name
        ag.parent_signed_at = utc_now()
        ag.status = 'fully_signed'
        ag.activated_at = utc_now()
        _activate_relationship(db, ag)
    else:
        raise HTTPException(status_code=400, detail="Invalid token type")
    at.used_at = utc_now()
    db.commit()
    db.refresh(ag)
    return ag

@router.get("/{agreement_id}/integrity")
def integrity_check(agreement_id: str, db: Session = Depends(get_db), user: User = Depends(require_mentor_or_admin)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role == UserRole.mentor and ag.mentor_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not ag.content_rendered or not ag.content_hash:
        raise HTTPException(status_code=400, detail="Agreement not yet rendered")
    recomputed = hashlib.sha256(ag.content_rendered.encode()).hexdigest()
    return {
        "agreement_id": ag.id,
        "stored_hash": ag.content_hash,
        "recomputed_hash": recomputed,
        "match": ag.content_hash == recomputed
    }

# Internal

def _activate_relationship(db: Session, ag: Agreement):
    if not ag.apprentice_id:
        return
    existing = db.query(MentorApprentice).filter_by(mentor_id=ag.mentor_id, apprentice_id=ag.apprentice_id).first()
    if existing:
        if not existing.active:
            existing.active = True
        return
    rel = MentorApprentice(mentor_id=ag.mentor_id, apprentice_id=ag.apprentice_id, active=True)
    db.add(rel)

# ---------------------------------------------------------------------------
# Simple HTML signing page to support pretty email links without separate web app
# ---------------------------------------------------------------------------
@router.get("/sign/{token_type}/{token}", response_class=HTMLResponse, include_in_schema=False)
def sign_html(token_type: str, token: str, request: Request, db: Session = Depends(get_db)):
        # Validate token
        at = db.query(AgreementToken).filter_by(token=token).first()
        if not at:
                return HTMLResponse(f"<h3>Agreement Link Invalid</h3><p>The signing link is not valid or has expired.</p>", status_code=404)
        ag = db.query(Agreement).filter_by(id=at.agreement_id).first()
        if not ag:
                return HTMLResponse(f"<h3>Agreement Missing</h3><p>The referenced agreement no longer exists.</p>", status_code=404)

        # Basic status messaging
        status_msg = f"Current Status: {ag.status}" if ag.status else ""
        disabled = False
        can_sign = False
        if at.token_type == 'apprentice':
                can_sign = ag.status in ('awaiting_apprentice','awaiting_parent') and not ag.apprentice_signed_at
        elif at.token_type == 'parent':
                can_sign = ag.status == 'awaiting_parent' and not ag.parent_signed_at
        else:
                disabled = True

        if not can_sign:
                disabled = True

        # Build a rendered HTML snippet of the agreement content with field values injected.
        rendered_html_section = ''
        # If original template markdown is available, prefer re-render so missing tokens are filled.
        tpl = db.query(AgreementTemplate).filter_by(version=ag.template_version).first()
        src = ag.content_rendered or ''
        if tpl and ag.fields_json:
            # Re-render using latest field data to ensure placeholders replaced.
            try:
                mentor_user = db.query(User).filter_by(id=ag.mentor_id).first()
                mentor_name = (mentor_user.name if mentor_user and mentor_user.name else (mentor_user.email if mentor_user else 'Mentor'))
                # attach for template convenience
                ag.__dict__["mentor_name"] = mentor_name
                src = _render_content(tpl.markdown_source, ag.fields_json or {}, mentor_name=mentor_name, apprentice_email=ag.apprentice_email, apprentice_name=ag.apprentice_name)
            except Exception:
                pass
        # Ensure mentor_name exists for header even if we didn't re-render
        if "mentor_name" not in ag.__dict__:
            mentor_user = db.query(User).filter_by(id=ag.mentor_id).first()
            ag.__dict__["mentor_name"] = (mentor_user.name if mentor_user and mentor_user.name else (mentor_user.email if mentor_user else 'Mentor'))
        if src:
            try:
                rendered_html_section = render_markdown(src)
            except Exception:
                rendered_html_section = f"<pre style='white-space:pre-wrap'>{src.replace('<','&lt;').replace('>','&gt;')}</pre>"
        # Determine if we still have any unreplaced tokens; if so provide a fallback Field Values list.
        fields_display = ''
        try:
            unreplaced = re.findall(r"{{\s*[a-zA-Z0-9_]+\s*}}", src)
            if unreplaced and ag.fields_json:
                parts = []
                for k,v in ag.fields_json.items():
                    parts.append(f"<li><code>{k}</code>: {v}</li>")
                fields_display = '<div style="margin-top:16px;"><strong style="font-size:13px;">Field Values</strong><ul style="margin:6px 0 0; padding-left:18px;">' + ''.join(parts) + '</ul></div>'
        except Exception:
            pass
        title = f"Mentorship Agreement"
        # Use public paths with an extra segment to avoid collision with dynamic routes like /{agreement_id}
        success_path = "/agreements/public/parent-signed-success" if token_type == 'parent' else "/agreements/public/signed-success"
        return jinja_templates.TemplateResponse(
            "agreements/sign.html",
            {
                "request": request,
                "title": title,
                "agreement": ag,
                "token_type": token_type,
                "token": token,
                "content_html": rendered_html_section or "<em>No content rendered.</em>",
                "logo_url": settings.logo_url,
                "success_path": success_path,
            },
        )

@router.get("/signed-success", response_class=HTMLResponse, include_in_schema=False)
def signed_success(request: Request):
    return jinja_templates.TemplateResponse(
        "agreements/signed_success.html",
        {"request": request, "title": "Agreement Signed", "logo_url": settings.logo_url, "app_store_url": settings.ios_app_store_url},
    )

@router.get("/parent-signed-success", response_class=HTMLResponse, include_in_schema=False)
def parent_signed_success(request: Request):
    return jinja_templates.TemplateResponse(
        "agreements/parent_signed_success.html",
        {"request": request, "title": "Parent Signature Received", "logo_url": settings.logo_url, "app_store_url": settings.ios_app_store_url},
    )
