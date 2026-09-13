# WizzAI Lead Management System

An enterprise-grade, AI-assisted Lead Management & Entity Resolution Platform built with **FastAPI**, **PostgreSQL**, and **Google Gemini AI**.

The system ingests raw, messy CRM contact datasets and multi-channel inbound form submissions, applies deterministic normalization pipelines, runs high-recall entity deduplication with transitive graph clustering, and extracts attribution channels from unstructured notes.

---

## Key Capabilities

- **High-Performance Ingestion Engine (`/api/leads/ingest`)**:
  - Ingests single or batch web form submissions.
  - Automatically resolves entity identity using a multi-signal scoring pipeline to either update existing contact profiles or create new leads.
  - Generates immutable audit logs for raw inbound submissions.

- **4-Stage Entity Resolution & Deduplication Pipeline (`/api/leads/dedupe-candidates`)**:
  - **Stage 1 (Blocking)**: Inverted index generation across normalized emails, phone suffixes, email domains, and company prefixes to reduce $O(N^2)$ pairwise comparisons to an efficient candidate subset.
  - **Stage 2 (Multi-Signal Scoring)**: Calibrated Jaro-Winkler string similarity, phone digit normalization, and company legal suffix stripping. Built-in false-positive guards prevent inadvertent merging of distinct colleagues sharing company domains.
  - **Stage 3 (AI Adjudication)**: Targeted Google Gemini 3.6 Flash verification for borderline candidate pairs ($0.8 \le \text{confidence} < 1.0$).
  - **Stage 4 (Transitive Graph Clustering)**: Disjoint-Set (Union-Find) with path compression and union-by-rank to group transitive duplicates ($A \sim B \land B \sim C \implies \{A, B, C\}$) into stable UUID clusters.

- **Hybrid Lead Attribution & Source Extractor (`/api/leads/extract-source`)**:
  - High-throughput regex pattern engine covering over 20+ acquisition patterns (Events, Google Ads, Organic Search, LinkedIn, Referrals, Inbound Sales).
  - Resilient LLM fallback to Google Gemini Flash for unstructured, conversational, or ambiguous notes.
  - Zero-downtime offline fallback mechanism ensuring system availability even during external API disruptions.

- **Lead Directory & Real-Time Analytics (`/api/leads`, `/api/dashboard`)**:
  - Paginated lead search, multi-field filtering (`status`, `owner`, `country`, free-text `q`), dynamic dropdown metadata, and streaming CSV export.
  - Real-time aggregation by lifecycle stage, lead status, attribution channel, and contact owner.

---

## Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **API Framework** | **FastAPI** (Python 3.11+) | Asynchronous ASGI framework with native OpenAPI/Swagger generation and strict Pydantic v2 data validation. |
| **Relational Database** | **PostgreSQL 14+** | Enterprise durability, relational integrity, B-Tree indexes on query filters, and future-proof `pg_trgm` extension compatibility. |
| **Database Driver & ORM**| **SQLAlchemy 2.0 + Psycopg v3** | Modern connection pooling (`pool_pre_ping`), session management, and robust SQL abstraction. |
| **AI / LLM Engine** | **Google Gemini 3.6 Flash** (`google-genai`) | Ultra-low latency and minimal inference cost for selective verification and semantic source extraction. |
| **Similarity Algorithms**| **Pure Python Jaro-Winkler** | Dependency-free string distance calculation ensuring zero C/Rust compilation bottlenecks across deployment targets. |
| **Migrations** | **Alembic** | Automated database schema version control and migration tracking. |

---

## Architecture Overview

```mermaid
flowchart TD
    Client[Client Applications / Webhooks] --> Router[FastAPI REST API Layer]
    Router --> Schemas[Pydantic Validation & Serialization]
    
    subgraph Services [Core Service Layer]
        IngestService[Ingest Service]
        DedupeEngine[4-Stage Deduplication Engine]
        SourceExtractor[Hybrid Source Extractor]
        LeadService[Lead Management Service]
    end
    
    Schemas --> IngestService
    Schemas --> DedupeEngine
    Schemas --> LeadService
    
    IngestService --> DedupeEngine
    IngestService --> SourceExtractor
    
    subgraph External [External AI Services]
        Gemini[Google Gemini API]
    end
    
    DedupeEngine -.->|Borderline Pair Adjudication| Gemini
    SourceExtractor -.->|Unstructured Text Fallback| Gemini
    
    subgraph Persistence [Database Layer]
        ORM[SQLAlchemy SessionLocal]
        Postgres[(PostgreSQL Database)]
    end
    
    Services --> ORM
    ORM --> Postgres
```

---

## Quickstart & Local Setup

