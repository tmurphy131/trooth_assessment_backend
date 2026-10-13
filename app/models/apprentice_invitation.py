from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from datetime import datetime, timedelta, UTC
from app.db import Base
from app.services.invite_codes import generate_invite_code
import uuid

class ApprenticeInvitation(Base):
    __tablename__ = "apprentice_invitations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mentor_id = Column(String, ForeignKey("users.id"), nullable=False)
    apprentice_email = Column(String, nullable=False)
    apprentice_name = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    # Short code apprentices type in the app; canonical form: uppercase, no dash (specs/006-invite-codes)
    code = Column(String(8), nullable=False, unique=True, index=True, default=generate_invite_code)
    # Store as naive datetime (PostgreSQL TIMESTAMP WITHOUT TIME ZONE)
    expires_at = Column(DateTime, default=lambda: (datetime.now(UTC) + timedelta(days=7)).replace(tzinfo=None))
    accepted = Column(Boolean, default=False)