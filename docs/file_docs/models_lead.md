# Model Documentation: `app/models/lead.py`

## Overview
Defines the central `Lead` entity representing sales and marketing prospective contacts in the CRM database.

## Schema & Attributes
The `Lead` class inherits from SQLAlchemy's `Base` and maps to the `leads` table in PostgreSQL.

### Core Contact Fields (Raw Data):
- **`id`**: Auto-incrementing integer primary key.
- **`record_id`**: Legacy HubSpot unique identifier from historical CSV exports.
- **`full_name`, `first_name`, `last_name`**: Resolved contact names.
- **`company_name`**: Associated organization or employer.
- **`email`**: Primary email address.
- **`phone_number`**: Raw inbound phone number string.
- **`notes`**: Free-text activity notes containing conversational sales context.
- **`lead_status`, `contact_owner`, `country`, `job_title`**: Categorical fields for CRM filtering and ownership.
- **`original_create_date`, `original_modified_date`**: Historical timestamps from source CRM exports.

### Normalized & Indexed Fields:
Deterministic values computed at ingestion time:
- **`phone_normalized`**: Clean numeric digits (minimum 7 digits) with extensions stripped for deduplication blocking and exact phone lookups.

### AI & Pipeline Enrichment Fields:
- **`ai_source_channel` & `ai_source_detail`**: Attribution channel (`Website`, `Event`, `LinkedIn`, `Organic Search`, `Referral`, `Manual/Sales`, `Other`) and extracted descriptive detail.
- **`dedup_group_id`**: UUID cluster identifier assigned by the Union-Find graph algorithm. All mutual duplicates share the same cluster UUID.

## Database Indexes
Optimized for high-throughput filtering and deduplication blocking:
- `ix_leads_email`
- `ix_leads_phone_normalized`
- `ix_leads_lead_status`
- `ix_leads_contact_owner`
- `ix_leads_country`
- `ix_leads_dedup_group_id`

## Inter-Module Relationships
- **Deduplication Engine (`dedupe_service.py`)**: Uses `email`, `phone_normalized`, and company prefixes for candidate blocking and multi-signal scoring.
- **Source Extractor (`source_extractor.py`)**: Parses the `notes` column to populate `ai_source_channel` and `ai_source_detail`.
- **Form Ingestion (`ingest.py`)**: Enriches existing records by appending timestamps to `notes` and populating missing fields.
