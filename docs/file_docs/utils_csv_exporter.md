# Utility Documentation: `app/utils/csv_exporter.py`

## Overview
The `csv_exporter.py` module provides in-memory serialization utilities for generating streaming CSV files from lead query sets. It powers the `GET /api/leads/export` endpoint.

---

## Function Reference

### `leads_to_csv(leads: list[dict[str, Any]]) -> str`
Converts a list of lead dictionaries into an RFC 4180-compliant CSV string.

### Mechanics & Implementation:
1. **Empty Set Handling**: If the input list is empty, returns an empty string `""`.
2. **Buffer Allocation**: Uses an in-memory `io.StringIO()` buffer, avoiding intermediate disk I/O.
3. **Canonical Field Ordering**: Formats fields into a standardized, predictable schema:
   ```python
   fieldnames = [
       "id", "record_id", "first_name", "last_name", "full_name",
       "job_title", "company_name", "email", "phone_number", "country",
       "lead_status", "lifecycle_stage", "original_source", "contact_owner",
       "lead_score", "notes", "ai_source_channel", "ai_source_detail",
       "original_create_date", "original_modified_date",
   ]
   ```
4. **Resilient Writing**: Uses `csv.DictWriter` with `extrasaction="ignore"` to safely suppress extraneous internal ORM attributes.
5. **Streaming Response Compatibility**: The generated string is piped directly into FastAPI's `Response` with `media_type="text/csv"` and `Content-Disposition: attachment; filename=leads_export.csv`.
