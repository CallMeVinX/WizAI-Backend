"""AI-assisted source extraction from lead Notes.

Hybrid approach: rule-based pattern matching first (fast, free),
then Gemini LLM fallback for unmatched notes.
"""

import re
import logging
from typing import Optional
from app.services.gemini_client import call_gemini_json

logger = logging.getLogger(__name__)

VALID_CHANNELS = [
    "Website", "Event", "LinkedIn", "Organic Search",
    "Referral", "Manual/Sales", "Other",
]


PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Event patterns
    (
        re.compile(r"(?:scanned|scan)\s+(?:the\s+)?(?:our\s+)?QR\s+code\s+at\s+(?:the\s+|our\s+)?(.+?)(?:\s+booth)", re.IGNORECASE),
        "Event",
        "{0} — Booth QR Code",
    ),
    (
        re.compile(r"(?:He|She|They)?\s*scanned\s+(?:our\s+)?QR\s+code\s+at\s+(?:the\s+|our\s+)?(.+?)(?:\s+booth)", re.IGNORECASE),
        "Event",
        "{0} — Booth QR Code",
    ),
    (
        re.compile(r"Scanned\s+the\s+QR\s+code\s+at\s+our\s+(.+?)\s+booth", re.IGNORECASE),
        "Event",
        "{0} — Booth QR Code",
    ),
    (
        re.compile(r"(?:Met|Spoke)\s+(?:her|him|them|with\s+them)?\s*at\s+(?:the|our)\s+booth\s+during\s+(.+?)(?:,|\.|$)", re.IGNORECASE),
        "Event",
        "{0} — Booth Visit",
    ),
    (
        re.compile(r"(?:Met|Spoke)\s+(?:her|him|them|with\s+them)?\s*at\s+(?:the\s+|our\s+)?(.+?)\s+booth", re.IGNORECASE),
        "Event",
        "{0} — Booth Visit",
    ),
    (
        re.compile(r"booth\s+during\s+(.+?)(?:,|\.|$)", re.IGNORECASE),
        "Event",
        "{0} — Booth Visit",
    ),
    (
        re.compile(r"at\s+our\s+(.+?)\s+booth", re.IGNORECASE),
        "Event",
        "{0} — Booth Visit",
    ),

    # Paid Search / Google Ads
    (
        re.compile(r"(?:clicking|clicked)\s+a?\s*google\s+ad", re.IGNORECASE),
        "Website",
        "Paid Search — Google Ads",
    ),
    (
        re.compile(r"book-?a-?demo\s+page\s+after\s+clicking\s+a?\s*(?:google\s+)?ad", re.IGNORECASE),
        "Website",
        "Paid Search — Google Ads → Book a Demo",
    ),

    # Organic Search
    (
        re.compile(r"(?:Googled\s+us|organic\s+google\s+search|found\s+us\s+through\s+organic)", re.IGNORECASE),
        "Organic Search",
        None,  # will extract landing page below
    ),

    # LinkedIn
    (
        re.compile(r"[Ll]inkedin\s+dm\s+inbound", re.IGNORECASE),
        "LinkedIn",
        "LinkedIn DM Inbound",
    ),
    (
        re.compile(r"[Cc]onnected\s+on\s+[Ll]inked[Ii]n\s+after\s+commenting", re.IGNORECASE),
        "LinkedIn",
        "LinkedIn Post Comment",
    ),
    (
        re.compile(r"[Ss]aw\s+our\s+post\s+about\s+(.+?)(?:\s+and\s+commented|\.\s|$)", re.IGNORECASE),
        "LinkedIn",
        "LinkedIn — Post about {0}",
    ),

    # Referral
    (
        re.compile(r"[Rr]eferred\s+by\s+([A-Z][a-zA-Z'’-]+(?:\s+[A-Z][a-zA-Z'’-]+)*)", re.DOTALL),
        "Referral",
        "Referred by {0}",
    ),

    # Website / Form
    (
        re.compile(r"[Ff]illed\s+out\s+the\s+form\s+on\s+(?:the\s+)?(.+?)(?:\.\s|\.?$)", re.DOTALL),
        "Website",
        "Form Submission — {0}",
    ),
    (
        re.compile(r"book-?a-?demo\s+page", re.IGNORECASE),
        "Website",
        "Book a Demo Page",
    ),
    (
        re.compile(r"Booked\s+a\s+demo\s+via\s+the\s+(.+?)(?:\s+after|\.\s|$)", re.IGNORECASE),
        "Website",
        "Demo Booking via {0}",
    ),

    # Manual / Sales
    (
        re.compile(r"[Mm]anually\s+added\s+by\s+sales", re.IGNORECASE),
        "Manual/Sales",
        "Manually Added by Sales",
    ),
    (
        re.compile(r"[Mm]anual\s*[-–—]\s*added\s+after\s+inbound\s+phone\s+call", re.IGNORECASE),
        "Manual/Sales",
        "Inbound Phone Call",
    ),
    (
        re.compile(r"cold\s+outreach\s+list", re.IGNORECASE),
        "Manual/Sales",
        "Cold Outreach List",
    ),
    (
        re.compile(r"walked\s+into\s+our\s+office", re.IGNORECASE),
        "Manual/Sales",
        "Walk-in",
    ),
    (
        re.compile(r"reached\s+out\s+via\s+our\s+general\s+info@?\s*inbox", re.IGNORECASE),
        "Manual/Sales",
        "Inbound Email (info@ inbox)",
    ),
    (
        re.compile(r"Other\s*[-–—]\s*reached\s+out\s+via\s+our\s+general\s+info", re.IGNORECASE),
        "Manual/Sales",
        "Inbound Email (info@ inbox)",
    ),
    (
        re.compile(r"Other\s*[-–—]\s*walked\s+into\s+our\s+office", re.IGNORECASE),
        "Manual/Sales",
        "Walk-in",
    ),
    (
        re.compile(r"inbound\s+phone\s+call", re.IGNORECASE),
        "Manual/Sales",
        "Inbound Phone Call",
    ),
]

