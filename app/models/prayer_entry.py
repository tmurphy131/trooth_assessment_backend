from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime
from datetime import datetime, UTC
from app.db import Base
import uuid


class PrayerEntry(Base):
    __tablename__ = "prayer_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    apprentice_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    body = Column(Text, nullable=True)
    # praise | confession | thanksgiving | request | intercession (validated in schema)
    category = Column(String(20), nullable=False, default="request")
    praying_for = Column(String(120), nullable=True)
    scripture_ref = Column(String(120), nullable=True)
    shared_with_mentor = Column(Boolean, nullable=False, default=False)
    answered_at = Column(DateTime, nullable=True)
    answer_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
