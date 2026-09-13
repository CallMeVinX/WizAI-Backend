# Model Documentation: `app/models/dedupe.py`

## Overview
Defines the `DedupeCandidate` SQLAlchemy model, functioning as a reconciliation table that stores pairwise candidate duplicate matches surfaced by the deduplication engine.

## Schema & Attributes
Mapped to the `dedupe_candidates` table inheriting from `Base`.

### Attributes:
- **`id`**: Integer primary key with index.
- **`lead_id_1` & `lead_id_2`**: Foreign keys referencing `leads.id`. Represents the two records under comparison, ordered canonically (`lead_id_1 < lead_id_2`) to prevent reverse-pair redundancy.
- **`confidence`**: Composite float score ($0.0 \le S \le 1.0$) indicating the statistical confidence that the pair represents the same real-world individual.
- **`match_reasons`**: Flexible `JSON` column storing individual signal breakdown scores (e.g., `{"email": 1.0, "name": 0.85, "phone": 0.0}`).
- **`explanation`**: Human-readable summary synthesized by the pipeline explaining why the match was flagged (e.g., "Exact email match; Same company").
- **`status`**: State machine string (`pending`, `confirmed`, `rejected`) enabling human-in-the-loop review and audit approvals.
- **`group_id`**: UUID identifying the cluster assigned by the Union-Find graph algorithm. All mutually duplicate records share the same cluster `group_id`.
- **`created_at`**: UTC timestamp recording when the candidate pair was generated.

## Architectural Role
This table maintains candidate pairs in a non-destructive manner. The system never automatically deletes or mutates original contact records. Instead, recommendations are persisted here for audit trails and operator review. If merge operations are executed in future workflows, this table acts as the authorization gate by targeting candidates with `confirmed` status.
