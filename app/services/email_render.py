"""One render path for every email (specs/005-email-redesign).

Renders a Jinja template on the shared layout, inlines its CSS (so Gmail and Outlook keep the
design) and derives the plain-text part from the same HTML. Engagement emails also get the
unsubscribe link and List-Unsubscribe headers.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import css_inline
import html2text

from app.core.settings import settings

logger = logging.getLogger(__name__)

SIZE_WARN_BYTES = 95_000  # Gmail clips messages over ~102 KB
_PREHEADER_RE = re.compile(r'<div style="display:none;font-size:1px[^>]*>.*?</div>', re.S)
_inliner = css_inline.CSSInliner(keep_style_tags=True)


@dataclass
class RenderedEmail:
    html: str
    text: str
    preheader: str
    size_bytes: int
    headers: dict = field(default_factory=dict)


def html_to_text(html: str) -> str:
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = True
    converter.ignore_emphasis = False
    converter.ignore_tables = True
    text = converter.handle(_PREHEADER_RE.sub("", html, count=1))
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>])", r"\1", text)  # html2text escapes Markdown; plain text shouldn't
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def render_email(template: str, context: Optional[dict[str, Any]] = None, *, preheader: str = "",
                 reason: str = "", category: str = "transactional",
                 user_id: Optional[str] = None) -> RenderedEmail:
    """Render ``template`` (path under app/templates/email/) with the shared defaults.

    ``category == "engagement"`` with a ``user_id`` adds the unsubscribe link and headers.
    """
    from app.services import email_links
    from app.services.email import get_email_template_env

    env = get_email_template_env()
    ctx: dict[str, Any] = {
        "logo_url": settings.logo_url,
        "email_logo_url": settings.email_logo_url,
        "app_url": settings.app_landing_url,
        "ios_app_store_url": settings.ios_app_store_url,
        "android_play_store_url": settings.android_play_store_url,
        "support_email": settings.support_email,
        "year": datetime.now().year,
        "preheader": preheader,
        "reason": reason,
        "unsubscribe_url": None,
    }
    ctx.update(context or {})
    headers: dict = {}
    if category == "engagement" and user_id:
        urls = email_links.unsubscribe_urls(user_id)
        if urls:
            ctx["unsubscribe_url"] = urls[0]
            headers = email_links.list_unsubscribe_headers(user_id)
        else:
            logger.error("email_link_secret_missing template=%s: sending without an unsubscribe link", template)

    html = _inliner.inline(env.get_template(template).render(**ctx))
    size = len(html.encode("utf-8"))
    if size > SIZE_WARN_BYTES:
        logger.warning("email_too_large template=%s bytes=%s (Gmail clips over ~102 KB)", template, size)
    return RenderedEmail(html=html, text=html_to_text(html), preheader=ctx["preheader"], size_bytes=size,
                         headers=headers)
