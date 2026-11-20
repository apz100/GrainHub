from __future__ import annotations

import math
from datetime import date
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.normalized_prices import (
    _group_preview_rows_by_delivery,
    _load_preview_payload,
    _month_sort_key_value,
)
from app.core.request_context import RequestContext, get_request_context
from app.db.session import get_db
from app.models.location import Location
from app.services.market_canonicalization import canonical_key, normalize_text

router = APIRouter(prefix="/api/market-search", tags=["market-search"])

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two lat/lng points."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def parse_delivery_month(value: str | None) -> int | None:
    """Parse a delivery month into the repo's month sort key (year*12+month).

    Accepts "YYYY-MM", "Month YYYY" and "Month" (month-only, year 9999
    sentinel, matching ``_month_sort_key_value``). Returns None for
    blank input; raises ValueError for an unrecognised value.
    """
    normalized = normalize_text(value)
    if normalized is None:
        return None
    iso_match = re.fullmatch(r"(\d{4})-(\d{1,2})", normalized)
    if iso_match:
        year = int(iso_match.group(1))
        month = int(iso_match.group(2))
        if 1 <= month <= 12:
            return year * 12 + month
        raise ValueError(f"Unrecognised delivery month: {value!r}")
    key = _month_sort_key_value(normalized)
    if key is None:
        raise ValueError(f"Unrecognised delivery month: {value!r}")
    return key


def _row_delivery_month_key(row: dict[str, object]) -> int | None:
    for field in ("delivery_label", "futures_month"):
        key = _month_sort_key_value(str(row.get(field)) if row.get(field) else None)
        if key is not None:
            return key
    return None


def _resolve_origin(
    db: Session,
    *,
    org_id: uuid.UUID,
    latitude: float | None,
    longitude: float | None,
    location: str | None,
    location_id: uuid.UUID | None,
) -> tuple[float, float] | None:
    if latitude is not None and longitude is not None:
        return latitude, longitude
    if latitude is not None or longitude is not None:
        raise HTTPException(
            status_code=400,
            detail="latitude and longitude must be supplied together for a radius search.",
        )
    target: Location | None = None
    if location_id is not None:
        target = db.execute(
            select(Location).where(Location.org_id == org_id, Location.id == location_id)
        ).scalar_one_or_none()
    elif location:
        wanted = canonical_key(location)
        candidates = db.execute(
            select(Location).where(Location.org_id == org_id)
        ).scalars().all()
        for candidate in candidates:
            if canonical_key(candidate.name) == wanted:
                target = candidate
                break
    if target is None:
        return None
    if target.latitude is None or target.longitude is None:
        return None
    return float(target.latitude), float(target.longitude)


@router.get("")
def market_search(
    commodity: str | None = Query(None),
    location: str | None = Query(None),
    location_id: uuid.UUID | None = Query(None),
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
    radius_km: float | None = Query(None, gt=0, le=2000),
    delivery_month: str | None = Query(None),
    top_n: int = Query(30, ge=1, le=30),
    limit: int = Query(250, ge=1, le=250),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    try:
        delivery_key = parse_delivery_month(delivery_month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    origin: tuple[float, float] | None = None
    if radius_km is not None:
        origin = _resolve_origin(
            db,
            org_id=context.org_id,
            latitude=latitude,
            longitude=longitude,
            location=location,
            location_id=location_id,
        )
        if origin is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "radius_km needs an origin with coordinates: supply latitude "
                    "and longitude, or a location / location_id whose stored "
                    "location has latitude and longitude."
                ),
            )

    rows = _load_preview_payload(
        context=context,
        db=db,
        commodity=commodity,
        location=location,
        source_name=None,
        region=None,
        company_id=None,
        location_id=location_id,
        captured_date=None,
        include_non_canonical=False,
        sort="cash_bu_desc",
        limit=limit,
    )

    excluded_unknown_distance = 0
    if origin is not None and radius_km is not None:
        location_ids = {
            row["location_id"]
            for row in rows
            if isinstance(row.get("location_id"), str) and row["location_id"]
        }
        coords: dict[str, tuple[float, float]] = {}
        if location_ids:
            for loc in db.execute(
                select(Location).where(Location.id.in_([uuid.UUID(v) for v in location_ids]))
            ).scalars().all():
                if loc.latitude is not None and loc.longitude is not None:
                    coords[str(loc.id)] = (float(loc.latitude), float(loc.longitude))
        kept: list[dict[str, object]] = []
        for row in rows:
            loc_id = row.get("location_id")
            point = coords.get(str(loc_id)) if isinstance(loc_id, str) else None
            if point is None:
                excluded_unknown_distance += 1
                continue
            if haversine_km(origin[0], origin[1], point[0], point[1]) <= radius_km:
                kept.append(row)
        rows = kept

    if delivery_key is not None:
        rows = [row for row in rows if _row_delivery_month_key(row) == delivery_key]

    groups = _group_preview_rows_by_delivery(rows, rows_per_group=top_n)
    return {
        "commodity": commodity,
        "location": location,
        "origin": {"latitude": origin[0], "longitude": origin[1]} if origin else None,
        "radius_km": radius_km,
        "delivery_month": delivery_month,
        "top_n_per_month": top_n,
        "row_count": len(rows),
        "excluded_unknown_distance": excluded_unknown_distance,
        "groups": groups,
        "note": (
            "Canonical latest rows only, deterministically deduped by "
            "location + company + commodity + delivery month + futures month. "
            "Rows without stored coordinates are excluded from radius searches."
        ),
    }
