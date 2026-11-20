"""Price history + seasonal averages (Cycle 2).

Read-only views over real ``NormalizedPrice`` rows already in the
database. Nothing here calls an external service, scrapes, or invents
a price:

- ``GET /api/prices/history`` returns the stored time series for one
  commodity (optionally one location), sorted by quote date.
- ``GET /api/prices/seasonal`` averages the stored cash prices by ISO
  week of year, per year, then across the years actually present
  (at most the 5 most recent). Years with no data are reported as
  missing, never invented or interpolated.

Currency note: ``NormalizedPrice`` stores no currency column, so
``currency`` is returned as ``null`` on every point with a note
explaining that no currency is assumed. ``unit`` is ``"bu"`` for
``cash_price_bu`` (``cash_price_mt`` is also returned, unit ``"mt"``).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(prefix="/api/prices", tags=["prices"])

CURRENCY_NOTE = (
    "Currency is not stored on normalized prices in this database, "
    "so currency is null on every point; no currency is assumed. "
    "Unit is \"bu\" for cash_price_bu (cash_price_mt is also shown, unit \"mt\")."
)
SEASONAL_YEARS = 5
_HISTORY_FETCH_LIMIT = 5000

# Cycle 17: the empty state (and every state) names its source and the
# date it was computed, so "no data" is honest and dated rather than
# a bare empty list.
HISTORY_SOURCE = (
    "Normalized prices already in the database (ingested elevator "
    "cash bids); no price is invented, backfilled or estimated."
)


def _quote_date(snapshot: PriceSnapshot) -> datetime | None:
    captured = snapshot.captured_at if snapshot is not None else None
    if captured is None:
        return None
    if captured.tzinfo is None:
        return captured.replace(tzinfo=timezone.utc)
    return captured


def _invalid_commodity_labels() -> tuple[str, ...]:
    return tuple(settings.invalid_commodity_labels_set) or ("__invalid_commodity__",)


def _load_price_rows(
    db: Session,
    *,
    commodity: str,
    location_id: uuid.UUID | None,
) -> list[tuple[NormalizedPrice, PriceSnapshot]]:
    """Fetch (price, snapshot) pairs for a commodity, newest first.

    Filtering that depends on stored values (commodity match,
    location, date window, cash price present) is done in Python so
    the endpoint behaves identically against the real database and
    against the fake sessions used in tests, and so no
    Postgres-specific SQL is needed here.
    """
    query = (
        select(NormalizedPrice, PriceSnapshot)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .order_by(desc(PriceSnapshot.captured_at))
    )
    rows = db.execute(query.limit(_HISTORY_FETCH_LIMIT)).all()
    wanted = (commodity or "").strip().casefold()
    invalid = {label.casefold() for label in _invalid_commodity_labels()}
    kept: list[tuple[NormalizedPrice, PriceSnapshot]] = []
    for price, snapshot in rows:
        name = (price.commodity_name or "").strip()
        if not name or name.casefold() in invalid:
            continue
        if wanted and wanted not in name.casefold():
            continue
        if location_id is not None and price.location_id != location_id:
            continue
        kept.append((price, snapshot))
    return kept


def _serialize_history_point(
    price: NormalizedPrice,
    snapshot: PriceSnapshot,
    company_name_map: dict[uuid.UUID, str],
    location_company_map: dict[uuid.UUID, uuid.UUID],
) -> dict[str, object]:
    captured = _quote_date(snapshot)
    return {
        "date": captured.date().isoformat() if captured else None,
        "quote_date": captured.isoformat() if captured else None,
        "location": price.location,
        "location_id": str(price.location_id) if price.location_id else None,
        "company_name": _display_company_name_for_row(
            price,
            company_name_map=company_name_map,
            location_company_map=location_company_map,
        ),
        "commodity_name": canonical_commodity_name(price.commodity_name) or price.commodity_name,
        "source_name": price.source_name,
        "delivery_label": _canonical_month_label(normalize_text(price.delivery_label) or normalize_text(price.delivery_end)),
        "futures_month": _canonical_month_label(normalize_text(price.futures_month)),
        "futures_price": _to_float(price.futures_price),
        "basis": _to_basis_float(price.basis),
        "cash_price_bu": _to_float(price.cash_price_bu),
        "cash_price_mt": _to_float(price.cash_price_mt),
        "currency": None,
        "unit": "bu",
    }


@router.get("/history")
def price_history(
    commodity: str = Query(...),
    location_id: uuid.UUID | None = Query(None),
    days: int = Query(90, ge=1, le=1825),
    db: Session = Depends(get_db),
):
    if not (commodity or "").strip():
        raise HTTPException(status_code=400, detail="commodity is required")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = _load_price_rows(db, commodity=commodity, location_id=location_id)

    location_ids = {price.location_id for price, _s in rows if price.location_id is not None}
    company_ids = {price.company_id for price, _s in rows if price.company_id is not None}
    location_company_map = _load_location_company_map(db, location_ids=location_ids)
    company_ids.update(location_company_map.values())
    company_name_map = _load_company_name_map(db, company_ids=company_ids)

    points: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for price, snapshot in rows:
        captured = _quote_date(snapshot)
        if captured is None or captured < cutoff:
            continue
        if _to_float(price.cash_price_bu) is None and _to_float(price.cash_price_mt) is None:
            continue
        point = _serialize_history_point(price, snapshot, company_name_map, location_company_map)
        dedupe_key = (
            point["date"],
            point["location"],
            point["company_name"],
            point["futures_month"],
            point["cash_price_bu"],
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        points.append(point)
    points.sort(key=lambda p: (str(p["date"] or ""), str(p["location"] or ""), str(p["company_name"] or "")))
    return {
        "commodity": commodity,
        "location_id": str(location_id) if location_id else None,
        "days": days,
        "point_count": len(points),
        "points": points,
        "source": HISTORY_SOURCE,
        "as_of": datetime.now(timezone.utc).date().isoformat(),
        "note": CURRENCY_NOTE,
    }


def _seasonal_points(
    rows: list[tuple[NormalizedPrice, PriceSnapshot]],
) -> tuple[list[dict[str, object]], list[int], dict[int, int]]:
    """Group stored cash prices by ISO week, per year, then average.

    Only years actually present in the rows are used, capped at the
    5 most recent. A week's seasonal value is the mean of that week's
    per-year means, so a year with many quotes does not outweigh a
    year with few. No missing year is invented or interpolated.
    """
    by_week_year: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    observations_by_year: dict[int, int] = defaultdict(int)
    for price, snapshot in rows:
        captured = _quote_date(snapshot)
        cash = _to_float(price.cash_price_bu)
        if captured is None or cash is None:
            continue
        year = captured.year
        observations_by_year[year] += 1
        by_week_year[captured.isocalendar()[1]][year].append(cash)

    years_present = sorted(observations_by_year)
    years_used = years_present[-SEASONAL_YEARS:]
    years_set = set(years_used)
    points: list[dict[str, object]] = []
    for week in sorted(by_week_year):
        yearly_means: dict[int, float] = {}
        observations = 0
        for year in sorted(by_week_year[week]):
            if year not in years_set:
                continue
            values = by_week_year[week][year]
            yearly_means[year] = mean(values)
            observations += len(values)
        if not yearly_means:
            continue
        month = _month_for_iso_week(week, years_used[-1] if years_used else datetime.now(timezone.utc).year)
        points.append(
            {
                "week": week,
                "month": month,
                "average_cash_price_bu": mean(yearly_means.values()),
                "years": sorted(yearly_means),
                "yearly_averages": {str(year): value for year, value in sorted(yearly_means.items())},
                "observations": observations,
            }
        )
    return points, years_used, dict(observations_by_year)


def _month_for_iso_week(week: int, year: int) -> int | None:
    """Calendar month containing the Monday of an ISO week in a year."""
    try:
        monday = datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u")
    except ValueError:
        return None
    return monday.month


@router.get("/seasonal")
def price_seasonal(
    commodity: str = Query(...),
    db: Session = Depends(get_db),
):
    if not (commodity or "").strip():
        raise HTTPException(status_code=400, detail="commodity is required")
    rows = _load_price_rows(db, commodity=commodity, location_id=None)
    points, years_used, observations_by_year = _seasonal_points(rows)
    years_covered = len(years_used)
    if years_covered >= SEASONAL_YEARS:
        note = (
            f"Seasonal average by ISO week from {SEASONAL_YEARS} years of real "
            "normalized prices already in the database. "
            "USDA research-report rows hold report metrics (ending stocks, "
            "crop progress), not cash prices, so no price is derived from them."
        )
    else:
        note = (
            f"Only {years_covered} year(s) of real normalized prices exist in "
            "the database for this commodity; the seasonal average uses only "
            "those years. Missing years are not invented or interpolated. "
            "USDA research-report rows hold report metrics (ending stocks, "
            "crop progress), not cash prices, so no price is derived from them."
        )
    return {
        "commodity": commodity,
        "granularity": "iso_week",
        "years_requested": SEASONAL_YEARS,
        "years_covered": years_covered,
        "years": years_used,
        "observations_by_year": {str(year): count for year, count in sorted(observations_by_year.items())},
        "point_count": len(points),
        "points": points,
        "source": HISTORY_SOURCE,
        "as_of": datetime.now(timezone.utc).date().isoformat(),
        "note": f"{note} {CURRENCY_NOTE}",
    }
