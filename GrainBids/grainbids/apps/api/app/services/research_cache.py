"""DB-backed cache for USDA reference data (Marathon Phase C).

The research routes call USDA FAS PSD / NASS Quick Stats live. Those
upstreams are slow and rate-limited, and the same world table is
requested on every page load — so decoded responses are cached in
``research_cache_entries`` and served until their TTL expires:

- PSD world tables and NASS series: 24 h (USDA revises monthly /
  weekly; a day of staleness is labelled in the response via
  ``fetched_at`` and ``cache_state``).
- PSD attribute / unit lookup tables: 7 days (they change rarely,
  and a stale name table only affects labels, never values).

``get_or_fetch`` is deliberately small: fresh row → return it;
missing/stale → call the fetcher, store, return. A fetcher failure
propagates (the route maps it to 502/503) and never poisons the
cache — a stale row, when one exists, is returned with
``cache_state="stale"`` instead of failing the request outright.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research_cache import ResearchCacheEntry

TTL_HOURS: dict[str, float] = {
    "fas_psd_world": 24,
    "fas_psd_commodities": 24,
    "fas_psd_attributes": 24 * 7,
    "fas_psd_units": 24 * 7,
    "nass_series": 24,
}
DEFAULT_TTL_HOURS = 24.0


@dataclass(frozen=True)
class CachedPayload:
    payload: dict
    cache_state: str  # "hit" | "fetched" | "stale"
    fetched_at: datetime


def _ttl_for(dataset: str) -> timedelta:
    return timedelta(hours=TTL_HOURS.get(dataset, DEFAULT_TTL_HOURS))


def _is_fresh(entry: ResearchCacheEntry, dataset: str, now: datetime) -> bool:
    fetched_at = entry.fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return now - fetched_at < _ttl_for(dataset)


def get_or_fetch(
    db: Session,
    *,
    dataset: str,
    cache_key: str,
    source: str,
    fetcher: Callable[[], dict],
) -> CachedPayload:
    """Return the cached payload for (dataset, cache_key) or fetch it.

    ``fetcher`` performs the live upstream call and returns the
    decoded payload dict. Its exceptions propagate unless a stale
    cached row exists, which is then returned as ``cache_state=
    "stale"`` so a USDA outage degrades to old data, not an error.
    """
    now = datetime.now(timezone.utc)
    entry = db.execute(
        select(ResearchCacheEntry).where(
            ResearchCacheEntry.dataset == dataset,
            ResearchCacheEntry.cache_key == cache_key,
        )
    ).scalars().first()
    if entry is not None and _is_fresh(entry, dataset, now):
        return CachedPayload(payload=entry.payload, cache_state="hit", fetched_at=entry.fetched_at)
    try:
        payload = fetcher()
    except Exception:
        if entry is not None:
            return CachedPayload(
                payload=entry.payload, cache_state="stale", fetched_at=entry.fetched_at
            )
        raise
    fetched_at = datetime.now(timezone.utc)
    if entry is None:
        entry = ResearchCacheEntry(
            dataset=dataset, cache_key=cache_key, payload=payload, source=source,
            fetched_at=fetched_at,
        )
        db.add(entry)
    else:
        entry.payload = payload
        entry.source = source
        entry.fetched_at = fetched_at
    db.commit()
    return CachedPayload(payload=payload, cache_state="fetched", fetched_at=fetched_at)
