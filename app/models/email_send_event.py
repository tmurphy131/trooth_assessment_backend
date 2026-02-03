from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from datetime import datetime, UTC
import uuid
from app.db import Base

class EmailSendEvent(Base):
    __tablename__ = "email_send_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=True)
    category = Column(String, nullable=True)  # e.g., 'spiritual_gifts'
    template_version = Column(Integer, nullable=True)
    role_context = Column(String, nullable=True)  # apprentice|mentor|admin
    purpose = Column(String, nullable=False, default="report")  # 'report','invite', etc.
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
