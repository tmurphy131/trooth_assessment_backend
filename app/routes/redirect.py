"""Deep-link redirect endpoints.

These pages are linked from emails. They attempt to open the native app via
the custom URL scheme (trooth://) and fall back to the relevant app store if
the app isn't installed.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from app.core.settings import settings

router = APIRouter()

_ANDROID_STORE_URL = "https://play.google.com/store/apps/details?id=com.trooth.flutterTroothAssessment"

def _render(template_name: str, context: dict) -> str:
    template_dir = os.path.join(os.path.dirname(__file__), "../templates/redirect")
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template(template_name).render(**context)


@router.get("/draft/{draft_id}", response_class=HTMLResponse)
def redirect_to_draft(draft_id: str):
    """Redirect page linked from draft reminder emails.

    Tries trooth://assessment/draft/{draft_id} first.
    Falls back to the appropriate app store if the app isn't installed.
    """
    deep_link = f"trooth://assessment/draft/{draft_id}"
    html = _render("draft.html", {
        "deep_link": deep_link,
        "ios_url": settings.ios_app_store_url,
        "android_url": _ANDROID_STORE_URL,
    })
    return HTMLResponse(content=html)
