"""Lead CRUD business logic."""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.lead import Lead
from app.utils.normalizers import normalize_status, normalize_phone


def get_leads(
    db: Session,
    status: Optional[str] = None,
    owner: Optional[str] = None,
    country: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[Lead], int]:
    """List leads with filtering, search, sorting, and pagination.
    
    Returns (leads, total_count).
    """
    query = db.query(Lead)

    # Apply filters
    if status:
        normalized = normalize_status(status)
        query = query.filter(Lead.lead_status == normalized)

    if owner:
        query = query.filter(Lead.contact_owner.ilike(f"%{owner}%"))

    if country:
        query = query.filter(Lead.country.ilike(f"%{country}%"))

    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Lead.full_name.ilike(search),
                Lead.first_name.ilike(search),
                Lead.last_name.ilike(search),
                Lead.company_name.ilike(search),
                Lead.email.ilike(search),
            )
        )

    # Total count before pagination
    total = query.count()

    # Sorting
    sort_column = getattr(Lead, sort_by, Lead.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Pagination
    offset = (page - 1) * page_size
    leads = query.offset(offset).limit(page_size).all()

    return leads, total


def get_lead_by_id(db: Session, lead_id: int) -> Optional[Lead]:
    """Get a single lead by internal ID."""
    return db.query(Lead).filter(Lead.id == lead_id).first()


def update_lead(db: Session, lead_id: int, updates: dict) -> Optional[Lead]:
    """Update a lead's mutable fields."""
    lead = get_lead_by_id(db, lead_id)
    if not lead:
        return None

    for key, value in updates.items():
        if value is not None and hasattr(lead, key):
            if key == "lead_status":
                value = normalize_status(value)
            if key == "phone_number":
                lead.phone_normalized = normalize_phone(value)
            setattr(lead, key, value)

    db.commit()
    db.refresh(lead)
    return lead


def find_lead_by_email(db: Session, email: str) -> Optional[Lead]:
    """Find a lead by exact email match."""
    normalized = email.strip().lower()
    return db.query(Lead).filter(func.lower(Lead.email) == normalized).first()


def find_lead_by_phone(db: Session, phone: str) -> list[Lead]:
    """Find leads by normalized phone digits."""
    phone_norm = normalize_phone(phone)
    if not phone_norm:
        return []
    return db.query(Lead).filter(Lead.phone_normalized == phone_norm).all()


def get_distinct_values(db: Session, field: str) -> list[str]:
    """Get distinct non-null values for a field (for filter dropdowns)."""
    column = getattr(Lead, field, None)
    if column is None:
        return []
    result = db.query(column).filter(column.isnot(None)).distinct().order_by(column).all()
    return [r[0] for r in result if r[0]]
