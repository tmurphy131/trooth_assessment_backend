from app.models.notification import Notification
from app.models.user import User
from app.services.email import send_email  # or your actual mail util
from sqlalchemy.orm import Session

def notify_user(db: Session, user: User, message: str, link: str = None, email_subject: str = None):
    notif = Notification(user_id=user.id, message=message, link=link)
    db.add(notif)

    # Email optional
    if user.email and email_subject:
        send_email(
            to=user.email,
            subject=email_subject,
            body=message + (f"\n\nLink: {link}" if link else "")
        )
