"""AI-assisted lead deduplication pipeline.

4-stage pipeline:
1. Blocking: Inverted index candidate pair generation via normalized keys
2. Scoring: Multi-signal weighted scoring (Jaro-Winkler, phone digits, domain guards)
3. AI Adjudication: Google Gemini verification for borderline candidates
4. Union-Find Grouping: Transitive disjoint-set clustering into stable entity UUIDs
"""

import logging
import uuid
from collections import defaultdict
from typing import Optional
from app.utils.similarity import jaro_winkler_similarity
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.dedupe import DedupeCandidate
from app.utils.normalizers import normalize_company_for_dedup, normalize_phone
from app.services.gemini_client import call_gemini_json
from app.config import get_settings

logger = logging.getLogger(__name__)


# Union-Find Data Structure

class UnionFind:
    """Disjoint-set (Union-Find) with path compression and union by rank.
    
    Used to group transitive duplicate pairs into clusters:
    if A~B and B~C, all three belong to the same cluster.
    """

    def __init__(self):
        self.parent: dict[int, int] = {}
        self.rank: dict[int, int] = {}

    def find(self, x: int) -> int:
        """Find root with path compression."""
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> None:
        """Union by rank."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1

    def get_groups(self) -> dict[int, list[int]]:
        """Return {root: [members]} for all groups with >1 member."""
        groups: dict[int, list[int]] = defaultdict(list)
        for x in self.parent:
            groups[self.find(x)].append(x)
        return {k: sorted(v) for k, v in groups.items() if len(v) > 1}


# Stage 1: Blocking

def generate_blocking_keys(lead: Lead) -> dict[str, list[str]]:
    """Generate multiple blocking keys for a lead.
    
    Returns dict of {key_type: [key_values]}.
    A lead can produce multiple keys — any shared key between
    two leads makes them a candidate pair.
    """
    keys: dict[str, list[str]] = defaultdict(list)

    # Key 1: Exact email
    if lead.email:
        email = lead.email.strip().lower()
        keys["email_exact"].append(email)

    # Key 2: Normalized phone (digits only)
    phone_norm = lead.phone_normalized or normalize_phone(lead.phone_number)
    if phone_norm and len(phone_norm) >= 7:
        keys["phone_normalized"].append(phone_norm)
        # Also try last 10 digits for international format matching
        if len(phone_norm) >= 10:
            keys["phone_suffix_10"].append(phone_norm[-10:])

    # Key 3: Email domain + last name initial
    if lead.email and "@" in lead.email:
        domain = lead.email.split("@")[1].lower()
        last = (lead.last_name or "").strip().lower()[:3]
        if last and len(last) >= 2:
            keys["domain_lastname"].append(f"{domain}|{last}")

    # Key 4: Normalized company + first name prefix
    company_norm = normalize_company_for_dedup(lead.company_name)
    first = (lead.first_name or "").strip().lower()[:3]
    if company_norm and first and len(first) >= 2:
        keys["company_firstname"].append(f"{company_norm}|{first}")

    return keys


def build_candidate_pairs(leads: list[Lead]) -> set[tuple[int, int]]:
    """Build candidate pairs using blocking keys.
    
    For each blocking key, all leads sharing that key are candidate pairs.
    Returns set of (lead_id_1, lead_id_2) tuples where id_1 < id_2.
    """
    # Inverted index: key → list of lead IDs
    inverted: dict[str, list[int]] = defaultdict(list)

    for lead in leads:
        keys = generate_blocking_keys(lead)
        for key_type, key_values in keys.items():
            for kv in key_values:
                full_key = f"{key_type}:{kv}"
                inverted[full_key].append(lead.id)

    # Generate pairs from each bucket
    pairs: set[tuple[int, int]] = set()
    for key, lead_ids in inverted.items():
        if len(lead_ids) < 2:
            continue
        # Skip buckets that are too large (likely noise)
        if len(lead_ids) > 50:
            logger.warning(f"Skipping large blocking bucket {key}: {len(lead_ids)} leads")
            continue
        for i in range(len(lead_ids)):
            for j in range(i + 1, len(lead_ids)):
                pair = (min(lead_ids[i], lead_ids[j]), max(lead_ids[i], lead_ids[j]))
                pairs.add(pair)

    logger.info(f"Blocking generated {len(pairs)} candidate pairs from {len(leads)} leads")
    return pairs


# Stage 2: Pairwise Scoring

def score_email(lead1: Lead, lead2: Lead) -> float:
    """Score email similarity between two leads."""
    e1 = (lead1.email or "").strip().lower()
    e2 = (lead2.email or "").strip().lower()

    if not e1 or not e2:
        return 0.0

    # Exact match
    if e1 == e2:
        return 1.0

    # Same domain
    d1 = e1.split("@")[1] if "@" in e1 else ""
    d2 = e2.split("@")[1] if "@" in e2 else ""

    local1 = e1.split("@")[0] if "@" in e1 else e1
    local2 = e2.split("@")[0] if "@" in e2 else e2

    if d1 == d2:
        # Same domain — check localpart similarity
        sim = jaro_winkler_similarity(local1, local2)
        if sim >= 0.8:
            return 0.7
        return 0.3

    return 0.0


def score_phone(lead1: Lead, lead2: Lead) -> float:
    """Score phone similarity between two leads."""
    p1 = lead1.phone_normalized or normalize_phone(lead1.phone_number)
    p2 = lead2.phone_normalized or normalize_phone(lead2.phone_number)

    if not p1 or not p2:
        return 0.0

    # Exact digits match
    if p1 == p2:
        return 1.0

    # Check suffix match (last 10 digits — handles country code differences)
    if len(p1) >= 10 and len(p2) >= 10:
        if p1[-10:] == p2[-10:]:
            return 0.8

    return 0.0


def score_name(lead1: Lead, lead2: Lead) -> float:
    """Score name similarity between two leads."""
    name1 = (lead1.full_name or "").strip().lower()
    name2 = (lead2.full_name or "").strip().lower()

    if not name1 or not name2:
        return 0.0

    # Exact match
    if name1 == name2:
        return 1.0

    # Jaro-Winkler similarity
    sim = jaro_winkler_similarity(name1, name2)
    if sim >= 0.85:
        return sim

    # Handle initial matching: "J. Diallo" ↔ "Joon Diallo"
    first1 = (lead1.first_name or "").strip().lower()
    first2 = (lead2.first_name or "").strip().lower()
    last1 = (lead1.last_name or "").strip().lower()
    last2 = (lead2.last_name or "").strip().lower()

    if last1 and last2 and last1 == last2:
        if first1 and first2:
            if first1[0] == first2[0]:
                return 0.6
        elif first1 or first2:
            # One has initial, other has full name
            short = first1 if len(first1) < len(first2) else first2
            long = first2 if len(first1) < len(first2) else first1
            if short and long and short[0] == long[0]:
                return 0.5

    return max(sim, 0.0)


def score_company(lead1: Lead, lead2: Lead) -> float:
    """Score company similarity between two leads."""
    c1 = normalize_company_for_dedup(lead1.company_name)
    c2 = normalize_company_for_dedup(lead2.company_name)

    if not c1 or not c2:
        return 0.0

    if c1 == c2:
        return 1.0

    sim = jaro_winkler_similarity(c1, c2)
    if sim >= 0.85:
        return sim

    # Check if one contains the other (subset matching)
    words1 = set(c1.split())
    words2 = set(c2.split())
    if words1 and words2:
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        if overlap >= 0.6:
            return max(overlap, sim)

    return max(sim - 0.3, 0.0)  # penalize low similarity


def score_notes_hint(lead1: Lead, lead2: Lead) -> float:
    """Check if notes contain 'possible duplicate' hint."""
    for notes in [lead1.notes, lead2.notes]:
        if notes and "possible duplicate" in notes.lower():
            return 1.0
    return 0.0


# Weight configuration
WEIGHTS = {
    "email": 0.35,
    "phone": 0.25,
    "name": 0.20,
    "company": 0.15,
    "notes_hint": 0.05,
}


def score_pair(lead1: Lead, lead2: Lead) -> tuple[float, dict[str, float]]:
    """Calculate weighted confidence score for a candidate pair.
    
    Returns (confidence, {signal: score}).
    """
    scores = {
        "email": score_email(lead1, lead2),
        "phone": score_phone(lead1, lead2),
        "name": score_name(lead1, lead2),
        "company": score_company(lead1, lead2),
        "notes_hint": score_notes_hint(lead1, lead2),
    }

    confidence = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return confidence, scores


# Stage 3: (Optional) LLM Verification

def verify_pair_llm(lead1: Lead, lead2: Lead) -> Optional[dict]:
    """Use Gemini to verify if a high-confidence pair is truly duplicate.
    
    Returns {"is_duplicate": bool, "confidence": float, "explanation": str}
    """
    prompt = f"""Analyze these two CRM lead records and determine if they represent the same person.
