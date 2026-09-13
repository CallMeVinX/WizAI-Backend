"""Data normalization utilities for cleaning messy CRM data."""

import re
from datetime import datetime, timezone
from typing import Optional


# ── Lead Status Normalization ──────────────────────────────────────────────

VALID_STATUSES = {
    "new", "qualified", "connected", "contacted",
    "opportunity", "closed_won", "closed_lost",
}

STATUS_MAP = {
    "closed won": "closed_won",
    "closedwon": "closed_won",
    "closed lost": "closed_lost",
    "closedlost": "closed_lost",
}


def normalize_status(raw: Optional[str]) -> str:
    """Normalize lead status to a clean enum value.
    
    Handles: mixed case, leading/trailing whitespace, quoted values,
    and 'Closed Won'/'Closed Lost' → 'closed_won'/'closed_lost'.
    """
    if not raw:
        return "new"
    cleaned = raw.strip().strip('"').strip().lower()
    if cleaned in STATUS_MAP:
        return STATUS_MAP[cleaned]
    if cleaned in VALID_STATUSES:
        return cleaned
    return "new"


# ── Phone Normalization ───────────────────────────────────────────────────

def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Extract digits-only version of phone number for dedup blocking.
    
    Handles extensions like 'ext 102' or 'x45':
    '+82 10-2476-5835' → '821024765835'
    '+1 555-123-4567 ext 102' → '15551234567'
    """
    if not raw:
        return None
    # Strip extension suffixes first (e.g. ext 123, x456, ext. 789)
    cleaned = re.sub(r"(?i)\s*(?:ext|x|ext\.)\s*\d+$", "", raw.strip())
    digits = re.sub(r"[^\d]", "", cleaned)
    return digits if len(digits) >= 7 else None


# ── Name Resolution ──────────────────────────────────────────────────────

HONORIFIC_PREFIXES = re.compile(r"^(?:dr|mr|mrs|ms|prof)\.?\s+", re.IGNORECASE)


def resolve_name(
    first_name: Optional[str],
    last_name: Optional[str],
    full_name: Optional[str],
) -> tuple[Optional[str], Optional[str], str]:
    """Resolve name fields into consistent first, last, full name.
    
    Returns (first_name, last_name, full_name).
    Per PRD: If Full Name is present but First/Last are empty → split on last space.
    If First/Last are present → compute Full Name.
    Handles honorific prefixes (Dr., Mr., Ms., Prof.).
    """
    first = first_name.strip() if first_name and first_name.strip() else None
    last = last_name.strip() if last_name and last_name.strip() else None
    full = full_name.strip() if full_name and full_name.strip() else None

    if first and last:
        computed_full = f"{first} {last}"
        return first, last, full or computed_full

    if full and not first and not last:
        # Strip honorific prefixes for cleaner first/last extraction
        cleaned_for_split = HONORIFIC_PREFIXES.sub("", full).strip()
        parts = cleaned_full = cleaned_for_split.rsplit(None, 1)
        first = parts[0] if len(parts) >= 1 else None
        last = parts[1] if len(parts) >= 2 else None
        return first, last, full

    if first and not last:
        return first, None, full or first
    if last and not first:
        return None, last, full or last

    return first, last, full or ""


# ── Date Parsing ─────────────────────────────────────────────────────────

DATE_FORMATS = [
    "%Y-%m-%d",             # 2026-05-18
    "%m/%d/%Y",             # 5/27/2026 (US)
    "%d/%m/%Y",             # 27/5/2026 (EU fallback)
    "%d-%m-%Y",             # 27-05-2026
    "%Y-%m-%dT%H:%M:%SZ",  # 2026-04-05T00:00:00Z
    "%Y-%m-%d %H:%M:%S",   # 2026-04-05 00:00:00
]


def parse_date(raw: Optional[str]) -> Optional[datetime]:
    """Parse date from multiple formats in the CRM export and submissions.
    
    Handles: '2026-05-18', '5/27/2026', '2026-04-05T00:00:00Z', offsets (+07:00),
    and European date fallbacks.
    """
    if not raw:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None

    # Try ISO fromisoformat first (handles Z and timezone offsets)
    try:
        iso_cleaned = cleaned.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass

    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


# ── Country Normalization ────────────────────────────────────────────────

COUNTRY_SPECIAL_CASES = {
    "uae": "UAE",
    "usa": "USA",
    "uk": "United Kingdom",
}


def normalize_country(raw: Optional[str]) -> Optional[str]:
    """Normalize country name: title case with special cases.
    
    'italy' → 'Italy', 'UAE' → 'UAE'
    """
    if not raw:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    lower = cleaned.lower()
    if lower in COUNTRY_SPECIAL_CASES:
        return COUNTRY_SPECIAL_CASES[lower]
    return cleaned.title() if cleaned != cleaned.title() else cleaned


# ── Contact Owner Normalization ──────────────────────────────────────────

def normalize_owner(raw: Optional[str]) -> Optional[str]:
    """Strip trailing/leading whitespace from contact owner."""
    if not raw:
        return None
    cleaned = raw.strip()
    return cleaned if cleaned else None


# ── Email Normalization ──────────────────────────────────────────────────

def normalize_email(raw: Optional[str]) -> Optional[str]:
    """Lowercase and strip email."""
    if not raw:
        return None
    cleaned = raw.strip().lower()
    return cleaned if cleaned else None


# ── Company Normalization (for dedup blocking) ───────────────────────────

COMPANY_SUFFIXES = {
    "ltd", "inc", "pte", "co", "co.", "gmbh", "ab", "ltda",
    "holdings", "partners", "studio", "group", "solutions",
    "trading", "freight", "retail", "consulting", "robotics",
    "analytics", "ventures", "digital", "sons", "bros",
    "&", "and", "the",
}


def normalize_company_for_dedup(raw: Optional[str]) -> str:
    """Normalize company name for dedup blocking.
    
    Remove legal suffixes, common words, punctuation → sort remaining words.
    'Singh Logistics & Co' → 'logistics singh'
    'Singh Logistics Ltd' → 'logistics singh'
    """
    if not raw:
        return ""
    cleaned = raw.strip().lower()
    # Remove punctuation except alphanumeric and spaces
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    words = cleaned.split()
    # Remove common suffixes/filler words
    filtered = [w for w in words if w not in COMPANY_SUFFIXES]
    if not filtered:
        filtered = words  # fallback if all words were suffixes
    filtered.sort()
    return " ".join(filtered)


# ── Lifecycle Stage Normalization ────────────────────────────────────────

LIFECYCLE_MAP = {
    "lead": "Lead",
    "marketing qualified lead": "Marketing Qualified Lead",
    "mql": "Marketing Qualified Lead",
    "sales qualified lead": "Sales Qualified Lead",
    "sql": "Sales Qualified Lead",
    "opportunity": "Opportunity",
    "customer": "Customer",
    "other": "Other",
}


def normalize_lifecycle(raw: Optional[str]) -> Optional[str]:
    """Normalize lifecycle stage."""
    if not raw:
        return None
    cleaned = raw.strip().lower()
    return LIFECYCLE_MAP.get(cleaned, raw.strip())
