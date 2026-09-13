"""Google Gemini API client wrapper.

Provides a singleton client for executing structured LLM prompts with
automatic retries, markdown code-fence sanitization, and graceful offline fallback.
"""

import json
import logging
from typing import Optional
from google import genai
from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[genai.Client] = None


def get_gemini_client() -> Optional[genai.Client]:
    """Get or create a singleton Google Gemini client.
    
    Returns None if GEMINI_API_KEY is not configured or empty.
    """
    global _client
    if _client is None:
        settings = get_settings()
        api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        if not api_key or api_key in ("YOUR_API_KEY", "your_gemini_api_key_here"):
            return None
        _client = genai.Client(api_key=api_key)
    return _client


def call_gemini(prompt: str, max_retries: int = 2) -> Optional[str]:
    """Execute a content generation prompt via Google Gemini API.
    
    Args:
        prompt: Text prompt string.
        max_retries: Maximum number of retry attempts on transient network errors.
        
    Returns:
        Generated text string, or None if credentials are missing or attempts fail.
    """
    settings = get_settings()
    client = get_gemini_client()
    if client is None:
        logger.debug("Gemini client skipped: GEMINI_API_KEY is not configured")
        return None

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            logger.warning(f"Gemini API call failed (attempt {attempt + 1}): {e}")
            if attempt == max_retries:
                logger.error(f"Gemini API call failed after {max_retries + 1} attempts")
                return None

    return None


def call_gemini_json(prompt: str) -> Optional[dict]:
    """Call Gemini and parse the response as JSON.
    
    Strips markdown code fences if present.
    """
    raw = call_gemini(prompt)
    if not raw:
        return None

    # Strip markdown code fences
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse Gemini response as JSON: {raw[:200]}")
        return None
