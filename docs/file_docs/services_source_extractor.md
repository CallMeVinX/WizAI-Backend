# Service Documentation: `app/services/source_extractor.py`

## Overview
This module parses unstructured sales notes to extract structured lead acquisition sources (e.g., Website, Event, Referral) alongside granular channel details. Because CRM `notes` frequently contain conversational, noisy text (such as *"Met him at the SFF booth, scanned our QR code"*), this service structures attribution data for reporting.

## The Dual-Tier "Fast-Path + LLM Fallback" Architecture
Combines deterministic regex matching for high throughput and zero inference cost with an LLM fallback for ambiguous text, maintaining high recall and precision.

### 1. The Fast-Path (Deterministic Regex Engine)
Implemented in `extract_source_rules`. Running LLM inference over thousands of rows incurs latency and cost. To circumvent this, the service evaluates a comprehensive catalog of pre-compiled regular expressions in `PATTERNS`:
- Event booth visits & QR code scans: `"Met him at the (...) booth"` $\to$ channel: `Event`.
- Search & Paid Advertising: `"organic google search"`, `"clicked a google ad"` $\to$ channel: `Organic Search` or `Website`.
- Word-of-mouth recommendations: `"Referred by (Name)"` $\to$ channel: `Referral`.
- Inbound demo requests and direct LinkedIn outreach.
When a pattern matches, groups are extracted and formatted into structured channel and detail attributes in $< 0.1\text{ ms}$ with zero API calls. This deterministic pass resolves over 85% of real-world notes in the seed dataset.

### 2. The LLM Fallback (AI Extraction)
Implemented in `extract_source_llm`.
When notes contain complex, narrative, or multilingual phrasing that fails regex matching, the text is dispatched to Google Gemini 3.6 Flash.
The model is prompted with strict JSON schema instructions (`{"channel": "...", "detail": "..."}`). Returned channels are validated against `VALID_CHANNELS`; unrecognized values gracefully default to `"Other"`.

## Service Integration
The extraction service (`extract_source`) is invoked by:
- `routers/ingest.py`: Automatically runs on newly ingested website form submissions.
- `routers/leads.py`: Exposed via the `POST /api/leads/extract-source` endpoint for ad-hoc and batch extraction.
- `seed.py`: Bulk initialization utility for attribution tagging across historical lead exports.
