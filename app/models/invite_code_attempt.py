from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index
from datetime import datetime, UTC
from app.db import Base
import uuid


class InviteCodeAttempt(Base):
    """One invite-code redemption attempt: rate limit + audit trail (specs/006-invite-codes)."""
    __tablename__ = "invite_code_attempts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # No FK: revoking (deleting) an invite must not cascade into the audit rows.
    invitation_id = Column(String, nullable=True)
    succeeded = Column(Boolean, nullable=False)
    # Store as naive datetime (PostgreSQL TIMESTAMP WITHOUT TIME ZONE)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    __table_args__ = (
        Index("ix_invite_code_attempts_user_created", "user_id", "created_at"),
    )
