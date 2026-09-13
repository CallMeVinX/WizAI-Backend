"""Pydantic schemas for dashboard."""

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    """Dashboard aggregation response."""
    by_status: dict[str, int]
    by_channel: dict[str, int]
    by_owner: dict[str, int]
    by_lifecycle: dict[str, int]
    total_leads: int
    recent_leads: int 