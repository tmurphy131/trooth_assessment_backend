from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC
from app.utils.datetime import utc_now
import hashlib

from app.db import get_db
from app.schemas.agreement import (
    AgreementCreate, AgreementOut, AgreementSubmit, AgreementSign,
    AgreementTemplateCreate, AgreementTemplateOut, ParentTokenResend
)
from app.models.agreement import Agreement, AgreementTemplate, AgreementToken
from app.models.user import User, UserRole
from app.models.mentor_apprentice import MentorApprentice
from app.services.email import send_notification_email  # legacy fallback
from app.services.agreement_notifications import (
    send_agreement_email,
    AgreementEmailEvent,
)
import time

# Simple in-memory (process local) rate limit store for resend attempts
_PARENT_RESEND_TRACK: dict[str, list[float]] = {}
MAX_RESENDS_PER_HOUR = 3
RESEND_WINDOW_SECONDS = 3600
from app.core.settings import settings
from app.services.auth import get_current_user, require_mentor, require_mentor_or_admin, require_admin

router = APIRouter(prefix="/agreements", tags=["Agreements"])

SIGN_WINDOW_DAYS = 7
VALID_STATUSES = {"draft","awaiting_apprentice","awaiting_parent","fully_signed","revoked","expired"}

# Utility

def _render_content(template_md: str, fields: dict, mentor_name: str, apprentice_email: str) -> str:
    content = template_md
    tokens = {**fields, "mentor_name": mentor_name, "apprentice_name": apprentice_email.split('@')[0]}
    for k, v in tokens.items():
        content = content.replace(f"{{{{{k}}}}}", str(v) if v is not None else "")
    return content

def _frontend_sign_url(token: str, token_type: str) -> str:
    base = settings.app_url.rstrip('/') if settings.app_url else 'http://localhost:3000'
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

# Agreement Creation
@router.post("", response_model=AgreementOut)
def create_agreement(payload: AgreementCreate, db: Session = Depends(get_db), mentor: User = Depends(require_mentor)):
    tpl = db.query(AgreementTemplate).filter_by(version=payload.template_version).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template version not found")
    if not tpl.is_active:
        raise HTTPException(status_code=400, detail="Template version inactive")

    agreement = Agreement(
        template_version=tpl.version,
        mentor_id=mentor.id,
        apprentice_email=payload.apprentice_email,
        status='draft',
        apprentice_is_minor=payload.apprentice_is_minor,
        parent_required=payload.parent_required,
        parent_email=payload.parent_email,
    fields_json=payload.fields.model_dump(),
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)
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

    ag.content_rendered = _render_content(tpl.markdown_source, fields, mentor_name=mentor.name or mentor.email, apprentice_email=ag.apprentice_email)
    ag.content_hash = hashlib.sha256(ag.content_rendered.encode()).hexdigest()
    ag.status = 'awaiting_apprentice'

    # Create apprentice token
    apprentice_token = AgreementToken(
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
    return ag

# Signing
@router.post("/{agreement_id}/sign/apprentice", response_model=AgreementOut)
def apprentice_sign(agreement_id: str, body: AgreementSign, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ag = db.query(Agreement).filter_by(id=agreement_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if ag.status not in ('awaiting_apprentice','awaiting_parent'):
        raise HTTPException(status_code=409, detail="Invalid state for signing")
    # Ensure user matches
    if user.email != ag.apprentice_email:
        raise HTTPException(status_code=403, detail="Not authorized to sign")
    if ag.apprentice_signed_at:
        raise HTTPException(status_code=409, detail="Already signed")

    ag.apprentice_signature_name = body.typed_name
    ag.apprentice_signed_at = utc_now()
    ag.apprentice_id = user.id

    # Determine next state
    if ag.parent_required:
        if ag.status == 'awaiting_apprentice':
            ag.status = 'awaiting_parent'
            # generate parent token if not exists
            existing_parent = db.query(AgreementToken).filter_by(agreement_id=ag.id, token_type='parent', used_at=None).first()
            if not existing_parent:
                parent_token = AgreementToken(
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
        ag.status = 'fully_signed'
    ag.activated_at = utc_now()
    _activate_relationship(db, ag)

    db.commit()
    db.refresh(ag)
    # Notify mentor if fully signed
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
    # Notify mentor/apprentice
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
    if ag.status != 'awaiting_parent' or not ag.parent_required:
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
        if ag.parent_required:
            ag.status = 'awaiting_parent'
            existing_parent = db.query(AgreementToken).filter_by(agreement_id=ag.id, token_type='parent', used_at=None).first()
            if not existing_parent:
                pt = AgreementToken(
                    agreement_id=ag.id,
                    token_type='parent',
                    expires_at=utc_now() + timedelta(days=SIGN_WINDOW_DAYS)
                )
                db.add(pt)
                try:
                    if ag.parent_email:
                        send_notification_email(
                            to_email=ag.parent_email,
                            subject="Mentorship Agreement Parent Signature Needed",
                            message="Please review and sign the mentorship agreement.",
                            action_url=_frontend_sign_url(pt.token, 'parent')
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
