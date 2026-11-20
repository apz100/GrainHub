"""add research_cache_entries table

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-20

Marathon Phase C: DB-backed cache for USDA reference data (FAS PSD
world data, PSD commodity catalogue, NASS series). The research
routes fetch live from USDA on a cache miss and serve the stored
decoded payload until the TTL in app.services.research_cache
expires, so page loads never wait on — or hammer — the upstream
APIs. Global reference data: no org_id, one row per
(dataset, cache_key).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_cache_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset", sa.String(length=60), nullable=False),
        sa.Column("cache_key", sa.String(length=200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset", "cache_key", name="uq_research_cache_dataset_key"),
    )
    op.create_index("ix_research_cache_dataset", "research_cache_entries", ["dataset"])


def downgrade() -> None:
    op.drop_index("ix_research_cache_dataset", table_name="research_cache_entries")
    op.drop_table("research_cache_entries")
