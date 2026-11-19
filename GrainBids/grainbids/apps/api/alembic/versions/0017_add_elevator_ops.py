"""add elevator ops tables (grower contracts, scale tickets, CRM notes)

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-18

Note: down_revision is 0016, the advisor silo migration. If 0016 is not
present when this runs, the chain is broken — check that the advisor
worker's 0016 migration exists first.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grower_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("grower_name", sa.String(length=200), nullable=False),
        sa.Column("commodity", sa.String(length=100), nullable=False),
        sa.Column("quantity_bushels", sa.Numeric(14, 2), nullable=False),
        sa.Column("delivery_start", sa.Date(), nullable=True),
        sa.Column("delivery_end", sa.Date(), nullable=True),
        sa.Column("price_per_bushel", sa.Numeric(12, 4), nullable=True),
        sa.Column("basis", sa.Numeric(12, 4), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("esign_status", sa.String(length=30), nullable=True),
        sa.Column("esign_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grower_contracts_org_id", "grower_contracts", ["org_id"], unique=False)
    op.create_index("ix_grower_contracts_company_id", "grower_contracts", ["company_id"], unique=False)
    op.create_index("ix_grower_contracts_status", "grower_contracts", ["status"], unique=False)

    op.create_table(
        "scale_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ticket_number", sa.String(length=100), nullable=False),
        sa.Column("ticket_date", sa.Date(), nullable=False),
        sa.Column("commodity", sa.String(length=100), nullable=False),
        sa.Column("bushels", sa.Numeric(14, 2), nullable=False),
        sa.Column("moisture_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("grade", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["grower_contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scale_tickets_org_id", "scale_tickets", ["org_id"], unique=False)
    op.create_index("ix_scale_tickets_contract_id", "scale_tickets", ["contract_id"], unique=False)
    op.create_index("ix_scale_tickets_ticket_date", "scale_tickets", ["ticket_date"], unique=False)

    op.create_table(
        "crm_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("grower_name", sa.String(length=200), nullable=False),
        sa.Column("author", sa.String(length=200), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_notes_org_id", "crm_notes", ["org_id"], unique=False)
    op.create_index("ix_crm_notes_grower_name", "crm_notes", ["grower_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crm_notes_grower_name", table_name="crm_notes")
    op.drop_index("ix_crm_notes_org_id", table_name="crm_notes")
    op.drop_table("crm_notes")
    op.drop_index("ix_scale_tickets_ticket_date", table_name="scale_tickets")
    op.drop_index("ix_scale_tickets_contract_id", table_name="scale_tickets")
    op.drop_index("ix_scale_tickets_org_id", table_name="scale_tickets")
    op.drop_table("scale_tickets")
    op.drop_index("ix_grower_contracts_status", table_name="grower_contracts")
    op.drop_index("ix_grower_contracts_company_id", table_name="grower_contracts")
    op.drop_index("ix_grower_contracts_org_id", table_name="grower_contracts")
    op.drop_table("grower_contracts")
