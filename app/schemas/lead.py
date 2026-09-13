"""Pydantic schemas for Lead API requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Response Schemas ─────────────────────────────────────────────────────

class LeadResponse(BaseModel):
    """Single lead response."""
    id: int
    record_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    company_name: str
    email: str
    phone_number: Optional[str] = None
    country: Optional[str] = None
    lead_status: str
    lifecycle_stage: Optional[str] = None
    original_source: Optional[str] = None
    source_drill_down: Optional[str] = None
    contact_owner: Optional[str] = None
    lead_score: Optional[int] = None
    notes: Optional[str] = None
    ai_source_channel: Optional[str] = None
    ai_source_detail: Optional[str] = None
    dedup_group_id: Optional[str] = None
    original_create_date: Optional[datetime] = None
    original_modified_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    """Paginated lead list response."""
    data: list[LeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Request Schemas ──────────────────────────────────────────────────────

class LeadUpdate(BaseModel):
    """PATCH /leads/:id request body."""
    lead_status: Optional[str] = None
    contact_owner: Optional[str] = None
    notes: Optional[str] = None
    job_title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    phone_number: Optional[str] = None
    country: Optional[str] = None


class ExtractSourceRequest(BaseModel):
    """POST /api/leads/extract-source request body."""
    lead_id: Optional[int] = None
    notes: Optional[str] = None
    save_to_lead: bool = False


class ExtractSourceResponse(BaseModel):
    """POST /api/leads/extract-source response."""
    channel: str
    detail: str
    lead_id: Optional[int] = None
    saved: bool = False

