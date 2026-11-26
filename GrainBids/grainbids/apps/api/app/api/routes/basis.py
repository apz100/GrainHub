"""Basis tracker routes (Cycle 2).

GET /api/basis/tracker -- rank the latest basis per location for a
commodity + delivery month, optionally within a radius of an origin.
GET /api/basis/history -- basis over time for one location + commodity.

Basis is always computed from stored normalized prices (cash minus
futures, per bushel); nothing is estimated. Prices carry their
stored source currency (migration 0022) when the source records one;
rows without one report ``currency: null`` with
``currency_unknown: true``, rather than assuming CAD or USD. Ranked
rows are grouped by currency and never compared across currencies;
no conversion is applied here.

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
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, defer

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
from app.services.market_canonicalization import canonical_key

router = APIRouter(prefix="/api/basis", tags=["basis"])


# Upper bound on the (price, snapshot) pairs the legacy loader below
# returns. Both /tracker (latest basis per location) and /history answer
# from the newest captures, and pairs arrive newest-first, so a cap only
# binds for an org with more stored pairs than this — in which case
# the routes say so in their data_quality note instead of pretending
# the whole history was scanned. The cap exists because the load used
# to be unbounded: on 2026-11-19 the production basis tracker took
# the free-tier API instance down three times in a row (HTTP 502,
# instance dead afterwards) while every other endpoint stayed up.
MAX_PRICE_PAIRS = 100_000

# Bounds for the SQL-reduced loaders the basis routes actually use
# (see _load_latest_pairs_per_group / _load_history_pairs). The
# 100k-pair cap above was not enough: after it shipped, production
# OOM'd again on 2026-11-19 23:46 EST — Render recorded "Ran out of
# memory (used over 512MB)" and restarted the instance — because
# 100,000 SQLAlchemy entity pairs is still far too much for the
# 512 MB free instance at production data volume. The reduced loaders
# therefore bound by *groups*, not pairs: the tracker materializes at
# most one pair per (location, commodity, delivery) group and history
# at most ``limit`` pairs per (location, commodity) group. These caps
# are defensive only — real group counts are orders of magnitude
# smaller — and the routes say so in their data_quality note if one
# ever binds.
MAX_TRACKER_GROUPS = 20_000
MAX_HISTORY_PAIRS = 25_000


def _pairs_from_rows(rows) -> list[tuple[NormalizedPrice, PriceSnapshot | None]]:
    """Consume execute() rows as (price, snapshot) pairs.

    Real SQLAlchemy Rows are NOT tuple instances (checked 2026-11-20),
    so an isinstance(item, tuple) gate here silently discarded every
    row from a real database — the endpoints only ever "worked"
    against the fake sessions in tests, which return plain tuples.
    Rows and tuples both unpack by index, so index directly.
    """
    pairs: list[tuple[NormalizedPrice, PriceSnapshot | None]] = []
    for item in rows:
        if isinstance(item, NormalizedPrice):
            pairs.append((item, None))
        else:
            pairs.append((item[0], item[1]))
    return pairs


def _load_price_pairs(
    db: Session, *, org_id: uuid.UUID
) -> list[tuple[NormalizedPrice, PriceSnapshot | None]]:
    """(price, snapshot) pairs for the org, newest snapshot first.

    Two deliberate bounds (see MAX_PRICE_PAIRS): the snapshot's
    ``raw_payload_json`` is deferred — nothing in the basis paths
    reads it, and it is the one unbounded-size field (a whole day
    file per snapshot) — and the result is capped at the newest
    MAX_PRICE_PAIRS pairs. The deferred attribute would still
    lazy-load if anything ever accessed it, so behaviour is
    unchanged apart from the cap.

    Retained as the bounded full-history primitive (pinned by
    tests/test_basis_pair_loading.py); the basis routes themselves
    use the SQL-reduced loaders below, which materialize far fewer
    pairs at production data volume.
    """
    rows = db.execute(
        select(NormalizedPrice, PriceSnapshot)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(Source, Source.id == PriceSnapshot.source_id)
        .where(Source.org_id == org_id)
        .order_by(desc(PriceSnapshot.captured_at))
        .options(defer(PriceSnapshot.raw_payload_json))
        .limit(MAX_PRICE_PAIRS)
    ).all()
    return _pairs_from_rows(rows)


def _latest_group_subquery(*, org_id: uuid.UUID, location_id: uuid.UUID | None):
    """Ids of the newest price row per tracker group, via row_number().

    The partition is (location_id, location, commodity_name,
    futures_month, delivery_label, delivery_end) — deliberately finer
    than every key the tracker service groups or filters by:

    * ``rank_basis`` ranks the latest row per location *after*
      filtering on the canonical commodity and on the delivery-month
      keys a row claims. Canonical commodity and claimed month keys
      are pure functions of (commodity_name, futures_month,
      delivery_label, delivery_end), so they are constant within a
      partition, and a partition's newest row is the only one that
      can win its location once the filters pass. Reducing to the
      newest row per partition therefore cannot change the ranking —
      it only skips rows the service would discard anyway.
    * Partitioning by the raw location string as well as its id keeps
      the reduction a superset for rows whose stored location_id is
      NULL (the service keys those by canonical location name).

    A window function is used rather than Postgres DISTINCT ON so the
    same statement runs on SQLite in the real-DB tests.
    """
    row_number = func.row_number().over(
        partition_by=(
            NormalizedPrice.location_id,
            NormalizedPrice.location,
            NormalizedPrice.commodity_name,
            NormalizedPrice.futures_month,
            NormalizedPrice.delivery_label,
            NormalizedPrice.delivery_end,
        ),
        order_by=(
            desc(PriceSnapshot.captured_at),
            desc(NormalizedPrice.created_at),
            desc(NormalizedPrice.id),
        ),
    )
    stmt = (
        select(NormalizedPrice.id.label("price_id"), row_number.label("rn"))
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(Source, Source.id == PriceSnapshot.source_id)
        .where(Source.org_id == org_id)
    )
    if location_id is not None:
        stmt = stmt.where(NormalizedPrice.location_id == location_id)
    return stmt.subquery()


def _load_latest_pairs_per_group(
    db: Session, *, org_id: uuid.UUID, location_id: uuid.UUID | None = None
) -> tuple[list[tuple[NormalizedPrice, PriceSnapshot | None]], bool]:
    """Newest (price, snapshot) pair per tracker group, newest first.

    Returns (pairs, truncated): ``truncated`` is True when the org has
    more than MAX_TRACKER_GROUPS groups and only the newest groups
    were loaded, so the route can say so in its data_quality note.
    The snapshot's ``raw_payload_json`` is never selected into the
    entities (deferred, as in the legacy loader).
    """
    groups = _latest_group_subquery(org_id=org_id, location_id=location_id)
    rows = db.execute(
        select(NormalizedPrice, PriceSnapshot)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(groups, groups.c.price_id == NormalizedPrice.id)
        .where(groups.c.rn == 1)
        .order_by(desc(PriceSnapshot.captured_at))
        .options(defer(PriceSnapshot.raw_payload_json))
        .limit(MAX_TRACKER_GROUPS + 1)
    ).all()
    truncated = len(rows) > MAX_TRACKER_GROUPS
    return _pairs_from_rows(rows[:MAX_TRACKER_GROUPS]), truncated


def _load_history_pairs(
    db: Session, *, org_id: uuid.UUID, location_id: uuid.UUID | None, limit: int
) -> tuple[list[tuple[NormalizedPrice, PriceSnapshot | None]], bool]:
    """Oldest-first candidate pairs for /history, bounded in SQL.

    History serves the oldest ``limit`` quotes for one location +
    commodity, so — unlike the tracker — it genuinely needs more
    than the latest row per group. The bound is therefore per group:
    a row_number() window partitioned by (location_id, commodity_name)
    keeps each group's first ``limit`` rows in the service's own
    selection order — quote *date* oldest first (``build_basis_history``
    sorts by date, not timestamp), newest capture first within a day
    (the service's sort is stable over the legacy loader's
    newest-first hand-off, so within one date the legacy path serves
    that day's newest captures). Keeping the window in the same order
    means the candidate set is exactly the per-group prefix the
    service could select from the full load, so results are unchanged;
    the commodity/location filters are constant within a partition
    (canonical commodity is a pure function of the raw name), so no
    selectable row is reduced away. Candidates are handed over
    newest-first, matching the legacy loader's order. A defensive
    total cap (MAX_HISTORY_PAIRS, trimmed in the same selection
    order) guards orgs with very many groups; ``truncated`` reports
    if it bound.
    """
    row_number = func.row_number().over(
        partition_by=(
            NormalizedPrice.location_id,
            NormalizedPrice.commodity_name,
        ),
        order_by=(
            func.date(PriceSnapshot.captured_at),
            desc(PriceSnapshot.captured_at),
            desc(NormalizedPrice.created_at),
            desc(NormalizedPrice.id),
        ),
    )
    stmt = (
        select(NormalizedPrice.id.label("price_id"), row_number.label("rn"))
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(Source, Source.id == PriceSnapshot.source_id)
        .where(Source.org_id == org_id)
    )
    if location_id is not None:
        stmt = stmt.where(NormalizedPrice.location_id == location_id)
    groups = stmt.subquery()
    rows = db.execute(
        select(NormalizedPrice, PriceSnapshot)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(groups, groups.c.price_id == NormalizedPrice.id)
        .where(groups.c.rn <= limit)
        .order_by(
            func.date(PriceSnapshot.captured_at),
            desc(PriceSnapshot.captured_at),
        )
        .options(defer(PriceSnapshot.raw_payload_json))
        .limit(MAX_HISTORY_PAIRS + 1)
    ).all()
    truncated = len(rows) > MAX_HISTORY_PAIRS
    # Rows arrive in the service's selection order so the defensive
    # cap keeps the candidates history would serve first; re-sort to
    # hand the service the legacy loader's newest-first order (its
    # date sort is stable, so hand-off order decides within a day).
    pairs = _pairs_from_rows(rows[:MAX_HISTORY_PAIRS])
    pairs.sort(
        key=lambda pair: (
            pair[1].captured_at if pair[1] is not None else pair[0].created_at
        ),
        reverse=True,
    )
    return pairs, truncated


def _count_missing_basis_by_commodity(
    db: Session, *, org_id: uuid.UUID, location_id: uuid.UUID | None
) -> dict[str | None, int] | None:
    """Stored rows per canonical commodity whose basis is not computable.

    ``build_basis_history`` counts missing rows among the pairs it is
    handed, but the history loader now hands it a bounded candidate
    set, so the count is computed over the whole org in SQL instead:
    a row's basis is not computable exactly when its cash or futures
    price is missing (NULL, or NaN — the one non-finite value a
    Postgres numeric column can hold, which ``compute_basis_for_row``
    also treats as missing; ``col != col`` is the NaN test).

    Returns None when the result is not the expected (name, count)
    shape — the fake sessions used in route tests dispatch on table
    names and answer every normalized_prices query with canned price
    pairs — so the caller falls back to the service's own count.
    """
    cash = NormalizedPrice.cash_price_bu
    futures = NormalizedPrice.futures_price
    stmt = (
        select(NormalizedPrice.commodity_name, func.count())
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(Source, Source.id == PriceSnapshot.source_id)
        .where(
            Source.org_id == org_id,
            or_(
                cash.is_(None),
                futures.is_(None),
                cash != cash,  # deliberate self-comparison: the NaN test
                futures != futures,  # deliberate self-comparison: NaN test
            ),
        )
        .group_by(NormalizedPrice.commodity_name)
    )
    if location_id is not None:
        stmt = stmt.where(NormalizedPrice.location_id == location_id)
    counts: dict[str | None, int] = {}
    for row in db.execute(stmt).all():
        name, count = row[0], row[1]
        if not isinstance(name, str) or not isinstance(count, int):
            return None
        key = canonical_key(name)
        counts[key] = counts.get(key, 0) + count
    return counts


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
    pairs, pairs_truncated = _load_latest_pairs_per_group(
        db, org_id=context.org_id, location_id=location_id
    )
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
    if pairs_truncated:
        ranked["data_quality"] = (
            str(ranked["data_quality"])
            + f" Note: only the newest {MAX_TRACKER_GROUPS} location / "
            "commodity / delivery groups were scanned; older history "
            "exists beyond this bound."
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
        "currencies": ranked["currencies"],
        "currency_unknown_count": ranked["currency_unknown_count"],
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
            "Rows are grouped by their stored currency; rank 1 is the "
            "strongest (highest) basis within its currency group."
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
    pairs, pairs_truncated = _load_history_pairs(
        db, org_id=context.org_id, location_id=location_id, limit=limit
    )
    # missing_count covers every matching stored row, not just the
    # bounded candidate set the service is handed, so it is counted in
    # SQL; when the count query's result shape is unusable (fake
    # sessions in route tests) the service's own count stands.
    missing_by_commodity = _count_missing_basis_by_commodity(
        db, org_id=context.org_id, location_id=location_id
    )
    missing_override: int | None = None
    if missing_by_commodity is not None:
        wanted = canonical_key(commodity) if commodity else None
        if wanted is None:
            missing_override = sum(missing_by_commodity.values())
        else:
            missing_override = missing_by_commodity.get(wanted, 0)
    history = build_basis_history(
        pairs,
        commodity=commodity,
        location_id=location_id,
        limit=limit,
        missing_count_override=missing_override,
    )
    if pairs_truncated:
        history["data_quality"] = (
            str(history["data_quality"])
            + f" Note: the scan was bounded to the oldest {MAX_HISTORY_PAIRS} "
            "candidate price pairs; older history exists beyond this bound."
        )
    status_map = _load_source_status_map(db, org_id=context.org_id)
    _attach_source_status(history["rows"], status_map)
    return {
        "commodity": commodity,
        "location_id": history["location_id"],
        "limit": limit,
        "currency": history["currency"],
        "currencies": history["currencies"],
        "currency_unknown_count": history["currency_unknown_count"],
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
