"""Deduplication API routes."""

import logging
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dedupe import DedupeCandidate
from app.models.lead import Lead
from app.schemas.dedupe import (
    DedupeCandidateResponse,
    DedupeCandidateListResponse,
    DedupeCandidateUpdate,
    DedupeClusterResponse,
    DedupeClusterListResponse,
)
from app.schemas.lead import LeadResponse
from app.services.dedupe_service import run_dedupe_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leads", tags=["dedup"])


def _candidate_to_response(c: DedupeCandidate, db: Session) -> DedupeCandidateResponse:
    """Helper to convert a DedupeCandidate ORM object to response schema."""
    lead1 = db.get(Lead, c.lead_id_1)
    lead2 = db.get(Lead, c.lead_id_2)
    return DedupeCandidateResponse(
        id=c.id,
        lead_id_1=c.lead_id_1,
        lead_id_2=c.lead_id_2,
        confidence=c.confidence,
        match_reasons=c.match_reasons,
        explanation=c.explanation,
        status=c.status,
        group_id=c.group_id,
        created_at=c.created_at,
        lead_1=LeadResponse.model_validate(lead1) if lead1 else None,
        lead_2=LeadResponse.model_validate(lead2) if lead2 else None,
    )


@router.post("/dedupe-candidates", response_model=DedupeCandidateListResponse)
def run_dedup(db: Session = Depends(get_db)):
    """Run the deduplication pipeline.
    
    Generates candidate pairs ranked by confidence, grouped into clusters.
    """
    run_dedupe_pipeline(db)
    
    candidates = db.query(DedupeCandidate).order_by(DedupeCandidate.confidence.desc()).all()
    response_data = [_candidate_to_response(c, db) for c in candidates]
    
    return DedupeCandidateListResponse(data=response_data, total=len(response_data))


@router.get("/dedupe-candidates", response_model=DedupeCandidateListResponse)
def list_dedupe_candidates(
    status: str = Query(None, description="Filter by status: pending, confirmed, rejected"),
    min_confidence: float = Query(None, description="Minimum confidence threshold"),
    db: Session = Depends(get_db),
):
    """List existing dedupe candidate pairs."""
    query = db.query(DedupeCandidate).order_by(DedupeCandidate.confidence.desc())
    
    if status:
        query = query.filter(DedupeCandidate.status == status)
    if min_confidence is not None:
        query = query.filter(DedupeCandidate.confidence >= min_confidence)
    
    candidates = query.all()
    response_data = [_candidate_to_response(c, db) for c in candidates]
    
    return DedupeCandidateListResponse(data=response_data, total=len(response_data))


@router.get("/dedupe-clusters", response_model=DedupeClusterListResponse)
def list_dedupe_clusters(db: Session = Depends(get_db)):
    """List dedupe results grouped as clusters.
    
    Returns grouped duplicate lead clusters by unique cluster group ID:
    {"group_id": "...", "confidence": 0.92, "explanation": "...", "lead_ids": [...]}
    """
    candidates = db.query(DedupeCandidate).order_by(DedupeCandidate.confidence.desc()).all()
    
    # Group by group_id
    groups: dict[str, list[DedupeCandidate]] = defaultdict(list)
    for c in candidates:
        gid = c.group_id or f"pair-{c.id}"
        groups[gid].append(c)
    
    clusters = []
    for group_id, group_candidates in groups.items():
        # Collect all unique lead IDs in this cluster
        lead_ids: set[int] = set()
        for c in group_candidates:
            lead_ids.add(c.lead_id_1)
            lead_ids.add(c.lead_id_2)
        
        # Use the highest confidence and combine explanations
        best = max(group_candidates, key=lambda c: c.confidence)
        explanations = list({c.explanation for c in group_candidates if c.explanation})
        
        # Fetch lead details
        sorted_ids = sorted(lead_ids)
        leads = [db.get(Lead, lid) for lid in sorted_ids]
        lead_responses = [LeadResponse.model_validate(l) for l in leads if l]
        
        clusters.append(DedupeClusterResponse(
            group_id=group_id,
            confidence=best.confidence,
            explanation="; ".join(explanations),
            lead_ids=sorted_ids,
            leads=lead_responses,
        ))
    
    # Sort clusters by confidence desc
    clusters.sort(key=lambda c: c.confidence, reverse=True)
    
    return DedupeClusterListResponse(clusters=clusters, total=len(clusters))


@router.patch("/dedupe-candidates/{candidate_id}", response_model=DedupeCandidateResponse)
def update_dedupe_candidate(
    candidate_id: int,
    body: DedupeCandidateUpdate,
    db: Session = Depends(get_db),
):
    """Update dedupe candidate status (confirm/reject)."""
    if body.status not in ("confirmed", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Status must be 'confirmed', 'rejected', or 'pending'")
    
    candidate = db.get(DedupeCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Dedupe candidate not found")
    
    candidate.status = body.status
    db.commit()
    db.refresh(candidate)
    
    return _candidate_to_response(candidate, db)

