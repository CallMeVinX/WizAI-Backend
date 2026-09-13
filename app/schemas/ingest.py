"""Pydantic schemas for lead ingestion."""

from pydantic import BaseModel
from typing import Optional


class FormSubmissionPayload(BaseModel):
    """Schema representing an incoming website form submission payload."""
    form_id: Optional[str] = None
    form_name: Optional[str] = None
    page_url: Optional[str] = None
    submitted_at: Optional[str] = None
    name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    country: Optional[str] = None
    message: Optional[str] = None


class IngestResponse(BaseModel):
    """Response from POST /leads/ingest."""
    created: int
    updated: int
    potential_duplicates: int
    details: list[dict] = []
