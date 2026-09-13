"""Core business logic and external integration services package."""

from app.services.lead_service import (
    get_leads,
    get_lead_by_id,
    update_lead,
    find_lead_by_email,
    find_lead_by_phone,
    get_distinct_values,
)
from app.services.dedupe_service import (
    run_dedupe_pipeline,
    find_best_match,
    score_pair,
    build_candidate_pairs,
    group_pairs_with_union_find,
)
from app.services.source_extractor import extract_source, extract_source_rules, extract_source_llm
from app.services.gemini_client import get_gemini_client, call_gemini, call_gemini_json
from app.services.csv_importer import import_csv

__all__ = [
    "get_leads",
    "get_lead_by_id",
    "update_lead",
    "find_lead_by_email",
    "find_lead_by_phone",
    "get_distinct_values",
    "run_dedupe_pipeline",
    "find_best_match",
    "score_pair",
    "build_candidate_pairs",
    "group_pairs_with_union_find",
    "extract_source",
    "extract_source_rules",
    "extract_source_llm",
    "get_gemini_client",
    "call_gemini",
    "call_gemini_json",
    "import_csv",
]
