"""add alert rule basis threshold columns

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-19

Adds the optional per-rule basis threshold used by the basis-alert
wiring (Cycle 7): ``alert_rules.basis_threshold`` /
``alert_rules.basis_threshold_operator``. Both nullable — existing
price-only rules are unaffected (a rule with no basis threshold never
takes the basis path in the evaluator).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alert_rules",
        sa.Column("basis_threshold", sa.Numeric(18, 6), nullable=True),
    )
    op.add_column(
        "alert_rules",
        sa.Column("basis_threshold_operator", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("alert_rules", "basis_threshold_operator")
    op.drop_column("alert_rules", "basis_threshold")