### 1. Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose** (or PostgreSQL 14+ running locally)
- **Gemini API Key** (optional, available via [Google AI Studio](https://aistudio.google.com/))

### 2. Database & Environment Setup

You can run PostgreSQL using either **Docker Compose** (recommended for quick setup) or your **local PostgreSQL** installation:

#### Option A: Using Docker Compose (Fastest & Automated)
Starts a containerized PostgreSQL 15 instance with database `wizzai_leads` pre-configured on port `5432`:
```bash
docker compose up -d
```

#### Option B: Using Local PostgreSQL (Native Installation)
1. Ensure your local PostgreSQL service is running on port `5432`.
2. Create the target database using `psql` or pgAdmin:
   ```sql
   CREATE DATABASE wizzai_leads;
   ```
3. Update your `.env` file with your local PostgreSQL credentials (see below).

---

### 3. Environment Configuration

Copy the environment template:
```bash
cp .env.example .env
```

Review or edit `.env` parameters:
```ini
# Database connection (adjust username/password if using local PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/wizzai_leads

# AI credentials (optional for testing, required for live LLM features)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash

# CORS & Pipeline tuning
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000
DEFAULT_PAGE_SIZE=25
MAX_PAGE_SIZE=100
DEDUPE_CONFIDENCE_THRESHOLD=0.6
DEDUPE_LLM_THRESHOLD=0.8
DEDUPE_LLM_MAX_PAIRS=5
```

### 4. Installation & Database Initialization

```bash
# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations (or initialize tables via seed)
alembic upgrade head

# Seed initial CRM dataset (2,049 leads + form submissions)
# Use --reset flag to cleanly drop and rebuild tables with the latest schema:
python seed.py --all --reset
```

### 5. Running the Application Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Documentation (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Application health and readiness check |
| `GET` | `/api/leads` | Paginated lead listing with full-text search and filters |
| `GET` | `/api/leads/{id}` | Retrieve individual lead record by primary ID |
| `PATCH` | `/api/leads/{id}` | Update mutable lead attributes (`lead_status`, `contact_owner`, `notes`) |
| `GET` | `/api/leads/export` | Stream CSV export based on active filter parameters |
| `GET` | `/api/leads/filters` | Distinct values for frontend dropdown filters |
| `POST` | `/api/leads/ingest` | Inbound web form submission ingestion with deduplication routing |
| `POST` | `/api/leads/dedupe-candidates`| Trigger asynchronous/synchronous deduplication pipeline scan |
| `GET` | `/api/leads/dedupe-candidates` | Query detected candidate duplicate pairs |
| `GET` | `/api/leads/dedupe-clusters` | Query grouped duplicate clusters with transitive member IDs |
| `PATCH` | `/api/leads/dedupe-candidates/{id}` | Confirm, reject, or reset duplicate candidate pair |
| `POST` | `/api/leads/extract-source` | Extract attribution channel from free-text notes |
| `GET` | `/api/dashboard` | Aggregated dashboard metrics across status, channel, and owners |

*For complete payload definitions, request schemas, and cURL examples, see [docs/API_REFERENCE.md](docs/API_REFERENCE.md).*

---

## Testing & Quality Assurance

The test suite validates data normalizers, string similarity algorithms, entity resolution boundaries, rule extraction, and API workflows:

```bash
# Execute test suite with verbose output
pytest tests/ -v

# Run with test coverage report
pytest --cov=app tests/
```

### Key Test Suites:
- `tests/test_normalizers.py`: Verifies multi-format date parsing, E.164 phone digit extraction, corporate suffix removal, and canonical status enum mapping.
- `tests/test_similarity.py`: Verifies boundary conditions of pure-Python Jaro-Winkler string metric.
- `tests/test_dedupe.py`: Verifies blocking key generation, exact/fuzzy duplicate scoring, transitive Union-Find grouping, and false-positive resilience against collocated individuals with identical surnames.
- `tests/test_source_extractor.py`: Tests regex rule parsing across event booths, LinkedIn interactions, Google Ads, and organic search landing pages.
- `tests/test_api.py`: Full end-to-end integration test executing complete CRUD lifecycle, ingestion, extraction, and dashboard aggregation against an in-memory SQLite database.

---

## LLM Engine Selection & Cost Analysis

- **Chosen Model**: `gemini-3.6-flash` (Google Gemini 3.6 Flash via official `google-genai` SDK).
- **Why Gemini 3.6 Flash (vs. `gemini-2.0-flash` or `gemini-3.8-flash`)**:
  1. **Production GA Status & Quota Stability**: Google AI Studio has officially superseded `gemini-2.0-flash` (returning `404 NOT_FOUND` instructing callers to use `gemini-3.6-flash`). Non-standard aliases like `gemini-3.8-flash` suffer from emergency rate-limiting (capped at 20 requests/day). In contrast, `gemini-3.6-flash` is active with standard developer quotas (15 RPM / 1,500 requests/day on free tier).
  2. **Sub-Second Latency**: Delivers TTFT under 400ms, essential for real-time CRM API endpoints (`POST /api/leads/extract-source`).
  3. **Strict JSON Schema Compliance**: Accurately emits Pydantic-compliant structured payloads (`is_duplicate`, `confidence`, `reasoning`) without extraneous markdown formatting.
  4. **Minimal Inference Cost**: At $0.10/1M input tokens, total project spend across all 2,049 seed leads is **<$0.01** (covered entirely by the free tier).
  5. **Hermetic Test Guarantee**: All 52 unit/integration tests run **100% offline with zero external API calls**, incurring $0.00 in testing expenses.

---

## Documentation Suite & Architecture Guides

Comprehensive technical documentation, architecture diagrams, algorithm deep dives, and component-level file guides are maintained in the [`docs/`](docs/) directory:

### Core Architecture & Technical Runbooks
| Document | Focus / Key Topics Covered |
|---|---|
| **[Backend Architecture Specification](docs/BACKEND_ARCHITECTURE.md)** | Layered service-oriented design, request lifecycles, database transactions, technology tradeoffs, and false-positive defense. |
| **[Deduplication & Entity Resolution Engine](docs/DEDUPLICATION_PIPELINE.md)** | Mathematical formulation, 4-stage pipeline (Blocking, Multi-Signal Scoring, Gemini Adjudication, Union-Find), and cluster UUID assignment. |
| **[Hybrid AI Source Extraction System](docs/AI_SOURCE_EXTRACTION.md)** | Dual-tier attribution pipeline: 20+ regex fast-path patterns, Gemini LLM fallback, prompt schemas, and offline fail-safe behavior. |
| **[API Reference & Integration Guide](docs/API_REFERENCE.md)** | Exhaustive endpoint documentation, query parameters, request/response JSON schemas, error codes, and copy-pasteable cURL examples. |

### Component-Level File Documentation ([`docs/file_docs/`](docs/file_docs/))
Detailed, function-by-function implementation reference for every backend file:

- **Core & Infrastructure**:
  - [`core_utils.md`](docs/file_docs/core_utils.md): Application entry point (`app/main.py`), Pydantic settings (`app/config.py`), and SQLAlchemy connection pooling (`app/database.py`).
- **Data Utilities (`app/utils/`)**:
  - [`utils_normalizers.md`](docs/file_docs/utils_normalizers.md): Deterministic cleaning for dates, names (right-most split), phones (extension stripping), company suffixes, and status enums.
  - [`utils_similarity.md`](docs/file_docs/utils_similarity.md): Pure-Python Jaro and Jaro-Winkler string distance implementations and prefix-scaling factors.
  - [`utils_csv_exporter.md`](docs/file_docs/utils_csv_exporter.md): In-memory streaming RFC 4180 CSV serialization helper.
- **Data Models (`app/models/`)**:
  - [`models_lead.md`](docs/file_docs/models_lead.md): Central lead entity, raw vs. normalized columns, and PostgreSQL B-Tree indexes.
  - [`models_dedupe.md`](docs/file_docs/models_dedupe.md): Pairwise candidate audit table, composite scores, and verification status state machine.
  - [`models_form_submission.md`](docs/file_docs/models_form_submission.md): Immutable audit log capturing raw inbound form payloads.
- **Business Services (`app/services/`)**:
  - [`services_dedupe_service.md`](docs/file_docs/services_dedupe_service.md): 4-stage deduplication pipeline execution, candidate scoring, and Disjoint-Set Union-Find.
  - [`services_source_extractor.md`](docs/file_docs/services_source_extractor.md): High-throughput regex catalog and Gemini 3.6 Flash fallback handler.
  - [`services_lead_service.md`](docs/file_docs/services_lead_service.md): CRUD business logic, dynamic multi-field filtering, search expressions, and pagination.
  - [`services_csv_importer.md`](docs/file_docs/services_csv_importer.md): Chunked bulk import (200-record batches) from legacy CRM CSV files.
  - [`services_gemini_client.md`](docs/file_docs/services_gemini_client.md): Singleton Google GenAI client wrapper, automated retries, and markdown fence sanitization.
- **Routers & API Layer (`app/routers/`)**:
  - [`routers.md`](docs/file_docs/routers.md): REST endpoint handlers for ingestion, deduplication, lead management, and telemetry dashboards.
- **Validation Schemas (`app/schemas/`)**:
  - [`schemas.md`](docs/file_docs/schemas.md): Pydantic v2 request/response schemas for DTOs and OpenAPI documentation.

