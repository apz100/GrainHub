"""Farm profile model for the Advisor silo (v1).

Design decision (Cycle 1): risk profile is NOT a separate table. A farm's
risk tolerance (``conservative`` / ``moderate`` / ``aggressive``) is a single
column on ``FarmProfile``. A separate ``risk_profile`` table would only pay
for itself if we later need versioned risk profiles, per-crop risk settings,
or a risk history — none of which v1 needs. If that need arises, split the
column out into its own table with a ``farm_profile_id`` FK; the API field
name (``risk_tolerance``) stays the same.

``crop_mix_json`` shape (list of objects, one per crop)::

    [
        {
            "commodity": "Corn",
            "acres": 500,
            "expected_yield_bu_per_acre": 200,
            "cost_per_acre": 800
        }
    ]

``cost_per_acre`` is the farm's all-in production cost per acre for that
crop; it is supplied by the farmer, never estimated by GrainHub. All money
figures are in USD unless the farm says otherwise (a currency field can be
added later; v1 assumes one currency per org).
"""

import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


RISK_TOLERANCES = ("conservative", "moderate", "aggressive")


class FarmProfile(Base):
    __tablename__ = "farm_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    farm_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # List of {commodity, acres, expected_yield_bu_per_acre, cost_per_acre}.
    crop_mix_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    total_acres: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    storage_capacity_bu: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Farmer-supplied cash-flow target in dollars (e.g. revenue needed
    # before a date). Advisory only; never used to invent a price.
    cash_flow_target_usd: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    # One of RISK_TOLERANCES. Drives the cushion the sell/hold signal
    # requires above breakeven (see app/services/advisor.py).
    risk_tolerance: Mapped[str] = mapped_column(String(20), nullable=False, default="moderate", server_default="moderate")
    # Home base used as the default location when looking up cash prices.
    home_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
