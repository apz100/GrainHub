"""Warm the USDA research cache on a schedule.

Background (first scheduled ingestion run, 46099501182, 2026-11-27):
the twice-daily "Scheduled ingestion" workflow never calls the USDA
APIs — it runs a file cycle (currently 0 sources) and the web poll —
so NASS_API_KEY / FAS_DATA_GOV_API_KEY sat unused there, and USDA
data was only fetched on demand when a research page (or anything
else) first asked for it. Emails, the newsletter, alerts and other
features cannot rely on that: they need the data already cached in
``research_cache_entries`` before they run.

This job pre-fetches exactly what the research routes cache, using
the same fetchers and the same ``(dataset, cache_key)`` pairs, so a
warmed row is byte-for-byte what the route would have stored on its
first live call:

- FAS PSD attribute + unit name tables (``fas_psd_attributes`` /
  ``fas_psd_units``, key ``all``) — the lookups that decode world rows.
- FAS PSD world tables (``fas_psd_world``, key ``{code}/{year}``) for
  the three commodities the web PSD page serves: Corn 0440000,
  Soybeans 2222000, Wheat 0410000.
- FAS PSD commodity catalogue (``fas_psd_commodities``, key ``{code}``)
  for the same three codes. (The upstream ignores the code and returns
  the full 63-row list every time; the rows are filtered client-side,
  exactly as the route does — three near-identical calls is the price
  of exact key parity with the route.)
- NASS Quick Stats series (``nass_series``, key ``{COMMODITY}/{year}``)
  for CORN / SOYBEANS / WHEAT — the same three grains.

The year is the current calendar year, matching the site's defaults
(the PSD page defaults to 2026; ``--year`` overrides it for a
backfill or a check).

Idempotency comes free from ``get_or_fetch``: the cache has a unique
``(dataset, cache_key)`` constraint and a fresh row is never
re-fetched, so re-running the job is a no-op while the TTLs hold
(24 h for world / commodities / NASS series, 7 days for the name
tables). A run therefore costs 11 upstream calls at most, and
usually zero.

Exit-code contract (same shape as ``poll_sources.run_once``): 0 when
the cycle completed and at least one dataset refreshed; 1 when
nothing refreshed at all (e.g. keys missing — a systemic config
failure worth a red run) or the job itself crashed. A single
dataset failing (upstream down, rate-limited) does not fail the
run — the stale row, if any, stays in place and the next scheduled
run retries it.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.db.session import get_sessionmaker
from app.services.research import (
    fetch_fas_psd,
    fetch_fas_psd_attribute_names,
    fetch_fas_psd_unit_names,
    fetch_fas_psd_world,
    fetch_nass_quick_stats,
    parse_fas_psd_rows,
    parse_nass_records,
)
from app.services.research_cache import get_or_fetch

# The commodities the web PSD page serves (apps/web/app/research/psd).
# PSD codes are the catalogue's own identifiers; NASS names are the
# Quick Stats commodity_desc values.
PSD_COMMODITIES: tuple[tuple[str, str], ...] = (
    ("0440000", "Corn"),
    ("2222000", "Soybeans"),
    ("0410000", "Wheat"),
)
NASS_COMMODITIES: tuple[str, ...] = ("CORN", "SOYBEANS", "WHEAT")


@dataclass(frozen=True)
class WarmTarget:
    dataset: str
    cache_key: str
    source: str
    fetcher: Callable[[], dict]


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _psd_names(db: Session | None, kind: str, *, dry_run: bool) -> dict[int, str]:
    """PSD attribute/unit name tables, exactly as the route resolves them.

    In a real run this goes through ``get_or_fetch`` (the name tables
    are themselves warm targets, warmed first, so this is a cache hit
    in practice). In dry-run mode there is no session, so the tables
    are fetched directly — the check still proves upstream
    reachability and decoding without writing anything.
    """
    if kind == "attributes":
        dataset, fetch_names = "fas_psd_attributes", fetch_fas_psd_attribute_names
    else:
        dataset, fetch_names = "fas_psd_units", fetch_fas_psd_unit_names
    if dry_run:
        return fetch_names()
    cached = get_or_fetch(
        db,
        dataset=dataset,
        cache_key="all",
        source="USDA FAS PSD",
        fetcher=lambda: {"names": {str(k): v for k, v in fetch_names().items()}},
    )
    return {int(k): str(v) for k, v in cached.payload.get("names", {}).items()}


def _fetch_psd_world(db: Session | None, code: str, year: int, *, dry_run: bool) -> dict:
    """Decoded world PSD table — the route's ``_fetch_world`` verbatim."""
    raw_rows = fetch_fas_psd_world(commodity_code=code, market_year=year)
    attributes = _psd_names(db, "attributes", dry_run=dry_run)
    units = _psd_names(db, "units", dry_run=dry_run)
    return {"rows": parse_fas_psd_rows(raw_rows, attribute_names=attributes, unit_names=units)}


