"""Unit tests for pure Python similarity functions."""

from app.utils.similarity import jaro_similarity, jaro_winkler_similarity


def test_jaro_similarity_exact_match():
    assert jaro_similarity("hello", "hello") == 1.0
    assert jaro_similarity("", "") == 1.0


def test_jaro_similarity_empty():
    assert jaro_similarity("hello", "") == 0.0
    assert jaro_similarity("", "world") == 0.0


def test_jaro_winkler_similarity():
    # Names with common prefix
    sim = jaro_winkler_similarity("Martha", "Marhta")
    assert sim > 0.9

    # Completely different
    assert jaro_winkler_similarity("Alpha", "Omega") < 0.5

    # Company name matching
    assert jaro_winkler_similarity("Acme Corp", "Acme Corporation") > 0.8


def test_similarity_edge_cases():
    # Identical strings
    assert jaro_winkler_similarity("Google", "Google") == 1.0
    assert jaro_winkler_similarity("", "") == 1.0

    # Single character comparisons
    assert jaro_winkler_similarity("A", "A") == 1.0
    assert jaro_winkler_similarity("A", "B") == 0.0

    # Unicode / accented character similarity
    sim_unicode = jaro_winkler_similarity("Müller", "Muller")
    assert sim_unicode > 0.8

