from sqlalchemy import Column, String, Integer, UniqueConstraint
from app.db import Base
import uuid

class SpiritualGiftDefinition(Base):
    __tablename__ = "spiritual_gift_definitions"
    __table_args__ = (
        UniqueConstraint('gift_slug', 'version', 'locale', name='uq_gift_slug_version_locale'),
    )
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    gift_slug = Column(String, nullable=False)  # e.g., wisdom, faith
    display_name = Column(String, nullable=False)
    short_summary = Column(String, nullable=True)
    full_definition = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    locale = Column(String, nullable=False, default="en")

    # Unique constraint (gift_slug, version, locale) can be enforced via migration if desired.
