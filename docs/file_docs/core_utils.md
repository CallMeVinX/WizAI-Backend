# Module Documentation: Core & Utils (`app/`, `app/utils/`)

The *Core* layer manages system-level backend configuration (FastAPI initialization, database connection pooling, and environment management), while the *Utils* layer provides deterministic helper algorithms and pure functions free of external framework dependencies.

---

## 1. Core Framework

### `app/main.py`
Primary application entry point for the ASGI FastAPI runtime:
- Configures Cross-Origin Resource Sharing (CORS) via `CORSMiddleware` based on the configured `CORS_ORIGINS`.
- Mounts all application routers (`leads`, `ingest`, `dedupe`, `dashboard`) with route order precedence to avoid parameterized path conflicts.
- Manages application startup and teardown lifespans: auto-initializes relational database tables via `Base.metadata.create_all`.
- Exposes core operational endpoints: `GET /` (metadata probe) and `GET /health` (liveness check).

### `app/config.py`
Type-safe application configuration powered by `pydantic_settings.BaseSettings`:
- Loads environment configuration from `.env` files and system variables: `DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS`, pagination parameters, and deduplication thresholds (`DEDUPE_CONFIDENCE_THRESHOLD`, `DEDUPE_LLM_THRESHOLD`, `DEDUPE_LLM_MAX_PAIRS`).
- Implements `@lru_cache()` on `get_settings()` for singleton performance and zero runtime overhead.

### `app/database.py`
SQLAlchemy 2.0 database engine and session management:
- Automatically injects the modern `postgresql+psycopg://` driver scheme for PostgreSQL URLs.
- Configures connection pooling with `pool_pre_ping=True` to verify socket liveness prior to checkout.
- Exposes the `get_db()` dependency generator, yielding a request-scoped `SessionLocal` that cleanly closes upon request termination.

---

## 2. Utilities Overview (`app/utils/`)

The utility layer provides deterministic helper functions with zero framework dependencies. For comprehensive function-level documentation, refer to the dedicated utility files:

- **[utils_normalizers.md](file:///d:/WizzAi%20-%20Task/backend/docs/file_docs/utils_normalizers.md)**: Multi-format date parsing, name resolution with right-most split, phone extension stripping, corporate legal suffix removal, and status enum mapping.
- **[utils_similarity.md](file:///d:/WizzAi%20-%20Task/backend/docs/file_docs/utils_similarity.md)**: Pure-Python Jaro and Jaro-Winkler string metrics, sliding-window calculations, and prefix-scaling factors.
- **[utils_csv_exporter.md](file:///d:/WizzAi%20-%20Task/backend/docs/file_docs/utils_csv_exporter.md)**: In-memory RFC 4180 CSV serialization and streaming HTTP response formatting.

