"""add farm profiles for the Advisor silo

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "farm_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farm_name", sa.String(length=200), nullable=False),
        sa.Column("crop_mix_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_acres", sa.Numeric(12, 2), nullable=True),
        sa.Column("storage_capacity_bu", sa.Numeric(14, 2), nullable=True),
        sa.Column("cash_flow_target_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("risk_tolerance", sa.String(length=20), nullable=False, server_default="moderate"),
        sa.Column("home_location", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_farm_profiles_org_id",
        "farm_profiles",
        ["org_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_farm_profiles_org_id", table_name="farm_profiles")
    op.drop_table("farm_profiles")
