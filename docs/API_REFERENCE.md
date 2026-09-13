# WizzAI Lead Management API Reference

Comprehensive specification of all HTTP endpoints, query parameters, request payloads, response schemas, and status codes for the WizzAI Lead Management System.

---

## Global Specifications

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json` (unless requesting CSV export)
- **Authentication**: Currently open for internal microservice consumption (configurable via reverse-proxy or middleware).
- **CORS**: Controlled via `CORS_ORIGINS` environment setting.

---

## 1. System & Health Endpoints

### `GET /health`
Health and readiness probe endpoint.

- **Response (200 OK)**:
  ```json
  {
    "status": "ok"
  }
  ```

### `GET /`
API root metadata and documentation pointer.

- **Response (200 OK)**:
  ```json
  {
    "message": "WizzAI Lead Management API",
    "version": "1.0.0",
    "docs": "/docs"
  }
  ```

---

## 2. Lead Directory & Management

### `GET /api/leads`
Retrieve a paginated list of leads with support for filtering, sorting, and full-text keyword search.

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `status` | string | No | - | Filter by canonical status (`new`, `qualified`, `connected`, `contacted`, `opportunity`, `closed_won`, `closed_lost`) |
| `owner` | string | No | - | Case-insensitive partial match on contact owner |
| `country` | string | No | - | Case-insensitive partial match on country name |
| `q` | string | No | - | Free-text keyword search across first name, last name, full name, company name, and email |
| `page` | integer | No | `1` | Page number (minimum: 1) |
| `page_size` | integer | No | `25` | Page size (1 to 100) |
| `sort_by` | string | No | `"created_at"` | Field name to sort by (`created_at`, `lead_score`, `company_name`, etc.) |
| `sort_order` | string | No | `"desc"` | Sort direction: `"asc"` or `"desc"` |

#### Response (200 OK):
```json
{
  "data": [
    {
      "id": 101,
      "record_id": 984124,
      "first_name": "Isabelle",
      "last_name": "Kapoor",
      "full_name": "Isabelle Kapoor",
      "job_title": "VP of Supply Chain",
      "company_name": "Kapoor Holdings Ltd",
      "email": "isabelle@kapoor.com",
      "phone_number": "+1 323-555-0192",
      "country": "USA",
      "lead_status": "qualified",
      "lifecycle_stage": "Marketing Qualified Lead",
      "original_source": "Offline Sources",
      "source_drill_down": "Tradeshow Booth",
      "contact_owner": "Alice Smith",
      "lead_score": 85,
      "notes": "Spoke at the annual trade fair.",
      "ai_source_channel": "Event",
      "ai_source_detail": "Annual Trade Fair — Booth Visit",
      "dedup_group_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "original_create_date": "2026-05-18T00:00:00Z",
      "original_modified_date": "2026-05-20T10:30:00Z",
      "created_at": "2026-05-20T10:30:00Z",
      "updated_at": "2026-05-21T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 25,
  "total_pages": 1
}
```

---

### `GET /api/leads/{lead_id}`
Retrieve complete detail of a single lead by its internal primary key.

#### Path Parameters:
- `lead_id` (integer, required): Unique internal lead identifier.

#### Responses:
- **200 OK**: Single `LeadResponse` object.
- **404 Not Found**:
  ```json
  {
    "detail": "Lead not found"
  }
  ```

---

### `PATCH /api/leads/{lead_id}`
Partially update attributes of an existing lead.

#### Path Parameters:
- `lead_id` (integer, required): Unique internal lead identifier.

#### Request Body (`LeadUpdate`):
```json
{
  "lead_status": "qualified",
  "contact_owner": "Marcus Vance",
  "notes": "Follow-up meeting booked for next Tuesday."
}
```

#### Responses:
- **200 OK**: Updated `LeadResponse` object.
- **400 Bad Request**: When no valid fields are provided in the payload.
- **404 Not Found**: When `lead_id` does not exist.

---

### `GET /api/leads/export`
Stream a CSV file export of leads matching the supplied query filters.

#### Query Parameters:
Supports identical filters as `GET /api/leads` (`status`, `owner`, `country`, `q`).

#### Response:
- **Status**: `200 OK`
- **Content-Type**: `text/csv`
- **Header**: `Content-Disposition: attachment; filename=leads_export.csv`

---

### `GET /api/leads/filters`
Retrieve distinct, non-null values currently in the database to populate frontend filter dropdowns.

#### Response (200 OK):
```json
{
  "statuses": ["closed_lost", "closed_won", "connected", "contacted", "new", "opportunity", "qualified"],
  "owners": ["Alice Smith", "Marcus Vance", "Sarah Connor"],
  "countries": ["Germany", "Singapore", "USA", "United Kingdom"],
  "channels": ["Event", "LinkedIn", "Manual/Sales", "Organic Search", "Other", "Referral", "Website"]
}
```

---

## 3. Lead Ingestion Engine

### `POST /api/leads/ingest`
Ingest single or bulk form submissions (e.g. from web forms, event scanners, or marketing webhooks). Executes the entity resolution pipeline to either update existing contacts or create new leads.

#### Request Body (`list[FormSubmissionPayload]`):
```json
[
  {
    "form_id": "contact_us_form",
    "form_name": "Contact Us — Enterprise Tier",
    "page_url": "https://wizzai.com/enterprise",
    "submitted_at": "2026-06-15T14:30:00Z",
    "name": "Jane Doe",
    "email": "jane.doe@acme.com",
    "phone": "+1 (555) 234-5678",
    "company": "Acme Corporation",
    "country": "United States",
    "message": "Interested in pilot program after seeing your LinkedIn post about AI workflows."
  }
]
```

#### Response (200 OK, `IngestResponse`):
```json
{
  "created": 1,
  "updated": 0,
  "potential_duplicates": 0,
  "details": [
    {
      "email": "jane.doe@acme.com",
      "action": "created",
      "lead_id": 142
    }
  ]
}
```

If an existing lead matches with confidence $\ge 0.6$:
```json
{
  "created": 0,
  "updated": 1,
  "potential_duplicates": 0,
  "details": [
    {
      "email": "jane.doe@acme.com",
      "action": "updated",
      "lead_id": 89,
      "match_confidence": 0.875
    }
  ]
}
```

---

## 4. Entity Deduplication & Clustering

### `POST /api/leads/dedupe-candidates`
Trigger full deduplication pipeline execution across all stored leads. Scans leads, generates blocking candidate pairs, performs multi-signal scoring, runs selective LLM adjudication, clusters transitive duplicates via Union-Find, and persists candidates.

#### Response (200 OK, `DedupeCandidateListResponse`):
```json
{
  "data": [
    {
      "id": 1,
      "lead_id_1": 42,
      "lead_id_2": 89,
      "confidence": 0.95,
      "match_reasons": {
        "email": 1.0,
        "phone": 0.8,
        "name": 0.92,
        "company": 1.0,
        "notes_hint": 0.0
      },
      "explanation": "Exact email match (isabelle@kapoor.com); Same company (Kapoor Holdings)",
      "status": "pending",
      "group_id": "c71a3994-e349-4118-87c1-236b9eef8941",
      "created_at": "2026-09-12T14:00:00Z",
      "lead_1": { "id": 42, "full_name": "Isabelle Kapoor" },
      "lead_2": { "id": 89, "full_name": "I. Kapoor" }
    }
  ],
  "total": 1
}
```

---

### `GET /api/leads/dedupe-candidates`
List existing deduplication candidate pairs with optional filtering.

#### Query Parameters:
| Parameter | Type | Required | Description |
|---|---|---|---|
| `status` | string | No | Filter by verification status (`pending`, `confirmed`, `rejected`) |
| `min_confidence`| float | No | Minimum confidence threshold filter (e.g. `0.75`) |

#### Response (200 OK):
`DedupeCandidateListResponse` structure.

---

### `GET /api/leads/dedupe-clusters`
List deduplication results aggregated by transitive clusters (groups of leads that are transitive duplicates of one another).

#### Response (200 OK, `DedupeClusterListResponse`):
```json
{
  "clusters": [
    {
      "group_id": "c71a3994-e349-4118-87c1-236b9eef8941",
      "confidence": 0.95,
      "explanation": "Exact email match (isabelle@kapoor.com); Same company (Kapoor Holdings)",
      "lead_ids": [42, 89],
      "leads": [
        { "id": 42, "full_name": "Isabelle Kapoor", "company_name": "Kapoor Holdings Ltd" },
        { "id": 89, "full_name": "I. Kapoor", "company_name": "Kapoor Holdings" }
      ]
    }
  ],
  "total": 1
}
```

---

### `PATCH /api/leads/dedupe-candidates/{candidate_id}`
Submit a manual quality review decision on a candidate duplicate pair.

#### Path Parameters:
- `candidate_id` (integer, required): Identifier of candidate pair record.

#### Request Body (`DedupeCandidateUpdate`):
```json
{
  "status": "confirmed"
}
```
*Allowed status values*: `"confirmed"`, `"rejected"`, `"pending"`.

#### Responses:
- **200 OK**: Updated `DedupeCandidateResponse`.
- **400 Bad Request**: Invalid status value.
- **404 Not Found**: Candidate ID does not exist.

---

## 5. AI Source & Channel Extraction

### `POST /api/leads/extract-source`
Extract attribution channel and descriptive detail from free-text notes. Can analyze arbitrary text or read and update an existing lead record.

#### Request Body (`ExtractSourceRequest`):
```json
{
  "lead_id": 105,
  "notes": "Met with them at our SaaStr Annual booth during the afternoon session.",
  "save_to_lead": true
}
```

#### Response (200 OK, `ExtractSourceResponse`):
```json
{
  "channel": "Event",
  "detail": "SaaStr Annual — Booth Visit",
  "lead_id": 105,
  "saved": true
}
```

#### Taxonomy of Channels:
- `Website`
- `Event`
- `LinkedIn`
- `Organic Search`
- `Referral`
- `Manual/Sales`
- `Other`

---

## 6. Dashboard Analytics

### `GET /api/dashboard`
Retrieve high-level aggregation metrics across the entire lead repository.

#### Response (200 OK, `DashboardResponse`):
```json
{
  "by_status": {
    "new": 1420,
    "qualified": 280,
    "connected": 150,
    "contacted": 90,
    "opportunity": 55,
    "closed_won": 34,
    "closed_lost": 20
  },
  "by_channel": {
    "Website": 680,
    "Event": 490,
    "LinkedIn": 320,
    "Organic Search": 210,
    "Referral": 180,
    "Manual/Sales": 110,
    "Other": 59
  },
  "by_owner": {
    "Alice Smith": 750,
    "Marcus Vance": 690,
    "Sarah Connor": 609
  },
  "by_lifecycle": {
    "Lead": 1200,
    "Marketing Qualified Lead": 450,
    "Sales Qualified Lead": 230,
    "Opportunity": 120,
    "Customer": 49
  },
  "total_leads": 2049,
  "recent_leads": 312
}
```

---

## Example cURL Requests

### Querying Leads:
```bash
curl -X GET "http://localhost:8000/api/leads?status=qualified&q=Acme&page=1&page_size=10" \
     -H "Accept: application/json"
```

### Ingesting Inbound Form Submissions:
```bash
curl -X POST "http://localhost:8000/api/leads/ingest" \
     -H "Content-Type: application/json" \
     -d '[{
       "form_id": "f_1",
       "form_name": "Demo",
       "name": "Sarah Connor",
       "email": "sarah@cyberdyne.com",
       "company": "Cyberdyne Systems",
       "message": "Inbound phone call regarding enterprise tier"
     }]'
```

### Running Deduplication:
```bash
curl -X POST "http://localhost:8000/api/leads/dedupe-candidates" \
     -H "Accept: application/json"
```
