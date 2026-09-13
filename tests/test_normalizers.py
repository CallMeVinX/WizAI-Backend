"""Unit tests for lead data normalizers."""

from datetime import datetime
from app.utils.normalizers import (
    normalize_status,
    normalize_country,
    normalize_phone,
    normalize_email,
    resolve_name,
    parse_date,
    normalize_company_for_dedup,
)


def test_normalize_status():
    assert normalize_status("New") == "new"
    assert normalize_status("NEW ") == "new"
    assert normalize_status(" Qualified") == "qualified"
    assert normalize_status("Closed Won") == "closed_won"
    assert normalize_status("closed lost") == "closed_lost"
    assert normalize_status(None) == "new"
    # Unrecognized status falls back to "new"
    assert normalize_status("unknown_status") == "new"


def test_normalize_country():
    assert normalize_country("italy") == "Italy"
    assert normalize_country("UAE") == "UAE"
    assert normalize_country("USA") == "USA"
    assert normalize_country("UK") == "United Kingdom"
    assert normalize_country("Germany ") == "Germany"
    assert normalize_country(None) is None


def test_normalize_phone():
    # Returns digits-only for deduplication blocking
    assert normalize_phone("+82 10-2476-5835") == "821024765835"
    assert normalize_phone("46704602383") == "46704602383"
    assert normalize_phone("+1 (323) 555-0192") == "13235550192"
    # Less than 7 digits is rejected
    assert normalize_phone("123") is None
    assert normalize_phone(None) is None


def test_normalize_email():
    assert normalize_email(" TEST@Example.com ") == "test@example.com"
    assert normalize_email("   ") is None
    assert normalize_email(None) is None


def test_resolve_name():
    # Both first and last provided
    first, last, full = resolve_name("Joon", "Diallo", None)
    assert first == "Joon"
    assert last == "Diallo"
    assert full == "Joon Diallo"

    # Only full name provided
    first, last, full = resolve_name(None, None, "Joon Diallo")
    assert first == "Joon"
    assert last == "Diallo"
    assert full == "Joon Diallo"

    # Single word full name
    first, last, full = resolve_name(None, None, "Cher")
    assert first == "Cher"
    assert last is None
    assert full == "Cher"


def test_parse_date():
    # ISO date
    d1 = parse_date("2026-05-18")
    assert d1.year == 2026 and d1.month == 5 and d1.day == 18

    # Slash format
    d2 = parse_date("5/27/2026")
    assert d2.year == 2026 and d2.month == 5 and d2.day == 27

    # ISO with timestamp
    d3 = parse_date("2026-04-05T00:00:00Z")
    assert d3.year == 2026 and d3.month == 4 and d3.day == 5


def test_parse_date_edge_cases():
    # ISO with timezone offset
    d_offset = parse_date("2026-04-05T07:00:00+07:00")
    assert d_offset is not None
    assert d_offset.year == 2026

    # European format (day first when day > 12)
    d_eu = parse_date("27/05/2026")
    assert d_eu is not None
    assert d_eu.day == 27 and d_eu.month == 5

    # Invalid date returns None gracefully
    assert parse_date("2026-02-31") is None
    assert parse_date("not-a-date") is None
    assert parse_date("   ") is None
    assert parse_date(None) is None


def test_normalize_company_for_dedup():
    # Strips corporate suffixes like 'Analytics', 'Pte', 'Ltd'
    assert normalize_company_for_dedup("Huang Analytics Pte. Ltd.") == "huang"
    # Strips '& Co' and sorts tokens
    assert normalize_company_for_dedup("Singh Logistics & Co") == "logistics singh"
    assert normalize_company_for_dedup("Singh Logistics Ltd") == "logistics singh"


def test_normalize_company_all_suffixes_fallback():
    # When all words are known suffixes, fallback to sorted original words
    res = normalize_company_for_dedup("Solutions Group Pte Ltd")
    assert "group" in res and "solutions" in res


def test_normalize_phone_extensions():
    # Strips extension suffixes cleanly
    assert normalize_phone("+1 555-123-4567 ext 102") == "15551234567"
    assert normalize_phone("+1 555-123-4567 x45") == "15551234567"
    assert normalize_phone("+1 555-123-4567 ext. 9") == "15551234567"


def test_resolve_name_edge_cases():
    # Honorific prefix stripping
    first, last, full = resolve_name(None, None, "Dr. John Smith")
    assert first == "John"
    assert last == "Smith"
    assert "Dr. John Smith" in full

    # Multi-word name splitting on last space (PRD heuristic)
    first2, last2, _ = resolve_name(None, None, "Mary Jane Watson")
    assert first2 == "Mary Jane"
    assert last2 == "Watson"

    # Whitespace cleanup
    first3, last3, _ = resolve_name("  Alan  ", "  Turing  ", None)
    assert first3 == "Alan"
    assert last3 == "Turing"

