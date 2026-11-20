"""Basis tracker routes (Cycle 2).

GET /api/basis/tracker -- rank the latest basis per location for a
commodity + delivery month, optionally within a radius of an origin.
GET /api/basis/history -- basis over time for one location + commodity.

Basis is always computed from stored normalized prices (cash minus
futures, per bushel); nothing is estimated. Currency is not stored on
normalized price rows, so responses report ``currency: null`` with a
data-quality note explaining that, rather than assuming CAD or USD.

Origin resolution, in order: ``location_id``, ``location`` name, then the
stored Testville pilot location (see ``basis_tracker.find_default_origin``).
No coordinates are hardcoded: if no origin can be resolved and a radius
is requested, the request is a 400; without a radius, ranking covers all
locations and says so.

Source status (Cycle 3 polish): every ranked / unranked / history row
carries ``source_status`` — the health of the price source that produced
the row, derived from the same real ingestion data as the
source-health dashboard (``app/api/routes/source_health.py``:
``ingestion_runs`` + ``source_health_snapshots``). The dashboard
vocabulary is ``live`` / ``stale`` / ``broken`` / ``unknown``; here
``live`` is reported as ``healthy`` so the tracker reads plainly, and
the mapping is stated on the response. A source with no ingestion data
is ``unknown``, never assumed healthy.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.routes.market_search import parse_delivery_month
from app.api.routes.source_health import build_source_health_rows
from app.core.request_context import RequestContext, get_request_context
from app.db.session import get_db
from app.models.ingestion_run import IngestionRun
from app.models.location import Location
from app.models.normalized_price import NormalizedPrice
from app.models.price_snapshot import PriceSnapshot
from app.models.source import Source
from app.models.source_health_snapshot import SourceHealthSnapshot
from app.services.basis_tracker import (
    build_basis_history,
    find_default_origin,
    rank_basis,
    resolve_origin_location,
)

router = APIRouter(prefix="/api/basis", tags=["basis"])


def _load_price_pairs(
    db: Session, *, org_id: uuid.UUID
) -> list[tuple[NormalizedPrice, PriceSnapshot | None]]:
    """All (price, snapshot) pairs for the org, newest snapshot first."""
    rows = db.execute(
        select(NormalizedPrice, PriceSnapshot)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(Source, Source.id == PriceSnapshot.source_id)
        .where(Source.org_id == org_id)
        .order_by(desc(PriceSnapshot.captured_at))
    ).all()
    pairs: list[tuple[NormalizedPrice, PriceSnapshot | None]] = []
    for item in rows:
        if isinstance(item, tuple) and len(item) == 2:
            pairs.append((item[0], item[1]))
        elif isinstance(item, NormalizedPrice):
            pairs.append((item, None))
    return pairs


def _load_locations(db: Session, *, org_id: uuid.UUID) -> list[Location]:
    rows = db.execute(
        select(Location).where(Location.org_id == org_id)
    ).scalars().all()
    return [row for row in rows if isinstance(row, Location)]


# Source-health vocabulary is live / stale / broken / unknown; the basis
# tracker reports "live" as "healthy" so the tracker reads plainly.
# The mapping is stated on every tracker response (see
# ``SOURCE_STATUS_NOTE``) and nowhere else renames a status.
SOURCE_HEALTH_TO_BASIS_STATUS = {
    "live": "healthy",
    "stale": "stale",
    "broken": "broken",
    "unknown": "unknown",
}

SOURCE_STATUS_NOTE = (
    "source_status comes from the source-health dashboard logic "
    "(ingestion_runs + source_health_snapshots in the database). "
    "'healthy' is the dashboard's 'live': the source's latest ingestion "
    "run completed successfully inside its staleness window. A source "
    "with no ingestion data is 'unknown', never assumed healthy."
)

_UNKNOWN_SOURCE_STATUS = {
    "status": "unknown",
    "note": "No ingestion data recorded for this source — status unknown until the first run.",
}


def _load_source_status_map(db: Session, *, org_id: uuid.UUID) -> dict[str, dict[str, str]]:
    """Source name (casefolded) -> ``{"status", "note"}`` from real ingestion data.

    Reuses :func:`source_health.build_source_health_rows`, so the tracker
    and the dashboard can never disagree about a source. Rows that are
    not the expected model types are ignored (the fake sessions used in
    tests return other row shapes for unmodelled queries); with no usable
    rows every source simply maps to ``unknown``.
    """
    now = datetime.now(timezone.utc)
    sources = [
        row
        for row in db.execute(
            select(Source).where(Source.org_id == org_id)
        ).scalars().all()
        if isinstance(row, Source)
    ]
    runs = [
        row
        for row in db.execute(
            select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(500)
        ).scalars().all()
        if isinstance(row, IngestionRun)
    ]
    snapshots = [
        row
        for row in db.execute(
            select(SourceHealthSnapshot)
            .order_by(SourceHealthSnapshot.captured_at.desc())
            .limit(500)
        ).scalars().all()
        if isinstance(row, SourceHealthSnapshot)
    ]
    status_map: dict[str, dict[str, str]] = {}
    for health_row in build_source_health_rows(sources, runs, snapshots, now):
        name = str(health_row["name"] or "").strip().casefold()
        if not name:
            continue
        status_map[name] = {
            "status": SOURCE_HEALTH_TO_BASIS_STATUS.get(
                str(health_row["status"]), "unknown"
            ),
            "note": str(health_row["note"] or ""),
        }
    return status_map


def _source_status_for(status_map: dict[str, dict[str, str]], source_name: str | None) -> dict[str, str]:
    """Source-health entry for one price row's source name, or ``unknown``."""
    key = (source_name or "").strip().casefold()
    entry = status_map.get(key) if key else None
    if entry is None:
        return dict(_UNKNOWN_SOURCE_STATUS)
    return dict(entry)


