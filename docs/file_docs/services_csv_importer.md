# Service Documentation: `app/services/csv_importer.py`

## Overview
The `csv_importer.py` module manages bulk ingestion of CRM lead datasets from CSV exports into the PostgreSQL database. It is invoked during initial seeding (`seed.py`) as well as in offline ingestion jobs.

## Core Functions

### `import_csv(db: Session, csv_path: str) -> int`
Executes structured data import from a given CSV file path:
1. **File Validation**: Confirms the file exists, raising `FileNotFoundError` if missing.
2. **Chunked Batching**: 
   - Reads rows using Python's `csv.DictReader` with `utf-8-sig` encoding (handling potential Byte Order Mark characters).
   - Collects instantiated `Lead` models into batches of 200 items.
   - Flushes batches via `db.bulk_save_objects(batch)` and commits to minimize database I/O latency.
   - Returns the total count of successfully imported records.

### `_parse_row(row: dict) -> Lead | None`
Parses an individual raw CSV row dictionary into a SQLAlchemy `Lead` model:
- **Mandatory Email Validation**: Invokes `normalize_email()`. Rows with invalid or missing emails are skipped (`return None`).
- **Name Resolution**: Calls `resolve_name(first_name, last_name, full_name)` to generate `first_name`, `last_name`, and `full_name` consistently.
- **Phone Digit Extraction**: Applies `normalize_phone()` to populate clean digits in `phone_normalized`.
- **Flexible Date Parsing**: Uses `parse_date()` to handle varying ISO dates, US standard formats, and UTC timestamps.
- **Status & Lifecycle Mapping**: Calls `normalize_status()` and `normalize_lifecycle()` for canonical enum alignment.
- **Numeric Casting**: Safely converts `Record ID` and `Lead Score` strings into integers with `ValueError` safeguards.
