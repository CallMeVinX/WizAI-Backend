"""CSV import service for bulk ingesting leads into the database."""

import csv
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.utils.normalizers import (
    normalize_status,
    normalize_phone,
    normalize_country,
    normalize_owner,
    normalize_email,
    normalize_lifecycle,
    resolve_name,
    parse_date,
)

logger = logging.getLogger(__name__)


def import_csv(db: Session, csv_path: str) -> int:
    """Import leads from CSV file into the database.
    
    Applies all normalizations during import.
    Returns the number of rows imported.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    count = 0
    batch = []
    batch_size = 200

    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                lead = _parse_row(row)
                if lead:
                    batch.append(lead)
                    count += 1

                    if len(batch) >= batch_size:
                        db.bulk_save_objects(batch)
                        db.commit()
                        batch = []
                        logger.info(f"Imported {count} leads...")

            except Exception as e:
                logger.error(f"Error parsing row {count + 1}: {e} | Row: {row.get('Record ID', 'N/A')}")
                continue

        if batch:
            db.bulk_save_objects(batch)
            db.commit()

    logger.info(f"CSV import complete: {count} leads imported")
    return count


def _parse_row(row: dict) -> Lead | None:
    """Parse a single CSV row into a Lead model instance."""
    email = normalize_email(row.get("Email", ""))
    if not email:
        return None

    company = (row.get("Company Name") or "").strip()
    if not company:
        company = "Unknown"

    # Resolve name fields
    first, last, full = resolve_name(
        row.get("First Name"),
        row.get("Last Name"),
        row.get("Full Name"),
    )

    # Parse phone
    raw_phone = (row.get("Phone Number") or "").strip()
    phone_norm = normalize_phone(raw_phone)

    # Parse dates
    create_date = parse_date(row.get("Create Date"))
    modified_date = parse_date(row.get("Last Modified Date"))

    # Parse lead score
    lead_score = None
    raw_score = (row.get("Lead Score") or "").strip()
    if raw_score:
        try:
            lead_score = int(raw_score)
        except ValueError:
            pass

    # Parse record ID
    record_id = None
    raw_id = (row.get("Record ID") or "").strip()
    if raw_id:
        try:
            record_id = int(raw_id)
        except ValueError:
            pass

    return Lead(
        record_id=record_id,
        first_name=first,
        last_name=last,
        full_name=full,
        job_title=(row.get("Job Title") or "").strip() or None,
        company_name=company,
        email=email,
        phone_number=raw_phone or None,
        phone_normalized=phone_norm,
        country=normalize_country(row.get("Country/Region")),
        lead_status=normalize_status(row.get("Lead Status")),
        lifecycle_stage=normalize_lifecycle(row.get("Lifecycle Stage")),
        original_source=(row.get("Original Source") or "").strip() or None,
        source_drill_down=(row.get("Original Source Drill-Down 1") or "").strip() or None,
        contact_owner=normalize_owner(row.get("Contact Owner")),
        lead_score=lead_score,
        notes=(row.get("Notes") or "").strip() or None,
        original_create_date=create_date,
        original_modified_date=modified_date,
    )
