"""Audit logging helper functions for key domain events.

Standard JSON-ish single-line logs so they are easy to index.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional, Any

_logger = logging.getLogger("app.audit")


def _emit(event: str, user_id: Optional[str] = None, **data: Any):
    payload = {"ts": datetime.utcnow().isoformat() + "Z", "event": event}
    if user_id:
        payload["user_id"] = user_id
    payload.update(data)
    # Single-line stable ordering (rough) for readability
    # Not using json.dumps to avoid imposing strict serialization on arbitrary values; could switch later.
    parts = [f"{k}={repr(v)}" for k,v in payload.items()]
    _logger.info("AUDIT " + " ".join(parts))

# Public convenience wrappers

def log_assessment_submit(user_id: str, assessment_id: str, category: str, template_id: Optional[str], template_version: Optional[int]):
    _emit("assessment.submit", user_id=user_id, assessment_id=assessment_id, category=category, template_id=template_id, template_version=template_version)

def log_assessment_view(user_id: str, assessment_id: str, category: str, actor_role: str, viewed_user_id: str):
    _emit("assessment.view", user_id=user_id, assessment_id=assessment_id, category=category, actor_role=actor_role, target_user_id=viewed_user_id)

def log_template_publish(user_id: str, template_id: str, template_name: str, version: int):
    _emit("template.publish", user_id=user_id, template_id=template_id, template_name=template_name, version=version)

def log_email_send(user_id: str, assessment_id: str | None, category: str | None, template_version: int | None,
                   target_user_id: str | None, purpose: str, actor_role: str, sent: bool):
    _emit(
        "email.send",
        user_id=user_id,
        assessment_id=assessment_id,
        category=category,
        template_version=template_version,
        target_user_id=target_user_id,
        purpose=purpose,
        actor_role=actor_role,
        sent=sent,
    )
