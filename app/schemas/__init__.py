"""Pydantic request and response schemas package."""

from app.schemas.lead import (
    LeadResponse,
    LeadListResponse,
    LeadUpdate,
    ExtractSourceRequest,
    ExtractSourceResponse,
)
from app.schemas.ingest import FormSubmissionPayload, IngestResponse
from app.schemas.dedupe import (
    DedupeCandidateResponse,
    DedupeCandidateListResponse,
    DedupeClusterResponse,
    DedupeClusterListResponse,
    DedupeCandidateUpdate,
)
from app.schemas.dashboard import DashboardResponse

__all__ = [
    "LeadResponse",
    "LeadListResponse",
    "LeadUpdate",
    "ExtractSourceRequest",
    "ExtractSourceResponse",
    "FormSubmissionPayload",
    "IngestResponse",
    "DedupeCandidateResponse",
    "DedupeCandidateListResponse",
    "DedupeClusterResponse",
    "DedupeClusterListResponse",
    "DedupeCandidateUpdate",
    "DashboardResponse",
]