# Landing page extraction for Organic Search
LANDING_PAGE_PATTERN = re.compile(
    r"(?:landed\s+on|ended\s+up\s+on)\s+(?:the\s+)?(.+?)(?:\.|\s+(?:before|page|then)|$)",
    re.IGNORECASE,
)


def extract_source_rules(notes: Optional[str]) -> Optional[tuple[str, str]]:
    """Try to extract source channel and detail using rule-based patterns.
    
    Returns (channel, detail) or None if no pattern matches.
    """
    if not notes:
        return None

    for pattern, channel, detail_template in PATTERNS:
        match = pattern.search(notes)
        if match:
            if detail_template is None:
                # Special handling for Organic Search — extract landing page
                lp_match = LANDING_PAGE_PATTERN.search(notes)
                landing = lp_match.group(1).strip().rstrip(".,") if lp_match else "Unknown page"
                detail = f"Organic Search → {landing}"
            elif "{0}" in detail_template:
                try:
                    captured = match.group(1).strip().rstrip(".,")
                    detail = detail_template.format(captured)
                except (IndexError, AttributeError):
                    detail = detail_template.replace("{0}", "")
            else:
                detail = detail_template

            return channel, detail

    return None


def extract_source_llm(notes: str) -> Optional[tuple[str, str]]:
    """Use Gemini LLM to extract source from notes that didn't match rules.
    
    Returns (channel, detail) or None.
    """
    prompt = f"""Extract the lead acquisition source from this CRM note. 
Respond ONLY with a JSON object, no other text.

Note: "{notes}"

Categories (pick exactly one): Website, Event, LinkedIn, Organic Search, Referral, Manual/Sales, Other

Response format:
{{"channel": "<one of the categories>", "detail": "<specific detail about the source>"}}"""

    result = call_gemini_json(prompt)
    if result and "channel" in result:
        channel = result["channel"]
        detail = result.get("detail", "")
        # Validate channel
        if channel not in VALID_CHANNELS:
            channel = "Other"
        return channel, detail

    return None


def extract_source(notes: Optional[str]) -> tuple[str, str]:
    """Extract source channel and detail from notes.
    
    Uses rule-based matching first, falls back to LLM.
    Returns (channel, detail).
    """
    if not notes:
        return "Other", "No notes available"

    # Try rules first
    result = extract_source_rules(notes)
    if result:
        return result

    # Fallback to LLM
    result = extract_source_llm(notes)
    if result:
        return result

    return "Other", "Could not determine source"
