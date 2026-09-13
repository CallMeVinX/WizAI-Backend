"""Unit tests for lead deduplication blocking, scoring, and Union-Find grouping.

Validates:
- Blocking key generation and inverted index filtering
- Exact and fuzzy duplicate multi-signal scoring
- False-positive resilience against collocated individuals with similar names
- True-positive entity resolution for normalized contact variations
- Union-Find transitive graph clustering
"""

from app.models.lead import Lead
from app.services.dedupe_service import (
    UnionFind,
    generate_blocking_keys,
    score_email,
    score_phone,
    score_name,
    score_company,
    score_pair,
    build_candidate_pairs,
    group_pairs_with_union_find,
)


def test_generate_blocking_keys():
    lead = Lead(
        id=1,
        first_name="Joon",
        last_name="Diallo",
        full_name="Joon Diallo",
        company_name="Huang Analytics Pte. Ltd.",
        email="joond@huanganalytics.co",
        phone_number="+82 10-2476-5835",
        phone_normalized="821024765835",
    )
    keys = generate_blocking_keys(lead)
    assert "email_exact" in keys
    assert "joond@huanganalytics.co" in keys["email_exact"]
    assert "phone_normalized" in keys
    assert "821024765835" in keys["phone_normalized"]
    assert "domain_lastname" in keys
    assert "company_firstname" in keys


def test_score_exact_duplicate():
    lead1 = Lead(
        id=1,
        first_name="Isabelle",
        last_name="Kapoor",
        full_name="Isabelle Kapoor",
        company_name="Kapoor Holdings Ltd",
        email="isabelle@kapoor.com",
        phone_number="+1 323-555-0192",
        phone_normalized="13235550192",
    )
    lead2 = Lead(
        id=2,
        first_name="Isabelle",
        last_name="Kapoor",
        full_name="Isabelle Kapoor",
        company_name="Kapoor Holdings Ltd",
        email="isabelle@kapoor.com",
        phone_number="+1 323-555-0192",
        phone_normalized="13235550192",
    )
    conf, scores = score_pair(lead1, lead2)
    assert conf >= 0.9
    assert scores["email"] == 1.0
    assert scores["name"] == 1.0
    assert scores["phone"] == 1.0


def test_score_subtle_duplicate():
    # Subtle duplicate with slight email change & company suffix change
    lead1 = Lead(
        id=1,
        first_name="Joon",
        last_name="Diallo",
        full_name="Joon Diallo",
        company_name="Huang Analytics Pte. Ltd.",
        email="joond@huanganalytics.co",
        phone_number="+82 10-2476-5835",
        phone_normalized="821024765835",
    )
    lead2 = Lead(
        id=2,
        first_name="J.",
        last_name="Diallo",
        full_name="J. Diallo",
        company_name="Huang Analytics & Co",
        email="joond@huanganalytics.co",
        phone_number="+82 10-2476-5835",
        phone_normalized="821024765835",
    )
    conf, scores = score_pair(lead1, lead2)
    assert conf >= 0.7
    assert scores["email"] == 1.0
    assert scores["phone"] == 1.0
    assert scores["company"] == 1.0


def test_score_different_leads():
    lead1 = Lead(
        id=1,
        first_name="Alice",
        last_name="Smith",
        full_name="Alice Smith",
        company_name="Acme Corp",
        email="alice@acme.com",
        phone_number="1112223333",
        phone_normalized="1112223333",
    )
    lead2 = Lead(
        id=2,
        first_name="Bob",
        last_name="Jones",
        full_name="Bob Jones",
        company_name="Globex Inc",
        email="bob@globex.com",
        phone_number="9998887777",
        phone_normalized="9998887777",
    )
    conf, scores = score_pair(lead1, lead2)
    assert conf < 0.2


# ── False-Positive Resilience Tests ──────────────────────────────────────────

