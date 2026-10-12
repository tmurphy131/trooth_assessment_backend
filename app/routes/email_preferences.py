"""Public email-preference pages (specs/005-email-redesign, contracts/email-preferences.md).

These routes are explicitly public (Principle I): they are authorized only by the HMAC-signed
token in the link, which identifies exactly one user. Opening the confirm page has no side
effects, so link scanners can't unsubscribe anyone; the form POST or the mail app's RFC 8058
one-click POST does.
"""
import logging
from datetime import UTC, datetime
from typing import Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db import get_db
from app.models.user import User
from app.services import email_links

logger = logging.getLogger(__name__)
router = APIRouter()
_pages = Jinja2Templates(directory="app/templates")


def _page(request: Request, name: str, status_code: int = 200, token: str = "") -> HTMLResponse:
    return _pages.TemplateResponse(request, f"pages/email_preferences/{name}.html",
                                   {"token": token, "support_email": settings.support_email},
                                   status_code=status_code)


def _user_for(db: Session, token: Optional[str]) -> Optional[User]:
    user_id = email_links.verify_token(token)
    return db.query(User).filter_by(id=user_id).first() if user_id else None


async def _form_token(request: Request) -> Optional[str]:
    body = (await request.body()).decode("utf-8", "replace")
    return (parse_qs(body).get("t") or [None])[0]


def _set_pref(db: Session, user: User, opt_out: bool, source: str) -> None:
    if user.email_opt_out != opt_out or user.email_pref_source != source:
        user.email_opt_out = opt_out
        user.email_pref_source = source
        user.email_pref_changed_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
    logger.info("email_pref_changed user=%s opt_out=%s source=%s", user.id, opt_out, source)


@router.get("/email/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
def unsubscribe_page(request: Request, t: Optional[str] = None, db: Session = Depends(get_db)):
    user = _user_for(db, t)
    if not user:
        return _page(request, "invalid", 400)
    return _page(request, "already" if user.email_opt_out else "confirm", token=t)


@router.post("/email/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
async def unsubscribe(request: Request, db: Session = Depends(get_db)):
    token = await _form_token(request)
    user = _user_for(db, token)
    if not user:
        return _page(request, "invalid", 400)
    if not user.email_opt_out:
        _set_pref(db, user, True, "link")
    return _page(request, "done", token=token)


@router.post("/email/unsubscribe/one-click", include_in_schema=False)
def unsubscribe_one_click(t: Optional[str] = None, db: Session = Depends(get_db)):
    """RFC 8058: the mail app POSTs `List-Unsubscribe=One-Click`; reply 200 with no body."""
    user = _user_for(db, t)
    if not user:
        return Response(status_code=400)
    if not user.email_opt_out:
        _set_pref(db, user, True, "one_click")
    return Response(status_code=200)


@router.post("/email/resubscribe", response_class=HTMLResponse, include_in_schema=False)
async def resubscribe(request: Request, db: Session = Depends(get_db)):
    token = await _form_token(request)
    user = _user_for(db, token)
    if not user:
        return _page(request, "invalid", 400)
    if user.email_opt_out:
        _set_pref(db, user, False, "resubscribe")
    return _page(request, "resubscribed")


@router.get("/settings/notifications", response_class=HTMLResponse, include_in_schema=False)
def legacy_notifications_page(request: Request):
    """Old emails linked here (it used to 404); explain how to unsubscribe instead."""
    return _page(request, "legacy")
