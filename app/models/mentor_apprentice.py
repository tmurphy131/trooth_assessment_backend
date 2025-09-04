from sqlalchemy import Column, String, ForeignKey, Boolean
from app.db import Base

class MentorApprentice(Base):
    __tablename__ = "mentor_apprentice"
    apprentice_id = Column(String, ForeignKey("users.id"), primary_key=True)
    mentor_id = Column(String, ForeignKey("users.id"), nullable=False)
    active = Column(Boolean, nullable=False, default=True)