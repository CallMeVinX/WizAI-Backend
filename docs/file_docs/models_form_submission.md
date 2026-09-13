# Model Documentation: `app/models/form_submission.py`

## Overview
The `FormSubmission` model represents an immutable audit log entity that persists every raw inbound form submission received through the ingestion endpoint (`POST /api/leads/ingest`).

## Schema & Columns

### Columns:
- **`id`**: Auto-incrementing integer primary key with index.
- **`form_id`**: String identifier of the source web form (e.g., `"contact_sales"`, `"demo_request"`).
- **`form_name`**: Descriptive title of the form (e.g., `"Enterprise Demo Request"`).
- **`page_url`**: URL of the landing page where the user submitted the form.
- **`submitted_at`**: Original submission timestamp parsed from the inbound payload.
- **`raw_payload`**: Complete raw JSON payload stored immutably to preserve historical audit fidelity.
- **`lead_id`**: Optional foreign key referencing `leads.id`. Associates the submission log with the lead created or enriched by the entity resolution pipeline.
- **`created_at`**: Server-generated UTC timestamp when the database record was written.

## Design Rationale
In enterprise CRM systems, lead contact details, lifecycle stages, and assignments evolve over time. `FormSubmission` acts as an immutable, append-only source of truth, guaranteeing historical traceability and auditability whenever original submissions need verification.
