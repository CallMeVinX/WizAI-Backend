"""Create initial schema with leads, form_submissions, and dedupe_candidates tables.

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
    """Create all initial database tables and indexes."""
    # 1. Create leads table
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.BigInteger(), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('full_name', sa.String(length=200), nullable=True),
        sa.Column('job_title', sa.String(length=150), nullable=True),
        sa.Column('company_name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('phone_normalized', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('lead_status', sa.String(length=20), nullable=False, server_default='new'),
        sa.Column('lifecycle_stage', sa.String(length=50), nullable=True),
        sa.Column('original_source', sa.String(length=100), nullable=True),
        sa.Column('source_drill_down', sa.String(length=200), nullable=True),
        sa.Column('contact_owner', sa.String(length=100), nullable=True),
        sa.Column('lead_score', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('ai_source_channel', sa.String(length=30), nullable=True),
        sa.Column('ai_source_detail', sa.Text(), nullable=True),
        sa.Column('dedup_group_id', sa.String(length=36), nullable=True),
        sa.Column('original_create_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('original_modified_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_id')
    )
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=False)
    op.create_index(op.f('ix_leads_phone_normalized'), 'leads', ['phone_normalized'], unique=False)
    op.create_index(op.f('ix_leads_country'), 'leads', ['country'], unique=False)
    op.create_index(op.f('ix_leads_lead_status'), 'leads', ['lead_status'], unique=False)
    op.create_index(op.f('ix_leads_contact_owner'), 'leads', ['contact_owner'], unique=False)
    op.create_index(op.f('ix_leads_dedup_group_id'), 'leads', ['dedup_group_id'], unique=False)

    # 2. Create form_submissions table
    op.create_table(
        'form_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('form_id', sa.String(length=50), nullable=True),
        sa.Column('form_name', sa.String(length=100), nullable=True),
        sa.Column('page_url', sa.String(length=200), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_form_submissions_id'), 'form_submissions', ['id'], unique=False)

    # 3. Create dedupe_candidates table
    op.create_table(
        'dedupe_candidates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id_1', sa.Integer(), nullable=False),
        sa.Column('lead_id_2', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('match_reasons', sa.JSON(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=True),
        sa.Column('group_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['lead_id_1'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id_2'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lead_id_1', 'lead_id_2', name='uq_dedupe_pair')
    )
    op.create_index(op.f('ix_dedupe_candidates_id'), 'dedupe_candidates', ['id'], unique=False)
    op.create_index(op.f('ix_dedupe_candidates_group_id'), 'dedupe_candidates', ['group_id'], unique=False)


def downgrade() -> None:
    """Drop all initial database tables and indexes."""
    op.drop_index(op.f('ix_dedupe_candidates_group_id'), table_name='dedupe_candidates')
    op.drop_index(op.f('ix_dedupe_candidates_id'), table_name='dedupe_candidates')
    op.drop_table('dedupe_candidates')

    op.drop_index(op.f('ix_form_submissions_id'), table_name='form_submissions')
    op.drop_table('form_submissions')

    op.drop_index(op.f('ix_leads_dedup_group_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_contact_owner'), table_name='leads')
    op.drop_index(op.f('ix_leads_lead_status'), table_name='leads')
    op.drop_index(op.f('ix_leads_country'), table_name='leads')
    op.drop_index(op.f('ix_leads_phone_normalized'), table_name='leads')
    op.drop_index(op.f('ix_leads_email'), table_name='leads')
    op.drop_index(op.f('ix_leads_id'), table_name='leads')
    op.drop_table('leads')
