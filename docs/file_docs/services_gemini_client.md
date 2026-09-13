# Service Documentation: `app/services/gemini_client.py`

## Overview
The `gemini_client.py` module wraps Google's official GenAI SDK (`google-genai`), providing a centralized interface for all Large Language Model (LLM) operations within WizzAI. It manages singleton client instantiation, JSON response sanitization, and graceful network fault tolerance.

## Functions & Mechanisms

### `get_gemini_client() -> Optional[genai.Client]`
Singleton design pattern that lazily initializes the `genai.Client` using `settings.GEMINI_API_KEY`. Safely returns `None` when the API key is unconfigured or empty, preventing unnecessary remote network attempts.

### `call_gemini(prompt: str, max_retries: int = 2) -> Optional[str]`
- Invokes the Gemini API using the model identifier defined in configuration (default: `gemini-3.6-flash`).
- Provides an automated retry loop up to `max_retries` times on transient network interruptions.
- Returns stripped response text, or `None` if all retries fail without bubbling unhandled exceptions up to callers.

### `call_gemini_json(prompt: str) -> Optional[dict]`
- Invokes `call_gemini()` and strips markdown code fences (e.g. ````json ... ````).
- Parses the sanitized string into a Python dictionary via `json.loads()`.
- Returns a valid JSON dictionary, or `None` if the model produces malformed or non-JSON output.

## Architectural Benefits
1. **Separation of Concerns**: Prevents SDK boilerplate and HTTP retry logic from leaking into domain business services like `dedupe_service.py` or `source_extractor.py`.
2. **Testability**: Facilitates hermetic unit testing and mocking without requiring live network access or paid API credentials.
3. **Operational Resilience**: Guarantees that external third-party outages or rate limits degrade gracefully without crashing core backend operations.
