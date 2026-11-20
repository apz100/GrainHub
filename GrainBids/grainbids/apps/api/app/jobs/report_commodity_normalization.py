"""Dry-run-only commodity normalization report (Marathon Phase B).

Usage: ``python -m app.jobs.report_commodity_normalization``

Read-time resolution (``app.services.commodity_normalization``) means
stored ``normalized_prices.commodity_name`` values never need a
backfill for search and facets to group canonically. This job exists
to make the mapping auditable: it lists every distinct stored
commodity label, the canonical commodity it resolves to, and —
separately — the labels that stay unmapped because they are
ambiguous or unrecognized, with the reason for each. Those are the
labels a human can pin via the ``commodity_aliases`` table
(migration 0020) if they choose.

The job NEVER writes. There is no --apply flag on purpose.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_sessionmaker
from app.models.normalized_price import NormalizedPrice
from app.services.commodity_normalization import resolve_commodity_name


def run(db: Session) -> int:
    rows = db.execute(
        select(NormalizedPrice.commodity_name, func.count(NormalizedPrice.id))
        .group_by(NormalizedPrice.commodity_name)
        .order_by(NormalizedPrice.commodity_name)
    ).all()

    mapped: list[tuple[str, str, int]] = []
    ambiguous: list[tuple[str, str, int]] = []
    unmapped: list[tuple[str, str, int]] = []
    group_counts: Counter[str] = Counter()
    for raw, count in rows:
        resolution = resolve_commodity_name(raw, db=db)
        if resolution is None:
            continue
        if resolution.canonical is not None:
            mapped.append((raw, resolution.display_name, int(count)))
            group_counts[resolution.canonical] += int(count)
        elif resolution.ambiguous:
            ambiguous.append((raw, resolution.reason or "", int(count)))
        else:
            unmapped.append((raw, resolution.reason or "", int(count)))

    print(f"distinct_labels={len(rows)} mapped={len(mapped)} "
          f"ambiguous={len(ambiguous)} unmapped={len(unmapped)}")
    print("canonical groups (by stored rows):")
    for canonical, total in group_counts.most_common():
        print(f"  {canonical}: {total}")
    print("mapped labels:")
    for raw, display, count in mapped:
        print(f"  {raw!r} -> {display!r} ({count} rows)")
    if ambiguous:
        print("AMBIGUOUS — not guessed (pin via commodity_aliases if wanted):")
        for raw, reason, count in ambiguous:
            print(f"  {raw!r} ({count} rows): {reason}")
    if unmapped:
        print("UNMAPPED — no rule and no override:")
        for raw, reason, count in unmapped:
            print(f"  {raw!r} ({count} rows): {reason}")
    print("dry_run=true — this job never writes")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report how stored commodity labels resolve to canonical commodities (read-only)."
    )
    parser.parse_args()
    session_factory = get_sessionmaker()
    with session_factory() as db:
        return run(db)


if __name__ == "__main__":
    sys.exit(main())
