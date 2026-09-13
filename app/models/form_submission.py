"""FormSubmission SQLAlchemy model."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, JSON
from app.database import Base


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(String(50), nullable=True)
    form_name = Column(String(100), nullable=True)
    page_url = Column(String(200), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<FormSubmission(id={self.id}, form_id='{self.form_id}')>"
