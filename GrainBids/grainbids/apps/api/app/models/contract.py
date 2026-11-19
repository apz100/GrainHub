import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Grower contract statuses. "pending_signature" is set by the stubbed eSign
# workflow (see app/api/routes/elevator_ops.py) — no real eSign provider is
# called. "signed" is only reachable once a real provider is configured.
CONTRACT_STATUSES = {
    "draft",
    "offered",
    "pending_signature",
    "signed",
    "fulfilled",
    "cancelled",
}


class GrowerContract(Base):
    """A grain contract between an elevator (company) and a grower.

    v1 scaffold: pricing is stored as a flat price and/or basis so the record
    works for cash, basis-only, and deferred-pricing contracts without
    inventing settlement logic. Settlement, delivery scheduling, and ERP
    sync are explicitly out of scope for v1.
    """

    __tablename__ = "grower_contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)

    grower_name: Mapped[str] = mapped_column(String(200), nullable=False)
    commodity: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_bushels: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    delivery_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    price_per_bushel: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    basis: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")

    # Stubbed eSign workflow state. esign_status is "pending_signature" once a
    # signing request has been recorded; no external provider is contacted.
    esign_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    esign_requested_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
