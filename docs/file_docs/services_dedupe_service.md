# Service Documentation: `app/services/dedupe_service.py`

## Overview
This module represents the core entity resolution engine, executing the 4-stage deduplication pipeline. It overcomes the computational bottleneck of $O(N^2)$ pairwise comparisons (evaluating ~2,000 leads would otherwise require ~2,100,000 comparisons).

## The 4-Stage Deduplication Pipeline

### Stage 1: Inverted Index Blocking (`generate_blocking_keys`, `build_candidate_pairs`)
Rather than comparing every record against every other record, leads are hashed into buckets using orthogonal blocking keys:
- Exact normalized email (`email_clean`).
- Clean phone suffix (last 10 digits for international matching).
- Corporate domain + last name initial (`domain:last_initial`).
- Normalized company prefix + first name initial (`company:first_initial`).
Only lead pairs sharing at least one common bucket key proceed to scoring, reducing millions of comparisons to a focused candidate set.

### Stage 2: Pairwise Multi-Signal Scoring (`score_pair`, `score_email`, etc.)
Surviving candidate pairs are evaluated against a composite score ($0.0 \le S \le 1.0$) using weighted signals:
- **Email (0.35)**: Exact match yields 1.0; matching domain with similar localpart yields 0.7.
- **Phone (0.25)**: Matching 10-digit normalized phone yields 0.8.
- **Name (0.20)**: Pure-Python Jaro-Winkler metric measures name distance ("Erik Jung" vs "Erick Jung").
- **Company (0.15)**: Strips legal corporate suffixes ("Ltd", "Inc", "Pte Ltd") and measures token overlap.
- **Notes Hint (0.05)**: Flags explicit "possible duplicate" mentions.
Pairs falling below `DEDUPE_CONFIDENCE_THRESHOLD` (default 0.6) are discarded. Built-in false-positive guards strictly prevent merging colleagues sharing an email domain who have distinct names.

### Stage 3: Selective LLM Adjudication (`verify_pair_llm`)
For borderline candidate pairs ($\text{confidence} \ge 0.80$), the engine dispatches a qualitative verification request to Google Gemini 3.6 Flash. This limits LLM calls to a maximum of 5 pairs per execution and caches results locally to avoid redundant API credit consumption.

### Stage 4: Transitive Graph Clustering (`group_pairs_with_union_find`)
Because duplication is transitive ($A \sim B \land B \sim C \implies \{A, B, C\}$), the engine applies a Disjoint-Set Union (Union-Find) data structure with path compression and union-by-rank. It merges connected candidate pairs into consolidated clusters and assigns a shared UUID `group_id` to both `dedupe_candidates` and `leads`.

## Ingestion Matching Helper
- **`find_best_match`**: Utilized by the form ingestion router (`POST /api/leads/ingest`). Instead of re-running the full dataset pipeline, it executes identical blocking and scoring logic for a single inbound submission, determining whether to enrich an existing record or provision a new lead.
