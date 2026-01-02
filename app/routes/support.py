"""
Support request endpoint for website and mobile app.
Handles spam prevention via honeypot (web) and rate limiting.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.auth import get_current_user_optional
from app.models.user import User
from app.core.settings import settings

logger = logging.getLogger("app.support")

router = APIRouter(prefix="/support", tags=["Support"])

# In-memory rate limiting (simple approach - resets on server restart)
# For production at scale, consider Redis
_rate_limit_store: dict[str, list[datetime]] = {}
RATE_LIMIT_WINDOW = timedelta(hours=1)
RATE_LIMIT_MAX_REQUESTS = 3  # Max 3 requests per hour per IP/user


class SupportRequest(BaseModel):
    name: str
    email: EmailStr
    topic: str  # Account Issues, Assessment Problems, Technical Bug, Feature Request, Other
    message: str
    # Honeypot field - should always be empty from real users
    website: Optional[str] = None  # Hidden field, bots will fill this
    # Optional fields for app submissions
    device_info: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "website"  # "website" or "app"


def _check_rate_limit(identifier: str) -> bool:
    """Check if identifier (IP or user_id) has exceeded rate limit.
    Returns True if allowed, False if rate limited.
    """
    now = datetime.now(timezone.utc)
    
    if identifier not in _rate_limit_store:
        _rate_limit_store[identifier] = []
    
    # Clean old entries
    _rate_limit_store[identifier] = [
        ts for ts in _rate_limit_store[identifier]
        if now - ts < RATE_LIMIT_WINDOW
    ]
    
    # Check limit
    if len(_rate_limit_store[identifier]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    # Record this request
    _rate_limit_store[identifier].append(now)
    return True


def _send_support_emails(data: SupportRequest, submitted_at: str):
    """Send admin notification and user confirmation emails."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        logger.warning("SendGrid API key not configured, skipping support emails")
        return False
    
    # Set up Jinja2
    template_dir = os.path.join(os.path.dirname(__file__), '../templates/email')
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Add strftime filter
    def strftime_filter(value, format='%Y'):
        if isinstance(value, str) and value == 'now':
            return datetime.now().strftime(format)
        return value
    env.filters['strftime'] = strftime_filter
    
    from_email = os.getenv("EMAIL_FROM_ADDRESS", "admin@onlyblv.com")
    admin_emails = ["admin@onlyblv.com", "tay.murphy88@gmail.com"]
    
    try:
        sg = SendGridAPIClient(api_key)
        
        # 1. Send admin notification to all admin emails
        admin_template = env.get_template('support_request_admin.html')
        admin_html = admin_template.render(
            name=data.name,
            email=data.email,
            topic=data.topic,
            message=data.message,
            user_id=data.user_id,
            device_info=data.device_info,
            source=data.source,
            submitted_at=submitted_at
        )
        
        for admin_email in admin_emails:
            admin_mail = Mail(
                from_email=from_email,
                to_emails=admin_email,
                subject=f"[Support] {data.topic} - {data.name}",
                html_content=admin_html
            )
            # Set reply-to as the user's email for easy response
            admin_mail.reply_to = data.email
            
            sg.send(admin_mail)
        logger.info(f"Support request admin notification sent to {len(admin_emails)} recipients for {data.email}")
        
        # 2. Send user confirmation
        user_template = env.get_template('support_request_confirmation.html')
        user_html = user_template.render(
            name=data.name,
            topic=data.topic,
            message=data.message
        )
        
        user_mail = Mail(
            from_email=from_email,
            to_emails=data.email,
            subject="We Received Your Support Request - T[root]H",
            html_content=user_html
        )
        
        sg.send(user_mail)
        logger.info(f"Support request confirmation sent to {data.email}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send support emails: {e}")
        return False


@router.post("/submit")
async def submit_support_request(
    data: SupportRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Submit a support request.
    
    For website: Uses honeypot field for spam detection + IP rate limiting.
    For app: Uses user authentication + user_id rate limiting.
    """
    
    # 1. Honeypot check (for website submissions)
    if data.website:
        # Honeypot field was filled - likely a bot
        logger.warning(f"Honeypot triggered from IP {request.client.host}")
        # Return success to not tip off the bot, but don't process
        return {"success": True, "message": "Support request submitted successfully"}
    
    # 2. Rate limiting
    if current_user:
        # For authenticated users, rate limit by user_id
        identifier = f"user:{current_user.id}"
        data.user_id = current_user.id
        # Pre-fill email if not provided differently
        if not data.email or data.email != current_user.email:
            data.email = current_user.email
    else:
        # For anonymous users, rate limit by IP
        identifier = f"ip:{request.client.host}"
    
    if not _check_rate_limit(identifier):
        raise HTTPException(
            status_code=429,
            detail="Too many support requests. Please try again later."
        )
    
    # 3. Validate topic
    valid_topics = ["Account Issues", "Assessment Problems", "Technical Bug", "Feature Request", "Other"]
    if data.topic not in valid_topics:
        data.topic = "Other"
    
    # 4. Log the request
    submitted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"Support request from {data.email} ({data.source}): {data.topic}")
    
    # 5. Send emails
    email_sent = _send_support_emails(data, submitted_at)
    
    if not email_sent:
        # Log but don't fail - we don't want to lose the user's message
        logger.error(f"Failed to send support emails for request from {data.email}")
    
    return {
        "success": True,
        "message": "Support request submitted successfully. You will receive a confirmation email shortly."
    }
