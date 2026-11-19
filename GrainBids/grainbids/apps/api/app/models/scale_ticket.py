import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScaleTicket(Base):
    """A scale ticket recording grain delivered against a grower contract.

    ticket_number is the elevator's own ticket number as printed / recorded
    at the scale — it is supplied by the elevator, never generated here.
    """

    __tablename__ = "scale_tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grower_contracts.id"), nullable=True
    )

    ticket_number: Mapped[str] = mapped_column(String(100), nullable=False)
    ticket_date: Mapped[date] = mapped_column(Date, nullable=False)
    commodity: Mapped[str] = mapped_column(String(100), nullable=False)
    bushels: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    moisture_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
