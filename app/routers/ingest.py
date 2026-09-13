"""Lead ingestion API route."""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.schemas.ingest import FormSubmissionPayload, IngestResponse
from app.models.lead import Lead
from app.models.form_submission import FormSubmission
from app.services.dedupe_service import find_best_match
from app.services.source_extractor import extract_source
from app.utils.normalizers import (
    normalize_email,
    normalize_phone,
    normalize_country,
    normalize_status,
    resolve_name,
    parse_date,
    normalize_company_for_dedup,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leads", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
def ingest_form_submissions(
    submissions: list[FormSubmissionPayload],
    db: Session = Depends(get_db),
):
    """Ingest website form submissions.
    
    For each submission, uses the entity resolution pipeline (blocking and scoring)
    to determine whether to create or update records:
    1. Build a transient Lead from the submission
    2. Run blocking+scoring against all existing leads
    3. If best match above threshold → update existing lead
    4. Otherwise → create new lead
    5. Run source extraction on message
    6. Log the form submission
    """
    created = 0
    updated = 0
    potential_duplicates = 0
    details = []

    # Load all existing leads once for matching
    existing_leads = db.query(Lead).all()

    for sub in submissions:
        email = normalize_email(sub.email)
        if not email:
            details.append({"email": sub.email, "action": "skipped", "reason": "Invalid email"})
            continue

        # Resolve name
        first, last, full = resolve_name(None, None, sub.name)

        # Transient in-memory Lead instance for pre-insertion similarity scoring
        transient = Lead(
            id=-1,  # Transient surrogate ID (not persisted)
            first_name=first,
            last_name=last,
            full_name=full,
            company_name=sub.company or "Unknown",
            email=email,
            phone_number=sub.phone,
            phone_normalized=normalize_phone(sub.phone),
            country=normalize_country(sub.country),
            notes=sub.message,
        )

        # Execute matching pipeline using deduplication scoring threshold
        match_result = find_best_match(transient, existing_leads, threshold=0.6)

        if match_result:
            existing, confidence, scores = match_result

            # Update existing lead
            if sub.message and sub.message.strip():
                existing.notes = f"{existing.notes or ''}\n---\n[Form: {sub.form_name}] {sub.message}".strip()
            if sub.phone and not existing.phone_number:
                existing.phone_number = sub.phone
                existing.phone_normalized = normalize_phone(sub.phone)
            if sub.country and not existing.country:
                existing.country = normalize_country(sub.country)

            # Re-extract source if message provides new info
            if sub.message:
                channel, detail = extract_source(sub.message)
                if channel != "Other":
                    existing.ai_source_channel = channel
                    existing.ai_source_detail = detail

            db.commit()
            updated += 1
            details.append({
                "email": email,
                "action": "updated",
                "lead_id": existing.id,
                "match_confidence": round(confidence, 4),
            })

            # Log form submission
            form_log = FormSubmission(
                form_id=sub.form_id,
                form_name=sub.form_name,
                page_url=sub.page_url,
                submitted_at=parse_date(sub.submitted_at) if sub.submitted_at else None,
                raw_payload=sub.model_dump(),
                lead_id=existing.id,
            )
            db.add(form_log)

        else:
            # Extract source
            channel, source_detail = extract_source(sub.message)

            # Create new lead
            new_lead = Lead(
                first_name=first,
                last_name=last,
                full_name=full,
                company_name=sub.company or "Unknown",
                email=email,
                phone_number=sub.phone,
                phone_normalized=normalize_phone(sub.phone),
                country=normalize_country(sub.country),
                lead_status="new",
                lifecycle_stage="Lead",
                notes=f"[Form: {sub.form_name}] {sub.message}" if sub.message else None,
                ai_source_channel=channel,
                ai_source_detail=source_detail,
                original_create_date=parse_date(sub.submitted_at) if sub.submitted_at else datetime.now(timezone.utc),
            )
            db.add(new_lead)
            db.flush()  # Get the ID

            # Add to existing_leads list for subsequent submissions in same batch
            existing_leads.append(new_lead)

            created += 1
            details.append({"email": email, "action": "created", "lead_id": new_lead.id})

            # Log form submission
            form_log = FormSubmission(
                form_id=sub.form_id,
                form_name=sub.form_name,
                page_url=sub.page_url,
                submitted_at=parse_date(sub.submitted_at) if sub.submitted_at else None,
                raw_payload=sub.model_dump(),
                lead_id=new_lead.id,
            )
            db.add(form_log)

    db.commit()

    return IngestResponse(
        created=created,
        updated=updated,
        potential_duplicates=potential_duplicates,
        details=details,
    )