def test_false_positive_same_company_similar_name():
    """Verify distinct individuals at the same company with similar names are not merged.
    
    Ensures that company match alone does not overpower distinct email and phone signals.
    """
    # Person A: Arun Kapoor at Kapoor Holdings
    lead_a = Lead(
        id=100,
        first_name="Arun",
        last_name="Kapoor",
        full_name="Arun Kapoor",
        company_name="Kapoor Holdings Ltd",
        email="arun.kapoor@kapoorholdings.com",
        phone_number="+91 98765 43210",
        phone_normalized="919876543210",
    )
    # Person B: Arjun Kapoor at Kapoor Holdings — different person!
    lead_b = Lead(
        id=101,
        first_name="Arjun",
        last_name="Kapoor",
        full_name="Arjun Kapoor",
        company_name="Kapoor Holdings Ltd",
        email="arjun.kapoor@kapoorholdings.com",
        phone_number="+91 91234 56789",
        phone_normalized="919123456789",
    )
    conf, scores = score_pair(lead_a, lead_b)

    # Company matches (same normalized company), name is superficially similar,
    # but email localpart and phone are different → must stay BELOW threshold.
    assert conf < 0.6, (
        f"False positive! Arun Kapoor ≠ Arjun Kapoor scored {conf:.3f} "
        f"(threshold 0.6). Scores: {scores}"
    )


def test_false_positive_same_company_different_first_name():
    """Two colleagues at the same company with different first names and same last name.
    
    Must NOT be grouped as duplicates even though company and last name match.
    """
    lead_a = Lead(
        id=200,
        first_name="Lina",
        last_name="Singh",
        full_name="Lina Singh",
        company_name="Singh Logistics & Co",
        email="lina@singhlogistics.com",
        phone_number="+65 8123 4567",
        phone_normalized="6581234567",
    )
    lead_b = Lead(
        id=201,
        first_name="Rajiv",
        last_name="Singh",
        full_name="Rajiv Singh",
        company_name="Singh Logistics Ltd",
        email="rajiv@singhlogistics.com",
        phone_number="+65 9876 5432",
        phone_normalized="6598765432",
    )
    conf, scores = score_pair(lead_a, lead_b)

    assert conf < 0.6, (
        f"False positive! Lina Singh ≠ Rajiv Singh scored {conf:.3f} "
        f"(threshold 0.6). Scores: {scores}"
    )


# ── True-Positive Entity Resolution Tests ────────────────────────────────────

def test_true_positive_seed_data_duplicate():
    """Verify entity resolution accurately detects realistic duplicate profiles.
    
    Covers name variations (initial vs full first name), identical email,
    and phone normalization matches.
    """
    lead1 = Lead(
        id=300,
        first_name="Isabelle",
        last_name="Chen",
        full_name="Isabelle Chen",
        company_name="Chen Technologies Pte Ltd",
        email="isabelle.chen@chentech.sg",
        phone_number="+65 9123-4567",
        phone_normalized="6591234567",
        notes="Possible duplicate of record #301",
    )
    lead2 = Lead(
        id=301,
        first_name="I.",
        last_name="Chen",
        full_name="I. Chen",
        company_name="Chen Technologies",
        email="isabelle.chen@chentech.sg",
        phone_number="65-91234567",
        phone_normalized="6591234567",
        notes="",
    )
    conf, scores = score_pair(lead1, lead2)

    assert conf >= 0.6, (
        f"True positive missed! Isabelle Chen / I. Chen scored only {conf:.3f}. "
        f"Scores: {scores}"
    )
    assert scores["email"] == 1.0, "Same email should score 1.0"
    assert scores["phone"] >= 0.8, "Same phone digits should score >= 0.8"


def test_true_positive_phone_and_company_match():
    """Same person, slightly different email but same phone + company."""
    lead1 = Lead(
        id=400,
        first_name="David",
        last_name="Müller",
        full_name="David Müller",
        company_name="Müller Consulting GmbH",
        email="d.mueller@muellerconsulting.de",
        phone_number="+49 170 1234567",
        phone_normalized="491701234567",
    )
    lead2 = Lead(
        id=401,
        first_name="David",
        last_name="Müller",
        full_name="David Müller",
        company_name="Mueller Consulting",
        email="david.mueller@muellerconsulting.de",
        phone_number="+49-170-1234567",
        phone_normalized="491701234567",
    )
    conf, scores = score_pair(lead1, lead2)

    assert conf >= 0.6, (
        f"True positive missed! David Müller scored only {conf:.3f}. "
        f"Scores: {scores}"
    )


# Union-Find Tests

