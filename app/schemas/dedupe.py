"""Pydantic schemas for dedup API."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from app.schemas.lead import LeadResponse


class DedupeCandidateResponse(BaseModel):
    """Single dedupe candidate pair response."""
    id: int
    lead_id_1: int
    lead_id_2: int
    confidence: float
    match_reasons: Optional[dict[str, Any]] = None
    explanation: Optional[str] = None
    status: str
    group_id: Optional[str] = None
    created_at: Optional[datetime] = None

    # Embedded lead details for UI display
    lead_1: Optional[LeadResponse] = None
    lead_2: Optional[LeadResponse] = None

    model_config = {"from_attributes": True}


class DedupeCandidateListResponse(BaseModel):
    """List of dedupe candidates."""
    data: list[DedupeCandidateResponse]
    total: int


class DedupeClusterResponse(BaseModel):
    """Grouped duplicate cluster response schema."""
    group_id: str
    confidence: float
    explanation: str
    lead_ids: list[int]
    leads: Optional[list[LeadResponse]] = None


class DedupeClusterListResponse(BaseModel):
    """List of dedupe clusters."""
    clusters: list[DedupeClusterResponse]
    total: int


class DedupeCandidateUpdate(BaseModel):
    """Request schema for updating dedupe candidate verification status."""
    status: str = Field(..., description="Decision status: 'confirmed', 'rejected', or 'pending'")

