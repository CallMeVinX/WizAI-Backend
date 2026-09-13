# Schema Layer Documentation: `app/schemas/`

The *Schemas* layer leverages **Pydantic v2** to enforce runtime type validation, ORM serialization (via `from_attributes=True`), and automated OpenAPI/Swagger documentation.

---

## 1. `app/schemas/lead.py`
Defines Data Transfer Objects (DTOs) for reading and updating `Lead` entities:
- **`LeadResponse`**: Full lead representation schema configured with `from_attributes=True`. Returns contact info, status, audit metadata, AI attribution fields (`ai_source_channel`, `ai_source_detail`), and cluster identifier `dedup_group_id`.
- **`LeadListResponse`**: Standard pagination envelope containing `data: list[LeadResponse]`, `total`, `page`, `page_size`, and `total_pages`.
- **`LeadUpdate`**: Request body for `PATCH /api/leads/{id}`. All attributes are optional (`Optional[str]`), enabling partial updates to status, owner, notes, or contact fields.
- **`ExtractSourceRequest`**: Request body for `POST /api/leads/extract-source` (`lead_id`, `notes`, `save_to_lead`).
- **`ExtractSourceResponse`**: Response schema containing parsed attribution results (`channel`, `detail`, `lead_id`, `saved`).

---

## 2. `app/schemas/dedupe.py`
Data exchange schemas for deduplication and quality review:
- **`DedupeCandidateResponse`**: Pairwise candidate duplicate model from table `dedupe_candidates` (`lead_id_1`, `lead_id_2`, `confidence`, `match_reasons`, `explanation`, `status`, and embedded `lead_1` & `lead_2`).
- **`DedupeCandidateListResponse`**: List envelope containing `data: list[DedupeCandidateResponse]` and `total`.
- **`DedupeClusterResponse`**: Transitive graph cluster schema (`group_id`, `confidence`, `explanation`, `lead_ids: list[int]`, and nested `leads` array).
- **`DedupeClusterListResponse`**: List envelope containing `clusters: list[DedupeClusterResponse]` and `total`.
- **`DedupeCandidateUpdate`**: Request schema for `PATCH /api/leads/dedupe-candidates/{id}` to submit human review decisions (`status: str`, constrained to `"confirmed"`, `"rejected"`, or `"pending"`).

---

## 3. `app/schemas/ingest.py`
Handles payload structures for inbound website form submissions:
- **`FormSubmissionPayload`**: Schema representing inbound form submissions (`form_id`, `form_name`, `page_url`, `submitted_at`, `name`, `email`, `phone`, `company`, `country`, `message`).
- **`IngestResponse`**: Ingestion outcome report (`created: int`, `updated: int`, `potential_duplicates: int`, and `details: list[dict]`).

---

## 4. `app/schemas/dashboard.py`
Reporting schema for aggregate metrics:
- **`DashboardResponse`**: High-level aggregated telemetry:
  - `by_status: dict[str, int]`
  - `by_channel: dict[str, int]`
  - `by_owner: dict[str, int]`
  - `by_lifecycle: dict[str, int]`
  - `total_leads: int`
  - `recent_leads: int` (last 30 days)
