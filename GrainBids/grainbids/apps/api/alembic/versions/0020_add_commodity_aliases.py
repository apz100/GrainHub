"""add commodity_aliases override table

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-20

Marathon Phase B: operator overrides for commodity normalization.
The resolver in ``app.services.commodity_normalization`` resolves raw
source labels (``HRW New Crop Wheat``, ``#2 Yellow Corn`` ...) to
canonical commodities by rule; this table lets an operator pin a
label the rules refuse to guess (or resolve differently for one
source) without a code change. Empty at creation — rules carry the
known labels, and ambiguous labels stay unmapped until a human pins
them here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commodity_aliases",
        sa.Column("raw_name", sa.String(length=120), nullable=False),
        sa.Column("canonical_name", sa.String(length=120), nullable=False),
        sa.Column("crop_tag", sa.String(length=10), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("raw_name"),
    )


def downgrade() -> None:
    op.drop_table("commodity_aliases")
