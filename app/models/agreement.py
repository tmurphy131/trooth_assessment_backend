from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from app.db import Base
from datetime import datetime, UTC
import uuid

class AgreementTemplate(Base):
    __tablename__ = 'agreement_templates'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    version = Column(Integer, nullable=False, unique=True)
    markdown_source = Column(Text, nullable=False)
    # Use timezone-aware UTC now; DB may store naive but origin is UTC
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    supersedes_version = Column(Integer, nullable=True)
    author_user_id = Column(String, ForeignKey('users.id'), nullable=True)
    notes = Column(Text, nullable=True)

class Agreement(Base):
    __tablename__ = 'agreements'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    template_version = Column(Integer, nullable=False)
    mentor_id = Column(String, ForeignKey('users.id'), nullable=False)
    apprentice_id = Column(String, ForeignKey('users.id'), nullable=True)
    apprentice_email = Column(String, nullable=False)
    status = Column(String, nullable=False, default='draft')
    apprentice_is_minor = Column(Boolean, default=False, nullable=False)
    parent_required = Column(Boolean, default=False, nullable=False)
    parent_email = Column(String, nullable=True)
    fields_json = Column(JSON, nullable=False)
    content_rendered = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)
    apprentice_signature_name = Column(String, nullable=True)
    apprentice_signed_at = Column(DateTime, nullable=True)
    parent_signature_name = Column(String, nullable=True)
    parent_signed_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    activated_at = Column(DateTime, nullable=True)

class AgreementToken(Base):
    __tablename__ = 'agreement_tokens'
    token = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agreement_id = Column(String, ForeignKey('agreements.id', ondelete='CASCADE'), nullable=False)
    token_type = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
