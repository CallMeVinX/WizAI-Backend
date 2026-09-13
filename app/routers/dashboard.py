"""Dashboard API route."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.lead import Lead
from app.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Get dashboard aggregation data."""
    
    # Total leads
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    
    # By status
    status_rows = (
        db.query(Lead.lead_status, func.count(Lead.id))
        .group_by(Lead.lead_status)
        .all()
    )
    by_status = {row[0]: row[1] for row in status_rows if row[0]}
    
    # By AI source channel
    channel_rows = (
        db.query(Lead.ai_source_channel, func.count(Lead.id))
        .filter(Lead.ai_source_channel.isnot(None))
        .group_by(Lead.ai_source_channel)
        .all()
    )
    by_channel = {row[0]: row[1] for row in channel_rows if row[0]}
    
    # By contact owner
    owner_rows = (
        db.query(Lead.contact_owner, func.count(Lead.id))
        .filter(Lead.contact_owner.isnot(None))
        .group_by(Lead.contact_owner)
        .all()
    )
    by_owner = {row[0]: row[1] for row in owner_rows if row[0]}
    
    # By lifecycle stage
    lifecycle_rows = (
        db.query(Lead.lifecycle_stage, func.count(Lead.id))
        .filter(Lead.lifecycle_stage.isnot(None))
        .group_by(Lead.lifecycle_stage)
        .all()
    )
    by_lifecycle = {row[0]: row[1] for row in lifecycle_rows if row[0]}
    
    # Recent leads (last 30 days based on original create date)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_leads = (
        db.query(func.count(Lead.id))
        .filter(Lead.original_create_date >= thirty_days_ago)
        .scalar() or 0
    )
    
    return DashboardResponse(
        by_status=by_status,
        by_channel=by_channel,
        by_owner=by_owner,
        by_lifecycle=by_lifecycle,
        total_leads=total_leads,
        recent_leads=recent_leads,
    )
