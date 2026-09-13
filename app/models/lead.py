"""Lead SQLAlchemy model."""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Float, DateTime, func
from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(BigInteger, unique=True, nullable=True)

    # Name fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)

    # Contact info
    job_title = Column(String(150), nullable=True)
    company_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone_number = Column(String(50), nullable=True)
    phone_normalized = Column(String(20), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)

    # Status & classification
    lead_status = Column(String(20), nullable=False, default="new", index=True)
    lifecycle_stage = Column(String(50), nullable=True)
    original_source = Column(String(100), nullable=True)
    source_drill_down = Column(String(200), nullable=True)
    contact_owner = Column(String(100), nullable=True, index=True)
    lead_score = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # AI-extracted source fields
    ai_source_channel = Column(String(30), nullable=True)
    ai_source_detail = Column(Text, nullable=True)

    # Dedup grouping (set after dedup pipeline runs)
    dedup_group_id = Column(String(36), nullable=True, index=True)

    # Original timestamps from CSV
    original_create_date = Column(DateTime(timezone=True), nullable=True)
    original_modified_date = Column(DateTime(timezone=True), nullable=True)

    # System timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.full_name}', email='{self.email}')>"
