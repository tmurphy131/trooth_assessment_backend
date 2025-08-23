from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from app.db import Base
from datetime import datetime
import uuid

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    apprentice_id = Column(String, ForeignKey("users.id"), nullable=False)
    answers = Column(JSON, nullable=False)
    scores = Column(JSON, nullable=True)
    recommendation = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
