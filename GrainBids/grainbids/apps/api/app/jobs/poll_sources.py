from __future__ import annotations

from datetime import datetime, timezone
import time

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models.commodity import Commodity
from app.services.source_orchestration import poll_due_sources


def _default_commodity_id(db) -> str:
    commodity = db.execute(select(Commodity).order_by(Commodity.created_at.asc()).limit(1)).scalar_one_or_none()
    if commodity is None:
        raise RuntimeError("No commodity exists; create at least one commodity before polling sources.")
    return commodity.id


def run_once() -> int:
    # Exit-code contract (changed 2026-11-28, first scheduled run):
    # 0 means "the poll ran to completion"; per-source failures do NOT
    # fail the run — each source's outcome is already recorded in
    # /api/source-health (status + consecutive_failures + last_error).
    # The old rule (exit 1 unless every source passed) made the first
    # scheduled run report FAILURE with 71/101 sources live, and would
    # keep every future run red until 101/101 sources are green at
    # once — which never happens while any elevator site is down or
    # changes its page. A red run now means the poll itself crashed
    # (DB down, bad config, unhandled exception), which is the signal
    # worth paging on.
    session = get_sessionmaker()()
    try:
        commodity_id = _default_commodity_id(session)
        results = poll_due_sources(session, commodity_id=commodity_id, now=datetime.now(timezone.utc))
    except Exception as exc:  # noqa: BLE001 - systemic failure, not a source failure
        print(f"poll_failed error={exc!r}")
        return 1
    finally:
        session.close()
    failed = sum(1 for result in results if result.status != "completed")
    print(f"polled={len(results)} failed={failed}")
    return 0


def run_loop(sleep_seconds: int = 60) -> int:
    while True:
        exit_code = run_once()
        print(f"cycle_exit={exit_code} sleeping={sleep_seconds}s")
        time.sleep(max(5, sleep_seconds))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Poll due GrainBids sources.")
    parser.add_argument("--loop", action="store_true", help="Run continuously.")
    parser.add_argument("--sleep-seconds", type=int, default=60, help="Loop delay in seconds.")
    args = parser.parse_args()

    if args.loop:
        return run_loop(sleep_seconds=args.sleep_seconds)
    return run_once()


if __name__ == "__main__":
    raise SystemExit(main())
