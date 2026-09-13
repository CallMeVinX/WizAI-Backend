# Utility Documentation: `app/utils/normalizers.py`

## Overview
The `normalizers.py` module contains pure, deterministic data-cleaning functions designed to handle the inconsistencies and formatting anomalies characteristic of legacy CRM exports (`leads_seed.csv`) and multi-channel inbound form payloads (`website_form_submissions.json`).

All functions are side-effect-free, highly performant, and execute in memory with zero external I/O or network overhead.

---

## Functions Reference

### `normalize_status(raw: Optional[str]) -> str`
Standardizes erratic lifecycle status values into a strict, validated enum representation.
- **Input Variations Handled**: Mixed casing (`"New"`, `"NEW"`, `"new"`), surrounding quotation marks (`"\"New\""`), and whitespace padding (`" New "`).
- **Canonical Mapping**: Converts space-separated or concatenated values (`"closed won"`, `"closedwon"`) to canonical database tokens (`"closed_won"`, `"closed_lost"`).
- **Default Fallback**: Returns `"new"` for `None`, empty strings, or unrecognized status entries.

### `normalize_phone(raw: Optional[str]) -> Optional[str]`
Extracts canonical digits-only phone numbers for deduplication blocking and indexing.
- **Extension Stripping**: Identifies and removes trailing phone extensions before digit extraction (e.g. `ext 102`, `x45`, `ext. 789`).
- **Sanitization**: Strips all non-digit formatting characters (`+`, `-`, `(`, `)`, spaces, dots).
- **Validation**: Requires a minimum length of 7 digits; inputs yielding fewer than 7 digits return `None` to eliminate corrupted fragments.
- **Examples**:
  - `"+1 (555) 019-2834 ext 102"` $\to$ `"15550192834"`
  - `"+82 10-2476-5835"` $\to$ `"821024765835"`

### `resolve_name(first_name: Optional[str], last_name: Optional[str], full_name: Optional[str]) -> tuple[Optional[str], Optional[str], str]`
Reconciles mixed name representations across legacy CRM records where some rows contain split `First Name` / `Last Name` while others contain only a combined `Full Name`.
- **Honorific Stripping**: Pre-cleans professional titles (`Dr.`, `Mr.`, `Mrs.`, `Ms.`, `Prof.`) using regex `HONORIFIC_PREFIXES`.
- **Right-Most Split Rule**: When only `Full Name` is provided, splits on the right-most whitespace boundary (`rsplit(None, 1)`). This ensures multi-word first names (e.g., *"Sarah Jane Smith"*) correctly yield `first_name="Sarah Jane"` and `last_name="Smith"`.
- **Synthesis**: If both `first_name` and `last_name` are present, computes a combined `full_name` (`"First Last"`).
- **Returns**: `(first_name, last_name, full_name)`.

### `parse_date(raw: Optional[str]) -> Optional[datetime]`
Flexibly parses heterogeneous date strings encountered across CRM exports into timezone-aware UTC `datetime` objects.
- **Evaluation Order**:
  1. ISO 8601 parsing via `datetime.fromisoformat()` (handles trailing `Z` and explicit timezone offsets like `+07:00`).
  2. Sequential trial against fallback format specifiers:
     - `"%Y-%m-%d"` (e.g., `2026-06-02`)
     - `"%m/%d/%Y"` (US standard, e.g., `6/4/2026`)
     - `"%d/%m/%Y"` (EU standard, e.g., `24/11/2026`)
     - `"%d-%m-%Y"`
     - `"%Y-%m-%dT%H:%M:%SZ"`
     - `"%Y-%m-%d %H:%M:%S"`
- **Fallback**: Gracefully returns `None` for unparseable dates without raising unhandled exceptions.

### `normalize_country(raw: Optional[str]) -> Optional[str]`
Standardizes country names using title casing with hardcoded overrides for sovereign acronyms.
- **Overrides**: `"uae"` $\to$ `"UAE"`, `"usa"` $\to$ `"USA"`, `"uk"` $\to$ `"United Kingdom"`.
- **General Rule**: Applies `.title()` casing (`"germany"` $\to$ `"Germany"`).

### `normalize_owner(raw: Optional[str]) -> Optional[str]`
Trims leading and trailing whitespace from sales representative assignment strings; returns `None` for blank entries.

### `normalize_email(raw: Optional[str]) -> Optional[str]`
Converts email addresses to lowercase and strips whitespace to ensure deterministic uniqueness checks and blocking key generation.

### `normalize_company_for_dedup(raw: Optional[str]) -> str`
Normalizes corporate names specifically for invariant deduplication blocking.
- **Punctuation Removal**: Replaces non-alphanumeric characters with whitespace.
- **Legal Suffix Stripping**: Removes 20+ corporate designations and common stop words (`ltd`, `inc`, `pte`, `co`, `gmbh`, `group`, `solutions`, `holdings`, `partners`, `digital`, `&`, `and`, `the`).
- **Lexicographical Token Sorting**: Sorts surviving words alphabetically (`"Singh Logistics & Co"` $\to$ `"logistics singh"`, `"Singh Logistics Ltd"` $\to$ `"logistics singh"`).
- **Safety Fallback**: If all tokens in a company name match suffix dictionaries (e.g., `"Solutions Group Pte Ltd"`), it falls back to the original tokens to prevent generating an empty string.

### `normalize_lifecycle(raw: Optional[str]) -> Optional[str]`
Standardizes CRM lifecycle stages (`"mql"` $\to$ `"Marketing Qualified Lead"`, `"sql"` $\to$ `"Sales Qualified Lead"`, `"lead"` $\to$ `"Lead"`).
