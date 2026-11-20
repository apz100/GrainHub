"""Public best-bid page API (Cycle 2).

``GET /api/best-bids`` is public: no auth, no ``X-Org-Id`` header,
no user data. It returns the top cash bids by company from real
``NormalizedPrice`` rows already in the database, grouped by
commodity and delivery month. Elevator cash bids are published
publicly by the elevators themselves, so no per-organisation scoping
is applied here — and no watchlists, alerts, accounts, or any other
user data appear in the response.

One row per company (its best cash price for that commodity +
delivery month), sorted by cash price descending, capped by
``limit`` (default 30). Empty states return empty groups, never
invented bids.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.routes.normalized_prices import (
    _canonical_month_label,
    _display_company_name_for_row,
    _load_company_name_map,
    _load_location_company_map,
    _to_basis_float,
    _to_float,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.normalized_price import NormalizedPrice
from app.models.price_snapshot import PriceSnapshot
from app.services.market_canonicalization import canonical_commodity_name, normalize_text

router = APIRouter(prefix="/api/best-bids", tags=["best-bids"])

_BEST_BIDS_FETCH_LIMIT = 300

NOTE = (
    "Top cash bids by company from real normalized prices already in "
    "the database. Currency is not stored on normalized prices, so "
    "currency is null on every bid; no currency is assumed. "
    "Unit is \"bu\" for cash_price_bu (cash_price_mt is also shown, unit \"mt\")."
)


def _delivery_label(price: NormalizedPrice) -> str:
    return _canonical_month_label(
        normalize_text(price.delivery_label)
        or normalize_text(price.delivery_end)
        or normalize_text(price.futures_month)
    ) or "Unspecified"


@router.get("")
def best_bids(
    commodity: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    invalid = {(label or "").strip().casefold() for label in settings.invalid_commodity_labels_set}
    wanted = (commodity or "").strip().casefold() or None

    query = (
        select(NormalizedPrice, PriceSnapshot)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .where(NormalizedPrice.cash_price_bu.is_not(None))
        .order_by(desc(NormalizedPrice.cash_price_bu), desc(PriceSnapshot.captured_at))
    )
    rows = db.execute(query.limit(_BEST_BIDS_FETCH_LIMIT)).all()

    location_ids = {price.location_id for price, _s in rows if price.location_id is not None}
    company_ids = {price.company_id for price, _s in rows if price.company_id is not None}
    location_company_map = _load_location_company_map(db, location_ids=location_ids)
    company_ids.update(location_company_map.values())
    company_name_map = _load_company_name_map(db, company_ids=company_ids)

    # Sort in Python as well as SQL so the per-company best pick does not
    # depend on the database returning rows in order.
    rows = sorted(
        rows,
        key=lambda pair: (
            -(_to_float(pair[0].cash_price_bu) if _to_float(pair[0].cash_price_bu) is not None else float("-inf")),
            -(pair[1].captured_at.timestamp() if pair[1] is not None and pair[1].captured_at is not None else 0.0),
        ),
    )

    # Best row per company per (commodity, delivery month): rows arrive
    # cash-price descending, so the first row seen for a key wins.
    best_by_key: dict[tuple[str, str, str], dict[str, object]] = {}
    for price, snapshot in rows:
        name = (price.commodity_name or "").strip()
        if not name or name.casefold() in invalid:
            continue
        if wanted and wanted not in name.casefold():
            continue
        company = _display_company_name_for_row(
            price,
            company_name_map=company_name_map,
            location_company_map=location_company_map,
        ) or (price.source_name or "Unknown")
        commodity_label = canonical_commodity_name(name) or name
        delivery = _delivery_label(price)
        key = (commodity_label.casefold(), delivery.casefold(), company.casefold())
        if key in best_by_key:
            continue
        captured = snapshot.captured_at if snapshot is not None else None
        if captured is not None and captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
        best_by_key[key] = {
            "company_name": company,
            "location": price.location,
            "location_id": str(price.location_id) if price.location_id else None,
            "commodity_name": commodity_label,
            "delivery_month": delivery,
            "cash_price_bu": _to_float(price.cash_price_bu),
            "cash_price_mt": _to_float(price.cash_price_mt),
            "basis": _to_basis_float(price.basis),
            "futures_month": _canonical_month_label(normalize_text(price.futures_month)),
            "futures_price": _to_float(price.futures_price),
            "currency": None,
            "unit": "bu",
            "quote_date": captured.date().isoformat() if captured else None,
            "captured_at": captured.isoformat() if captured else None,
            "source": price.source_name,
        }

    top = sorted(
        best_by_key.values(),
        key=lambda bid: (
            -(bid["cash_price_bu"] if isinstance(bid["cash_price_bu"], (int, float)) else float("-inf")),
            str(bid["company_name"] or ""),
        ),
    )[:limit]

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for bid in top:
        grouped[(str(bid["commodity_name"]), str(bid["delivery_month"]))].append(bid)
    groups = [
        {"commodity": commodity_label, "delivery_month": delivery, "bids": bids}
        for (commodity_label, delivery), bids in sorted(grouped.items())
    ]
    return {
        "commodity": commodity,
        "limit": limit,
        "bid_count": len(top),
        "groups": groups,
        "note": NOTE,
    }
