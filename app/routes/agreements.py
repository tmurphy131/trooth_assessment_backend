from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC
import re
from app.utils.datetime import utc_now
import hashlib

from app.db import get_db
from app.schemas.agreement import (
    AgreementCreate, AgreementOut, AgreementSubmit, AgreementSign,
    AgreementTemplateCreate, AgreementTemplateOut, ParentTokenResend,
    AgreementFieldsUpdate,
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
    """Return the pretty frontend sign URL (handled by Flutter deep link).

    Frontend screen: /agreements/sign/<type>/<token>
    API calls still use /agreements/public/<token> endpoints under the hood.
    """
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

    # Pre-render draft so mentor can preview before submit
    fields_dict = payload.fields.model_dump()
    # Include parent_email for token substitution if provided
    if payload.parent_email:
        fields_dict['parent_email'] = payload.parent_email
    rendered = _render_content(
        tpl.markdown_source,
        fields_dict,
        mentor_name=mentor.name or mentor.email,
        apprentice_email=payload.apprentice_email,
    apprentice_name=payload.apprentice_name,
    )
    agreement = Agreement(
        template_version=tpl.version,
        mentor_id=mentor.id,
        apprentice_email=payload.apprentice_email,
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

# ---------------------------------------------------------------------------
# Simple HTML signing page to support pretty email links without separate web app
# ---------------------------------------------------------------------------
@router.get("/sign/{token_type}/{token}", response_class=HTMLResponse, include_in_schema=False)
def sign_html(token_type: str, token: str, db: Session = Depends(get_db)):
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
                src = _render_content(tpl.markdown_source, ag.fields_json or {}, mentor_name=mentor_name, apprentice_email=ag.apprentice_email, apprentice_name=ag.apprentice_name)
            except Exception:
                pass
        if src:
            try:
                import markdown  # type: ignore
                rendered_html_section = markdown.markdown(src)
            except Exception:
                # Very small naive markdown replacements (headers + bold/italics + line breaks)
                import html
                esc = html.escape(src)
                # headers
                esc = re.sub(r'^### (.*)$', r'<h3>\1</h3>', esc, flags=re.MULTILINE)
                esc = re.sub(r'^## (.*)$', r'<h2>\1</h2>', esc, flags=re.MULTILINE)
                esc = re.sub(r'^# (.*)$', r'<h1>\1</h1>', esc, flags=re.MULTILINE)
                # bold / italic
                esc = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', esc)
                esc = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', esc)
                esc = esc.replace('\n\n', '<br><br>')
                rendered_html_section = f"<div>{esc}</div>"
        if not rendered_html_section and ag.content_rendered:
            esc = ag.content_rendered.replace('<','&lt;').replace('>','&gt;')
            rendered_html_section = f"<pre style='white-space:pre-wrap'>{esc}</pre>"
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
        html = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <title>Mentorship Agreement Sign</title>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background:#101317; color:#eee; margin:0; padding:20px; }}
        h1 {{ font-size:20px; margin:0 0 12px; }}
        .card {{ background:#1c2128; border:1px solid #2a313a; border-radius:8px; padding:20px; max-width:640px; box-shadow:0 2px 4px rgba(0,0,0,.4); }}
        label {{ display:block; font-size:14px; margin-bottom:6px; }}
        input[type=text] {{ width:100%; padding:10px 12px; border-radius:6px; border:1px solid #39424d; background:#0f1419; color:#eee; font-size:15px; }}
        button {{ background:#f6c344; color:#000; border:none; padding:12px 20px; border-radius:6px; font-weight:600; cursor:pointer; font-size:15px; }}
        button[disabled] {{ opacity:.5; cursor:not-allowed; }}
        .status {{ font-size:13px; color:#aaa; margin:8px 0 16px; }}
        .msg {{ margin-top:16px; font-size:14px; }}
        .error {{ color:#ff6b6b; }}
                pre {{ white-space:pre-wrap; background:#0f1419; padding:12px; border-radius:6px; font-size:13px; line-height:1.35; }}
                .agreement-html h1,.agreement-html h2,.agreement-html h3 {{ color:#f6c344; }}
                .agreement-html p, .agreement-html li {{ line-height:1.4; }}
    </style>
</head>
<body>
    <div class='card'>
        <h1>Mentorship Agreement</h1>
        <div class='status'>{status_msg}</div>
        <p>Agreement ID: {ag.id}</p>
        <p>Apprentice Email: {ag.apprentice_email}</p>
        {f'<p>Parent Email: {ag.parent_email}</p>' if ag.parent_email else ''}
        {'<p><em>This agreement is no longer signable with this link.</em></p>' if disabled else ''}
                <details open>
                    <summary style="cursor:pointer;margin:8px 0 12px;">Agreement Preview</summary>
                    <div class='agreement-html' style='margin-top:8px;'>{rendered_html_section or '<em>No content rendered.</em>'}{fields_display}</div>
                </details>
        <form id='signForm' onsubmit='return false;' style='margin-top:12px;'>
            <label>Type Full Name to Sign</label>
            <input id='typedName' type='text' placeholder='Full Name' {'disabled' if disabled else ''} />
            <div style='margin-top:12px;'>
                <button id='signBtn' {'disabled' if disabled else ''}>{'Cannot Sign' if disabled else 'Sign Agreement'}</button>
            </div>
            <div class='msg' id='msg'></div>
        </form>
    </div>
    <script>
        const btn = document.getElementById('signBtn');
        const input = document.getElementById('typedName');
        const msg = document.getElementById('msg');
        const form = document.getElementById('signForm');
        form?.addEventListener('submit', async () => {{
            if (btn.disabled) return;
            const name = input.value.trim();
            if (!name) {{ msg.textContent = 'Name required'; msg.className='msg error'; return; }}
            btn.disabled = true; msg.textContent = 'Signing...'; msg.className='msg';
            try {{
                const res = await fetch('/agreements/public/{token}/sign', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ typed_name: name }})
                }});
                const data = await res.json();
                if (res.ok) {{
                    msg.textContent = 'Signed successfully. Status: ' + data.status;
                    msg.className='msg';
                    btn.disabled = true;
                }} else {{
                    msg.textContent = 'Failed: ' + (data.detail || res.status);
                    msg.className='msg error';
                    btn.disabled = false;
                }}
            }} catch (e) {{
                msg.textContent = 'Network error: ' + e;
                msg.className='msg error';
                btn.disabled = false;
            }}
        }});
    </script>
</body>
</html>
"""
        return HTMLResponse(html)
