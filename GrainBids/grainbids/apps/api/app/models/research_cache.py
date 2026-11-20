import uuid

from sqlalchemy import DateTime, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResearchCacheEntry(Base):
    """One cached USDA reference-data response (Marathon Phase C).

    FAS PSD and NASS Quick Stats data is public reference data, not
    org data, so the cache is global (no org_id): one row per
    (dataset, cache_key), e.g. dataset ``fas_psd_world`` with key
    ``0440000/2026``. ``payload`` stores the DECODED rows exactly as
    the route returns them; ``fetched_at`` drives the TTL in
    ``app.services.research_cache``. Nothing here is invented data —
    rows only ever come from a live upstream fetch.
    """

    __tablename__ = "research_cache_entries"
    __table_args__ = (
        UniqueConstraint("dataset", "cache_key", name="uq_research_cache_dataset_key"),
        Index("ix_research_cache_dataset", "dataset"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset: Mapped[str] = mapped_column(String(60), nullable=False)
    cache_key: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    fetched_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
