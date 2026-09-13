"""Lead CRUD API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.schemas.lead import (
    LeadResponse,
    LeadListResponse,
    LeadUpdate,
    ExtractSourceRequest,
    ExtractSourceResponse,
)
from app.services.lead_service import get_leads, get_lead_by_id, update_lead, get_distinct_values
from app.services.source_extractor import extract_source
from app.utils.csv_exporter import leads_to_csv

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=LeadListResponse)
def list_leads(
    status: Optional[str] = Query(None, description="Filter by lead status"),
    owner: Optional[str] = Query(None, description="Filter by contact owner"),
    country: Optional[str] = Query(None, description="Filter by country"),
    q: Optional[str] = Query(None, description="Free-text search across name/company/email"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Page size"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
):
    """List leads with filtering, search, and pagination."""
    leads, total = get_leads(
        db, status=status, owner=owner, country=country, q=q,
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order,
    )

    total_pages = (total + page_size - 1) // page_size

    return LeadListResponse(
        data=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/export")
def export_leads(
    status: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export leads as CSV with the same filters as list endpoint."""
    leads, _ = get_leads(
        db, status=status, owner=owner, country=country, q=q,
        page=1, page_size=10000,  # Export all matching
    )

    lead_dicts = []
    for lead in leads:
        d = LeadResponse.model_validate(lead).model_dump()
        # Convert datetime to string for CSV
        for key in ["original_create_date", "original_modified_date", "created_at", "updated_at"]:
            if d.get(key):
                d[key] = str(d[key])
        lead_dicts.append(d)

    csv_content = leads_to_csv(lead_dicts)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )


@router.get("/filters")
def get_filters(db: Session = Depends(get_db)):
    """Get distinct values for filter dropdowns."""
    return {
        "statuses": get_distinct_values(db, "lead_status"),
        "owners": get_distinct_values(db, "contact_owner"),
        "countries": get_distinct_values(db, "country"),
        "channels": get_distinct_values(db, "ai_source_channel"),
    }


@router.post("/extract-source", response_model=ExtractSourceResponse)
def extract_lead_source(body: ExtractSourceRequest, db: Session = Depends(get_db)):
    """Extract lead acquisition source from notes or an existing lead."""
    notes = body.notes
    lead = None
    if body.lead_id is not None:
        lead = get_lead_by_id(db, body.lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not notes:
            notes = lead.notes

    if not notes or not notes.strip():
        raise HTTPException(status_code=400, detail="Notes content or a lead with notes is required")

    channel, detail = extract_source(notes)

    saved = False
    if lead and body.save_to_lead:
        lead.ai_source_channel = channel
        lead.ai_source_detail = detail
        db.commit()
        saved = True

    return ExtractSourceResponse(
        channel=channel,
        detail=detail,
        lead_id=lead.id if lead else None,
        saved=saved,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get a single lead by ID."""
    lead = get_lead_by_id(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def patch_lead(lead_id: int, body: LeadUpdate, db: Session = Depends(get_db)):
    """Update a lead's status, owner, or notes."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    lead = update_lead(db, lead_id, updates)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return LeadResponse.model_validate(lead)
