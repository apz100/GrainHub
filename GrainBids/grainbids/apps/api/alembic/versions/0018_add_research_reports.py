"""add research reports table

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(length=60), nullable=False),
        sa.Column("commodity", sa.String(length=120), nullable=False),
        sa.Column("report_date", sa.String(length=50), nullable=False),
        sa.Column("vintage", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("delay_label", sa.String(length=120), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "report_type",
            "commodity",
            "report_date",
            name="uq_research_reports_org_type_commodity_date",
        ),
    )
    op.create_index(
        "ix_research_reports_org_type",
        "research_reports",
        ["org_id", "report_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_research_reports_org_type", table_name="research_reports")
    op.drop_table("research_reports")
