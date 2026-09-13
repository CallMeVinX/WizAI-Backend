# Router Layer Documentation: API Endpoints (`app/routers/`)

The *Routers* layer handles inbound HTTP requests, validates request payloads via Pydantic schemas, delegates business logic execution to domain *Services*, and serializes JSON responses.

---

## 1. `app/routers/ingest.py`
Inbound web form and webhook ingestion endpoint (`POST /api/leads/ingest`):
- Receives a JSON array of `FormSubmissionPayload` objects.
- Logs each inbound submission immutably into `form_submissions` for historical audit tracking.
- Constructs an in-memory transient `Lead` model for similarity evaluation.
- **Entity Resolution & Non-Destructive Enrichment**: Calls `find_best_match` in `dedupe_service`. If composite confidence $\ge 0.60$, the existing record is updated and enriched (timestamps and messages appended to notes, missing phone/country populated). Otherwise, a new lead is created.
- Automatically triggers source attribution extraction on submission messages via `source_extractor`.

---

## 2. `app/routers/dedupe.py`
Controls entity deduplication sweeps and manual audit approval workflows:
- **`POST /api/leads/dedupe-candidates`**: Triggers the 4-stage deduplication pipeline (Blocking $\to$ Scoring $\to$ LLM Adjudication $\to$ Union-Find Grouping) and persists candidate pairs to `dedupe_candidates`.
- **`GET /api/leads/dedupe-candidates`**: Lists candidate duplicate pairs with optional filtering by `status` (`pending`, `confirmed`, `rejected`) and threshold `min_confidence`.
- **`GET /api/leads/dedupe-clusters`**: Returns transitive graph clusters grouped by UUID `group_id`, surfacing member `lead_ids` and nested lead profiles.
- **`PATCH /api/leads/dedupe-candidates/{candidate_id}`**: Human-in-the-loop review endpoint updating candidate verification status (`"confirmed"`, `"rejected"`, or `"pending"`).

---

## 3. `app/routers/leads.py`
Core CRUD operations and lead directory management:
- **`GET /api/leads`**: Paginated lead listing supporting multi-attribute filters (`status`, `owner`, `country`), dynamic sorting (`sort_by`, `sort_order`), and full-text search (`q`).
- **`GET /api/leads/export`**: Streams a dynamically generated RFC 4180 CSV export adhering to currently active filter criteria with `Content-Disposition` attachment headers.
- **`GET /api/leads/filters`**: Returns distinct values for frontend dropdowns (`statuses`, `owners`, `countries`, `channels`).
- **`POST /api/leads/extract-source`**: Standalone AI source extraction endpoint for parsing raw notes text and optionally saving the result to a specified lead.
- **`GET /api/leads/{lead_id}`** & **`PATCH /api/leads/{lead_id}`**: Retrieves single lead profiles or executes partial field updates (`lead_status`, `contact_owner`, `notes`, etc.).

---

## 4. `app/routers/dashboard.py`
- **`GET /api/dashboard`**: Returns centralized, real-time telemetry aggregated directly in PostgreSQL using `func.count()`. Categorizes data into distributions across lead status, attribution channel, contact owner, lifecycle stage, total record count, and recent leads from the last 30 days.