Respond ONLY with a JSON object.

Lead A:
- Name: {lead1.full_name}
- Email: {lead1.email}
- Phone: {lead1.phone_number}
- Company: {lead1.company_name}
- Job Title: {lead1.job_title or 'N/A'}
- Notes: {(lead1.notes or '')[:200]}

Lead B:
- Name: {lead2.full_name}
- Email: {lead2.email}
- Phone: {lead2.phone_number}
- Company: {lead2.company_name}
- Job Title: {lead2.job_title or 'N/A'}
- Notes: {(lead2.notes or '')[:200]}

Response format:
{{"is_duplicate": true/false, "confidence": 0.0-1.0, "explanation": "brief explanation"}}"""

    return call_gemini_json(prompt)


def generate_explanation(scores: dict[str, float], lead1: Lead, lead2: Lead) -> str:
    """Generate a human-readable explanation for a match."""
    parts = []

    if scores["email"] >= 1.0:
        parts.append(f"Exact email match ({lead1.email})")
    elif scores["email"] >= 0.5:
        parts.append(f"Similar email (same domain)")

    if scores["phone"] >= 1.0:
        parts.append("Exact phone match")
    elif scores["phone"] >= 0.7:
        parts.append("Phone digits match (format difference)")

    if scores["name"] >= 0.85:
        parts.append(f"Name very similar ({lead1.full_name} ↔ {lead2.full_name})")
    elif scores["name"] >= 0.5:
        parts.append(f"Name partially matches ({lead1.full_name} ↔ {lead2.full_name})")

    if scores["company"] >= 0.85:
        parts.append(f"Same company ({lead1.company_name} ≈ {lead2.company_name})")

    if scores["notes_hint"] >= 1.0:
        parts.append("Notes contain 'possible duplicate' flag")

    return "; ".join(parts) if parts else "Multiple weak signals"


# Stage 4: Union-Find Grouping

def group_pairs_with_union_find(
    scored_pairs: list[dict],
) -> tuple[list[dict], dict[str, list[int]]]:
    """Apply Union-Find to group transitive duplicate pairs into clusters.
    
    If A~B and B~C, all three end up in the same cluster.
    
    Returns:
        - scored_pairs with 'group_id' added to each pair
        - clusters: {group_id: [lead_id_1, lead_id_2, ...]}
    """
    uf = UnionFind()

    # Union all pairs
    for pair in scored_pairs:
        uf.union(pair["lead_id_1"], pair["lead_id_2"])

    # Assign stable group IDs (UUID based on root)
    root_to_group_id: dict[int, str] = {}
    groups = uf.get_groups()
    for root, members in groups.items():
        root_to_group_id[root] = str(uuid.uuid4())

    # Tag each pair with its group_id
    clusters: dict[str, list[int]] = {}
    for pair in scored_pairs:
        root = uf.find(pair["lead_id_1"])
        gid = root_to_group_id.get(root, str(uuid.uuid4()))
        pair["group_id"] = gid
        clusters[gid] = sorted(groups.get(root, [pair["lead_id_1"], pair["lead_id_2"]]))

    logger.info(f"Union-Find produced {len(clusters)} clusters from {len(scored_pairs)} pairs")
    return scored_pairs, clusters


# Ingest Matching Helper

def find_best_match(
    new_lead: Lead,
    existing_leads: list[Lead],
    threshold: float = 0.6,
) -> Optional[tuple[Lead, float, dict]]:
    """Find the best matching existing lead using the same blocking+scoring logic.
    
    Used by the ingest endpoint to decide create-or-update.
    Returns (matched_lead, confidence, scores) or None.
    """
    if not existing_leads:
        return None

    # Generate blocking keys for the new lead
    new_keys = generate_blocking_keys(new_lead)
    new_key_set: set[str] = set()
    for key_type, key_values in new_keys.items():
        for kv in key_values:
            new_key_set.add(f"{key_type}:{kv}")

    # Find candidates via blocking
    candidates: set[int] = set()
    lead_map = {lead.id: lead for lead in existing_leads}

    for existing in existing_leads:
        existing_keys = generate_blocking_keys(existing)
        for key_type, key_values in existing_keys.items():
            for kv in key_values:
                if f"{key_type}:{kv}" in new_key_set:
                    candidates.add(existing.id)

    if not candidates:
        return None

    # Score each candidate
    best_match = None
    best_confidence = 0.0
    best_scores = {}

    for cid in candidates:
        existing = lead_map[cid]
        confidence, scores = score_pair(new_lead, existing)
        if confidence >= threshold and confidence > best_confidence:
            best_match = existing
            best_confidence = confidence
            best_scores = scores

    if best_match:
        return best_match, best_confidence, best_scores
    return None


# Main Pipeline

def run_dedupe_pipeline(db: Session) -> list[dict]:
    """Run the full deduplication pipeline.
    
    1. Load all leads
    2. Generate blocking candidates
    3. Score each candidate pair
    4. Optionally verify top pairs with LLM
    5. Union-Find grouping into clusters
    6. Persist results + update dedup_group_id on leads
    
    Returns list of candidate dicts sorted by confidence desc.
    """
    settings = get_settings()

    # Load all leads
    leads = db.query(Lead).all()
    lead_map = {lead.id: lead for lead in leads}
    logger.info(f"Loaded {len(leads)} leads for dedup pipeline")

    # Stage 1: Blocking
    candidate_pairs = build_candidate_pairs(leads)
    logger.info(f"Blocking produced {len(candidate_pairs)} candidate pairs")

    # Stage 2: Scoring
    scored_pairs = []
    for id1, id2 in candidate_pairs:
        lead1 = lead_map.get(id1)
        lead2 = lead_map.get(id2)
        if not lead1 or not lead2:
            continue

        confidence, scores = score_pair(lead1, lead2)
        if confidence >= settings.DEDUPE_CONFIDENCE_THRESHOLD:
            explanation = generate_explanation(scores, lead1, lead2)
            scored_pairs.append({
                "lead_id_1": id1,
                "lead_id_2": id2,
                "confidence": round(confidence, 4),
                "match_reasons": {k: round(v, 4) for k, v in scores.items()},
                "explanation": explanation,
            })

    scored_pairs.sort(key=lambda x: x["confidence"], reverse=True)
    logger.info(f"Scoring found {len(scored_pairs)} pairs above threshold {settings.DEDUPE_CONFIDENCE_THRESHOLD}")

    # Stage 3: Optional LLM verification for top pairs (with local cache to prevent quota exhaustion)
    if settings.GEMINI_API_KEY:
        # Cache previously verified pairs so re-running scans doesn't burn redundant API credits
        existing_llm_cache = {}
        for cand in db.query(DedupeCandidate).all():
            if cand.explanation and " | LLM: " in cand.explanation:
                existing_llm_cache[(cand.lead_id_1, cand.lead_id_2)] = cand.explanation.split(" | LLM: ", 1)[1]

        top_pairs = [p for p in scored_pairs if p["confidence"] >= settings.DEDUPE_LLM_THRESHOLD]
        top_pairs = top_pairs[:settings.DEDUPE_LLM_MAX_PAIRS]

        for pair in top_pairs:
            pair_key = (pair["lead_id_1"], pair["lead_id_2"])
            cached_exp = existing_llm_cache.get(pair_key)
            if cached_exp:
                pair["explanation"] += f" | LLM: {cached_exp}"
                continue

            lead1 = lead_map[pair["lead_id_1"]]
            lead2 = lead_map[pair["lead_id_2"]]
            try:
                llm_result = verify_pair_llm(lead1, lead2)
                if llm_result:
                    pair["llm_verification"] = llm_result
                    if llm_result.get("explanation"):
                        pair["explanation"] += f" | LLM: {llm_result['explanation']}"
            except Exception as e:
                logger.warning(f"LLM verification failed for pair ({pair['lead_id_1']}, {pair['lead_id_2']}): {e}")

    # Stage 4: Union-Find grouping
    scored_pairs, clusters = group_pairs_with_union_find(scored_pairs)

    # Persist results
    # Clear old candidates
    db.query(DedupeCandidate).delete()

    # Clear old dedup_group_id on all leads
    db.query(Lead).filter(Lead.dedup_group_id.isnot(None)).update(
        {Lead.dedup_group_id: None}, synchronize_session="fetch"
    )

    for pair in scored_pairs:
        candidate = DedupeCandidate(
            lead_id_1=pair["lead_id_1"],
            lead_id_2=pair["lead_id_2"],
            confidence=pair["confidence"],
            match_reasons=pair["match_reasons"],
            explanation=pair["explanation"],
            status="pending",
            group_id=pair.get("group_id"),
        )
        db.add(candidate)

    # Update dedup_group_id on leads
    for group_id, lead_ids in clusters.items():
        for lid in lead_ids:
            lead = lead_map.get(lid)
            if lead:
                lead.dedup_group_id = group_id

    db.commit()
    logger.info(f"Persisted {len(scored_pairs)} dedupe candidates in {len(clusters)} clusters")

    return scored_pairs

