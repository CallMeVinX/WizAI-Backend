# Service Documentation: `app/services/lead_service.py`

## Overview
The `lead_service.py` module encapsulates all business logic and database querying operations for the `Lead` entity using SQLAlchemy. It decouples persistence concerns from HTTP routing logic.

## Core Functions

### `get_leads(db, status=None, owner=None, country=None, q=None, page=1, page_size=25, sort_by="created_at", sort_order="desc") -> tuple[list[Lead], int]`
Executes paginated queries supporting multi-attribute filtering:
- **Filtering**: Filters on normalized `lead_status`, `contact_owner` (case-insensitive partial `ILIKE`), and `country` (partial `ILIKE`).
- **Full-Text Search (`q`)**: Uses SQLAlchemy `or_()` across `full_name`, `first_name`, `last_name`, `company_name`, and `email`.
- **Sorting**: Dynamically orders queries by designated column and sort direction (`asc` or `desc`).
- **Pagination**: Counts total matching records prior to applying limit/offset for accurate client-side pagination calculations.

### `get_lead_by_id(db: Session, lead_id: int) -> Optional[Lead]`
Retrieves a single lead entity by its primary key `id`.

### `update_lead(db: Session, lead_id: int, updates: dict) -> Optional[Lead]`
Performs partial field updates on a lead entity (PATCH):
- Validates field existence on the model via `hasattr()`.
- Automatically normalizes `lead_status` when updated.
- Recomputes and updates `phone_normalized` when phone numbers change.
- Commits transactions and refreshes the instance from the database.

### `find_lead_by_email(db: Session, email: str) -> Optional[Lead]`
Looks up lead entities by exact case-insensitive email match (`func.lower(Lead.email) == normalized`).

### `find_lead_by_phone(db: Session, phone: str) -> list[Lead]`
Finds lead records sharing normalized phone digits via `phone_normalized`.

### `get_distinct_values(db: Session, field: str) -> list[str]`
Retrieves distinct non-null values for a given column to populate dynamic filter dropdowns on the frontend interface (e.g., `/api/leads/filters`).