def test_union_find_basic():
    """Union-Find correctly merges elements and finds roots."""
    uf = UnionFind()
    uf.union(1, 2)
    uf.union(3, 4)
    uf.union(2, 3)  # Now 1,2,3,4 should be in one group

    assert uf.find(1) == uf.find(4), "Transitive union should merge all four"
    groups = uf.get_groups()
    assert len(groups) == 1
    group = list(groups.values())[0]
    assert sorted(group) == [1, 2, 3, 4]


def test_union_find_separate_groups():
    """Union-Find keeps unrelated pairs in separate groups."""
    uf = UnionFind()
    uf.union(1, 2)
    uf.union(3, 4)

    assert uf.find(1) != uf.find(3), "Separate pairs should stay separate"
    groups = uf.get_groups()
    assert len(groups) == 2


def test_group_pairs_with_union_find_transitive():
    """group_pairs_with_union_find merges A~B, B~C into one cluster."""
    pairs = [
        {"lead_id_1": 10, "lead_id_2": 20, "confidence": 0.85,
         "match_reasons": {}, "explanation": "test"},
        {"lead_id_1": 20, "lead_id_2": 30, "confidence": 0.75,
         "match_reasons": {}, "explanation": "test"},
    ]
    tagged_pairs, clusters = group_pairs_with_union_find(pairs)

    # Should produce exactly 1 cluster with IDs [10, 20, 30]
    assert len(clusters) == 1
    cluster_members = list(clusters.values())[0]
    assert sorted(cluster_members) == [10, 20, 30]

    # Both pairs should share the same group_id
    assert tagged_pairs[0]["group_id"] == tagged_pairs[1]["group_id"]


def test_group_pairs_independent_pairs():
    """Independent pairs (no shared lead_id) stay in separate clusters."""
    pairs = [
        {"lead_id_1": 10, "lead_id_2": 20, "confidence": 0.9,
         "match_reasons": {}, "explanation": "pair A"},
        {"lead_id_1": 30, "lead_id_2": 40, "confidence": 0.8,
         "match_reasons": {}, "explanation": "pair B"},
    ]
    tagged_pairs, clusters = group_pairs_with_union_find(pairs)

    assert len(clusters) == 2
    assert tagged_pairs[0]["group_id"] != tagged_pairs[1]["group_id"]


def test_false_positive_family_members_shared_phone():
    """Verify family members with same phone & last name but different first name and work are not merged."""
    lead_father = Lead(
        id=501,
        first_name="David",
        last_name="Miller",
        full_name="David Miller",
        company_name="Miller Logistics",
        email="david.miller@millerlogistics.com",
        phone_number="+1 555-987-6543",
        phone_normalized="15559876543",
    )
    lead_daughter = Lead(
        id=502,
        first_name="Sarah",
        last_name="Miller",
        full_name="Sarah Miller",
        company_name="BioTech Solutions",
        email="sarah.m@biotechsolutions.org",
        phone_number="+1 555-987-6543",  # shared household / office line
        phone_normalized="15559876543",
    )
    conf, scores = score_pair(lead_father, lead_daughter)
    assert conf < 0.6, (
        f"Family members with shared phone incorrectly scored {conf:.3f} >= 0.6! Scores: {scores}"
    )


def test_sparse_leads_handling():
    """Verify leads with sparse/minimal attributes do not produce false positive merges."""
    lead_a = Lead(
        id=601,
        email="contact@company.com",
    )
    lead_b = Lead(
        id=602,
        email="sales@company.com",
    )
    conf, scores = score_pair(lead_a, lead_b)
    assert conf < 0.6


def test_union_find_cyclic_clustering():
    """Verify Union-Find correctly handles cyclic duplicate graphs (A~B, B~C, C~A)."""
    pairs = [
        {"lead_id_1": 1, "lead_id_2": 2, "confidence": 0.85, "match_reasons": {}, "explanation": ""},
        {"lead_id_1": 2, "lead_id_2": 3, "confidence": 0.80, "match_reasons": {}, "explanation": ""},
        {"lead_id_1": 1, "lead_id_2": 3, "confidence": 0.82, "match_reasons": {}, "explanation": ""},
    ]
    tagged_pairs, clusters = group_pairs_with_union_find(pairs)
    assert len(clusters) == 1
    assert list(clusters.values())[0] == [1, 2, 3]
    # All pairs tagged with identical group_id
    assert tagged_pairs[0]["group_id"] == tagged_pairs[1]["group_id"] == tagged_pairs[2]["group_id"]