def _fetch_nass_series(commodity: str, year: int) -> dict:
    """Parsed NASS series — the route's ``_fetch_series`` verbatim."""
    records = parse_nass_records(fetch_nass_quick_stats(commodity=commodity, year=year))
    return {"records": records, "total_records": len(records)}


def build_targets(db: Session | None, year: int, *, dry_run: bool = False) -> list[WarmTarget]:
    """All cache rows the research routes serve, in warm order.

    Name tables first: the world-table fetchers resolve their decode
    lookups through them.
    """
    targets: list[WarmTarget] = [
        WarmTarget(
            dataset="fas_psd_attributes", cache_key="all", source="USDA FAS PSD",
            fetcher=lambda: {"names": {str(k): v for k, v in fetch_fas_psd_attribute_names().items()}},
        ),
        WarmTarget(
            dataset="fas_psd_units", cache_key="all", source="USDA FAS PSD",
            fetcher=lambda: {"names": {str(k): v for k, v in fetch_fas_psd_unit_names().items()}},
        ),
    ]
    for code, _label in PSD_COMMODITIES:
        targets.append(
            WarmTarget(
                dataset="fas_psd_world", cache_key=f"{code}/{year}", source="USDA FAS PSD",
                fetcher=lambda code=code: _fetch_psd_world(db, code, year, dry_run=dry_run),
            )
        )
    for code, _label in PSD_COMMODITIES:
        targets.append(
            WarmTarget(
                dataset="fas_psd_commodities", cache_key=code, source="USDA FAS PSD",
                fetcher=lambda code=code: {"rows": fetch_fas_psd(commodity_code=code)},
            )
        )
    for commodity in NASS_COMMODITIES:
        targets.append(
            WarmTarget(
                dataset="nass_series", cache_key=f"{commodity}/{year}",
                source="USDA NASS Quick Stats",
                fetcher=lambda commodity=commodity: _fetch_nass_series(commodity, year),
            )
        )
    return targets


def run_once(*, year: int | None = None, dry_run: bool = False) -> int:
    """Warm every research-cache row once. Returns an exit code (0/1)."""
    year = year if year is not None else _current_year()
    session = None if dry_run else get_sessionmaker()()
    try:
        targets = build_targets(session, year, dry_run=dry_run)
        warmed = 0
        failed = 0
        for target in targets:
            try:
                if dry_run:
                    payload = target.fetcher()
                    rows = payload.get("rows", payload.get("records", []))
                    print(
                        f"warm dataset={target.dataset} key={target.cache_key} "
                        f"state=dry-run rows={len(rows)}"
                    )
                else:
                    cached = get_or_fetch(
                        session,
                        dataset=target.dataset,
                        cache_key=target.cache_key,
                        source=target.source,
                        fetcher=target.fetcher,
                    )
                    print(
                        f"warm dataset={target.dataset} key={target.cache_key} "
                        f"state={cached.cache_state}"
                    )
                warmed += 1
            except Exception as exc:  # noqa: BLE001 - per-dataset failure, not a crash
                print(
                    f"warm_failed dataset={target.dataset} key={target.cache_key} "
                    f"error={exc!r}"
                )
                failed += 1
        print(f"warmed={warmed} failed={failed} year={year} dry_run={dry_run}")
        # 0 means "the cycle ran"; 1 means "nothing was cached at all"
        # (keys missing, both upstreams down) or the job crashed below.
        return 0 if warmed > 0 else 1
    except Exception as exc:  # noqa: BLE001 - systemic failure, not a dataset failure
        print(f"warmup_failed error={exc!r}")
        return 1
    finally:
        if session is not None:
            session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Warm the USDA research cache.")
    parser.add_argument(
        "--year", type=int, default=None,
        help="Marketing / NASS year to warm (default: current year).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch from USDA and report row counts without writing to the DB.",
    )
    args = parser.parse_args()
    return run_once(year=args.year, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
