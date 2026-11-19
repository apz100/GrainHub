import uuid

from sqlalchemy import DateTime, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResearchReport(Base):
    """One ingested USDA / official report snapshot.

    ``payload`` holds the report's parsed values exactly as published
    (never invented). Every number shown from this table must also
    carry ``source``, ``vintage`` (release date) and ``delay_label``.
    """

    __tablename__ = "research_reports"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "report_type",
            "commodity",
            "report_date",
            name="uq_research_reports_org_type_commodity_date",
        ),
        Index("ix_research_reports_org_type", "org_id", "report_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    report_type: Mapped[str] = mapped_column(String(60), nullable=False)
    commodity: Mapped[str] = mapped_column(String(120), nullable=False)
    report_date: Mapped[str] = mapped_column(String(50), nullable=False)
    vintage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delay_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
