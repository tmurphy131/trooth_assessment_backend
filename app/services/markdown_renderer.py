from __future__ import annotations

from typing import Iterable
import bleach
from markdown import Markdown

_ALLOWED_TAGS: set[str] = {
    "p", "pre", "code", "blockquote", "strong", "em", "u", "del", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "a", "span", "br"
}
_ALLOWED_ATTRS: dict[str, Iterable[str]] = {
    "a": ["href", "title", "name", "id", "target", "rel"],
    "span": ["class"],
    "code": ["class"],
    "pre": ["class"],
    "h1": ["id"], "h2": ["id"], "h3": ["id"], "h4": ["id"], "h5": ["id"], "h6": ["id"],
}


def render_markdown(md: str) -> str:
    """Render Markdown -> sanitized HTML with useful extensions."""
    md_engine = Markdown(
        extensions=[
            "extra",
            "sane_lists",
            "smarty",
            # Remove 'toc' to avoid header permalinks adding pilcrow symbol
            "nl2br",
        ],
        output_format="html5",
    )
    html = md_engine.convert(md or "")
    clean = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        strip=True,
    )
    clean = bleach.linkify(clean, callbacks=[], skip_tags=None, parse_email=False)
    return clean
