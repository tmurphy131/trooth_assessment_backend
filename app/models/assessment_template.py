from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Float, Integer, JSON
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime
import uuid

# models/assessment_template.py
class AssessmentTemplate(Base):
    __tablename__ = "assessment_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_published = Column(Boolean, default=False)
    is_master_assessment = Column(Boolean, default=False)  # True for the main Trooth Assessment
    created_by = Column(String, ForeignKey("users.id"), nullable=True)  # Allow null for existing records
    created_at = Column(DateTime, default=datetime.utcnow)
    # Explicit version for versioned assessments (e.g., spiritual gifts). Null for legacy rows.
    version = Column(Integer, nullable=True)

    # Optional metadata for routing/scoring/reporting. These are additive and nullable to preserve
    # backward compatibility with existing rows and tests that don't set them.
    # A human/route-friendly stable key (e.g., "master_trooth_v1", "spiritual_gifts_v1").
    key = Column(String, nullable=True)
    # How this template should be scored: e.g., "ai_master", "ai_generic", "deterministic".
    scoring_strategy = Column(String, nullable=True)
    # Free-form rubric JSON (e.g., weights, categories). Used by generic scorers.
    rubric_json = Column(JSON, nullable=True)
    # Jinja2 email template name for report emails (e.g., "master_trooth_report.html").
    report_template = Column(String, nullable=True)
    # Identifier for PDF renderer (e.g., "master_trooth", "generic").
    pdf_renderer = Column(String, nullable=True)

    # Relationship to User who created the template
    creator = relationship("User", back_populates="created_templates")

    # Relationship to template questions
    questions = relationship("AssessmentTemplateQuestion", back_populates="template")
