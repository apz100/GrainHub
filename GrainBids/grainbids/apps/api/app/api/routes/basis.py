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
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.routes.market_search import parse_delivery_month
from app.core.request_context import RequestContext, get_request_context
from app.db.session import get_db
from app.models.location import Location
from app.models.normalized_price import NormalizedPrice
from app.models.price_snapshot import PriceSnapshot
from app.models.source import Source
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
        "note": (
            "Basis over time, oldest quote first, from stored normalized "
            "prices. Rows without a cash or futures price are kept with "
            "basis null and a missing-data reason."
        ),
    }
