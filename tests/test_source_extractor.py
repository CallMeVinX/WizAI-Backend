"""Unit tests for rule-based source extraction."""

from app.services.source_extractor import extract_source_rules, extract_source


def test_event_qr_code_extraction():
    note = "He scanned our QR code at the TechCrunch Disrupt booth"
    channel, detail = extract_source_rules(note)
    assert channel == "Event"
    assert "TechCrunch Disrupt" in detail
    assert "Booth QR Code" in detail


def test_event_booth_visit_extraction():
    note = "Spoke with them at our SaaStr Annual booth during the afternoon"
    channel, detail = extract_source_rules(note)
    assert channel == "Event"
    assert "SaaStr Annual" in detail


def test_paid_search_extraction():
    note = "Visited book-a-demo page after clicking a Google ad"
    channel, detail = extract_source_rules(note)
    assert channel == "Website"
    assert "Google Ads" in detail


def test_organic_search_extraction():
    note = "Googled us and landed on the pricing page before filling form"
    channel, detail = extract_source_rules(note)
    assert channel == "Organic Search"
    assert "pricing" in detail.lower()


def test_linkedin_extraction():
    note = "Saw our post about AI sales workflows and commented"
    channel, detail = extract_source_rules(note)
    assert channel == "LinkedIn"
    assert "AI sales workflows" in detail


def test_referral_extraction():
    note = "Referred by Maria Santos after an introductory meeting"
    channel, detail = extract_source_rules(note)
    assert channel == "Referral"
    assert "Maria Santos" in detail


def test_manual_sales_extraction():
    note = "Manual — added after inbound phone call regarding enterprise tier"
    channel, detail = extract_source_rules(note)
    assert channel == "Manual/Sales"
    assert "Inbound Phone Call" in detail


def test_empty_notes_fallback():
    channel, detail = extract_source("")
    assert channel == "Other"
    assert "No notes" in detail


def test_event_booth_during_precedence():
    """Verify 'booth during <Event>' is accurately extracted without producing 'the — Booth Visit'."""
    note = "Met at the booth during Mobile World Congress, said they'd follow up over email."
    channel, detail = extract_source_rules(note)
    assert channel == "Event"
    assert "Mobile World Congress" in detail
    assert "the — Booth" not in detail
    assert "Booth Visit" in detail


def test_organic_search_landing_page_with_period():
    """Verify landing page extraction cleanly terminates at period without leaking sales notes."""
    note = "Found us through organic google search then landed on the homepage. Connected, sending proposal."
    channel, detail = extract_source_rules(note)
    assert channel == "Organic Search"
    assert detail == "Organic Search → homepage"
    assert "Connected" not in detail


def test_referral_hyphenated_names():
    """Verify referral extraction supports hyphenated names (e.g. Min-jun Colombo, Diego Al-Farsi)."""
    note1 = "Referred by Min-jun Colombo, warm intro. Connected, sending proposal."
    channel1, detail1 = extract_source_rules(note1)
    assert channel1 == "Referral"
    assert detail1 == "Referred by Min-jun Colombo"

    note2 = "Referred by Diego Al-Farsi, warm intro."
    channel2, detail2 = extract_source_rules(note2)
    assert channel2 == "Referral"
    assert detail2 == "Referred by Diego Al-Farsi"


def test_website_form_no_trailing_dot():
    """Verify form submission detail cleanly removes trailing periods."""
    note = "Filled out the form on the contact page."
    channel, detail = extract_source_rules(note)
    assert channel == "Website"
    assert detail == "Form Submission — contact page"
    assert not detail.endswith(".")


def test_noisy_and_ambiguous_notes(monkeypatch):
    """Verify unclassifiable, noisy, or symbol-only notes fallback cleanly."""
    monkeypatch.setattr("app.services.source_extractor.call_gemini_json", lambda prompt: None)
    note = "Followed up on conversation, will touch base next quarter."
    channel, detail = extract_source(note)
    assert channel == "Other"
    assert "Could not determine source" in detail


def test_llm_source_extraction_success(monkeypatch):
    """Verify extract_source_llm parses valid structured JSON correctly."""
    monkeypatch.setattr(
        "app.services.source_extractor.call_gemini_json",
        lambda prompt: {"channel": "LinkedIn", "detail": "LinkedIn message from VP"}
    )
    res = extract_source("Some unstructured note about a chat on LinkedIn with VP")
    assert res == ("LinkedIn", "LinkedIn message from VP")


def test_llm_hallucinated_channel_coerced_to_other(monkeypatch):
    """Verify LLM hallucinated category outside VALID_CHANNELS is coerced to 'Other'."""
    monkeypatch.setattr(
        "app.services.source_extractor.call_gemini_json",
        lambda prompt: {"channel": "TikTok", "detail": "Saw viral video"}
    )
    res = extract_source("Watched viral video")
    assert res == ("Other", "Saw viral video")

