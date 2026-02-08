from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from datetime import datetime, timedelta, UTC
from app.db import Base
import uuid

class ApprenticeInvitation(Base):
    __tablename__ = "apprentice_invitations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mentor_id = Column(String, ForeignKey("users.id"), nullable=False)
    apprentice_email = Column(String, nullable=False)
    apprentice_name = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, default=lambda: datetime.now(UTC) + timedelta(days=7))
    accepted = Column(Boolean, default=False)