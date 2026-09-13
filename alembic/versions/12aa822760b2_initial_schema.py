"""Add deduplication cluster group columns to leads and dedupe_candidates.

Revision ID: 12aa822760b2
Revises: None
Create Date: 2026-09-13 16:22:06.941115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = '12aa822760b2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cluster group_id to dedupe_candidates and dedup_group_id to leads."""
    op.add_column('dedupe_candidates', sa.Column('group_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_dedupe_candidates_group_id'), 'dedupe_candidates', ['group_id'], unique=False)
    op.add_column('leads', sa.Column('dedup_group_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_leads_dedup_group_id'), 'leads', ['dedup_group_id'], unique=False)


def downgrade() -> None:
    """Revert cluster group_id from dedupe_candidates and dedup_group_id from leads."""
    op.drop_index(op.f('ix_leads_dedup_group_id'), table_name='leads')
    op.drop_column('leads', 'dedup_group_id')
    op.drop_index(op.f('ix_dedupe_candidates_group_id'), table_name='dedupe_candidates')
    op.drop_column('dedupe_candidates', 'group_id')

