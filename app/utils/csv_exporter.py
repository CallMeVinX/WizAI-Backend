"""CSV export helper."""

import csv
import io
from typing import Any


def leads_to_csv(leads: list[dict[str, Any]]) -> str:
    """Convert a list of lead dicts to a CSV string."""
    if not leads:
        return ""

    output = io.StringIO()
    fieldnames = [
        "id", "record_id", "first_name", "last_name", "full_name",
        "job_title", "company_name", "email", "phone_number", "country",
        "lead_status", "lifecycle_stage", "original_source", "contact_owner",
        "lead_score", "notes", "ai_source_channel", "ai_source_detail",
        "original_create_date", "original_modified_date",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead)

    return output.getvalue()