def _attach_source_status(
    rows: list[dict[str, object]],
    status_map: dict[str, dict[str, str]],
) -> dict[str, str]:
    """Add ``source_status`` to each serialized basis row.

    Returns a summary mapping each distinct source name in the rows to
    its status string, for the response's top-level ``source_statuses``.
    """
    summary: dict[str, str] = {}
    for row in rows:
        source_name = row.get("source")
        entry = _source_status_for(
            status_map, source_name if isinstance(source_name, str) else None
        )
        row["source_status"] = entry
        if isinstance(source_name, str) and source_name:
            summary[source_name] = entry["status"]
    return summary


def _parse_delivery_month_or_400(delivery_month: str | None) -> int | None:
    if delivery_month is None:
        return None
    try:
        return parse_delivery_month(delivery_month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tracker")
def basis_tracker(
    commodity: str | None = Query(None),
    location: str | None = Query(None),
    location_id: uuid.UUID | None = Query(None),
    radius_km: float | None = Query(None, gt=0, le=2000),
    delivery_month: str | None = Query(None),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    delivery_month_key = _parse_delivery_month_or_400(delivery_month)
    pairs = _load_price_pairs(db, org_id=context.org_id)
    locations = _load_locations(db, org_id=context.org_id)

    origin_location: Location | None = None
    origin_source: str | None = None
    if location_id is not None or location:
        origin_location = resolve_origin_location(
            locations, location_id=location_id, location=location
        )
        origin_source = "location_id" if location_id is not None else "location"
    else:
        origin_location = find_default_origin(locations)
        if origin_location is not None:
            origin_source = f"pilot: {origin_location.name}"

    origin: tuple[float, float] | None = None
    if (
        origin_location is not None
        and origin_location.latitude is not None
        and origin_location.longitude is not None
    ):
        origin = (float(origin_location.latitude), float(origin_location.longitude))

    if radius_km is not None and origin is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "radius_km needs an origin with coordinates: supply a "
                "location_id or location whose stored location has latitude "
                "and longitude, or store coordinates for the Testville "
                "pilot location. No origin could be resolved from stored data."
            ),
        )

    # Narrow the candidate rows to the requested location before ranking.
    if location_id is not None:
        pairs = [pair for pair in pairs if pair[0].location_id == location_id]

    ranked = rank_basis(
        pairs,
        locations=locations,
        origin=origin,
        radius_km=radius_km,
        commodity=commodity,
        delivery_month_key=delivery_month_key,
    )
    status_map = _load_source_status_map(db, org_id=context.org_id)
    ranked_statuses = _attach_source_status(ranked["ranked"], status_map)
    unranked_statuses = _attach_source_status(ranked["unranked"], status_map)
    source_statuses = {**unranked_statuses, **ranked_statuses}
    return {
        "commodity": commodity,
        "location": location,
        "location_id": str(location_id) if location_id else None,
        "origin": (
            {
                "latitude": origin[0],
                "longitude": origin[1],
                "location": origin_location.name if origin_location else None,
                "location_id": str(origin_location.id) if origin_location else None,
                "source": origin_source,
            }
            if origin is not None
            else None
        ),
        "origin_source": origin_source,
        "radius_km": radius_km,
        "delivery_month": delivery_month,
        "currency": ranked["currency"],
        "unit": ranked["unit"],
        "ranked": ranked["ranked"],
        "unranked": ranked["unranked"],
        "row_count": ranked["row_count"],
        "unranked_count": ranked["unranked_count"],
        "excluded_unknown_distance": ranked["excluded_unknown_distance"],
        "excluded_outside_radius": ranked["excluded_outside_radius"],
        "data_quality": ranked["data_quality"],
        "source_statuses": source_statuses,
        "source_status_note": SOURCE_STATUS_NOTE,
        "note": (
            "Basis = stored cash price (per bushel) minus stored futures "
            "price. Rows without a cash or futures price are listed under "
            "unranked with a missing-data reason; no basis is estimated. "
            "Rank 1 is the strongest (highest) basis."
        ),
    }


@router.get("/history")
def basis_history(
    commodity: str | None = Query(None),
    location_id: uuid.UUID | None = Query(None),
    limit: int = Query(90, ge=1, le=500),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    pairs = _load_price_pairs(db, org_id=context.org_id)
    history = build_basis_history(
        pairs,
        commodity=commodity,
        location_id=location_id,
        limit=limit,
    )
    status_map = _load_source_status_map(db, org_id=context.org_id)
    _attach_source_status(history["rows"], status_map)
    return {
        "commodity": commodity,
        "location_id": history["location_id"],
        "limit": limit,
        "currency": history["currency"],
        "unit": history["unit"],
        "row_count": history["row_count"],
        "missing_count": history["missing_count"],
        "rows": history["rows"],
        "data_quality": history["data_quality"],
        "source_status_note": SOURCE_STATUS_NOTE,
        "note": (
            "Basis over time, oldest quote first, from stored normalized "
            "prices. Rows without a cash or futures price are kept with "
            "basis null and a missing-data reason."
        ),
    }
