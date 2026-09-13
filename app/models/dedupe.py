"""DedupeCandidate SQLAlchemy model."""

from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, UniqueConstraint, func, JSON
from app.database import Base


class DedupeCandidate(Base):
    __tablename__ = "dedupe_candidates"

    id = Column(Integer, primary_key=True, index=True)
    lead_id_1 = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    lead_id_2 = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Float, nullable=False)
    match_reasons = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending | confirmed | rejected
    group_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("lead_id_1", "lead_id_2", name="uq_dedupe_pair"),
    )

    def __repr__(self):
        return f"<DedupeCandidate(lead_1={self.lead_id_1}, lead_2={self.lead_id_2}, conf={self.confidence})>"
