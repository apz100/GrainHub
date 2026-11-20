from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CommodityAlias(Base):
    """Operator override pinning one raw commodity label to a canonical name.

    Written by hand (SQL/admin), never by code: the resolver in
    ``app.services.commodity_normalization`` reads this table before
    its built-in rules so a label the rules refuse to guess — or get
    wrong for a specific source — can be pinned without a deploy.
    ``crop_tag`` is "new" / "old" / NULL and overrides the tag parsed
    from the label.
    """

    __tablename__ = "commodity_aliases"

    raw_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(120), nullable=False)
    crop_tag: Mapped[str | None] = mapped_column(String(10), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
