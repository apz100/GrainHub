"""Source-health dashboard routes (read-only).

GET /api/source-health          — one row per price source
GET /api/source-health/summary  — counts by status

Status is computed ONLY from real rows already in the database:
``ingestion_runs`` and ``source_health_snapshots`` (plus the ``sources``
table itself for the roster, last-error and failure counters). No probe
is performed here and no status is ever invented: a source with no
ingestion run and no snapshot is reported as ``unknown`` with an
explicit note.

Status rules (deterministic, documented here so the dashboard and the
tests agree):

* ``unknown`` — no ingestion run and no snapshot on record, or the
  latest run is still ``running`` with nothing completed yet.
* ``broken``  — the latest completed run failed, or the latest
  snapshot says failed/broken.
* ``stale``   — the latest run completed, but the last successful
  fetch is older than ``max(60, 2 * polling_interval_minutes)``
  minutes ago.
* ``live``    — the latest run completed successfully within the
  staleness window.

Probe results (``app/services/price_source_probe.py``) are a manual
CLI smoke test and are not persisted to any table, so they cannot
contribute rows here; when that changes, add them as a third input
to :func:`build_source_health_rows` instead of inventing a status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.request_context import RequestContext, get_request_context
from app.db.session import get_db
from app.models.ingestion_run import IngestionRun
from app.models.source import Source
from app.models.source_health_snapshot import SourceHealthSnapshot

router = APIRouter(prefix="/api/source-health", tags=["source-health"])

STATUSES = ("live", "stale", "broken", "unknown")

_NO_DATA_NOTE = "No ingestion data recorded yet — status unknown until the first run."
_RUNNING_NOTE = "Ingestion run in progress; no completed run on record yet."


def _stale_after_minutes(source: Source | None) -> int:
    interval = int(getattr(source, "polling_interval_minutes", 15) or 15)
    return max(60, 2 * interval)


def _parse_rate(run: IngestionRun | None, snapshot: SourceHealthSnapshot | None) -> float | None:
    if run is not None and run.parse_success_rate is not None:
        return float(run.parse_success_rate)
    if snapshot is not None and snapshot.parse_success_rate is not None:
        return float(snapshot.parse_success_rate)
    return None


def _snapshot_status(snapshot: SourceHealthSnapshot) -> str:
    raw = (snapshot.status or "").strip().lower()
    if raw in STATUSES:
        return raw
    if raw == "completed":
        return "live"
    if raw in {"failed", "failure", "error"}:
        return "broken"
    return "unknown"


def classify_source_status(
    *,
    source: Source | None,
    latest_run: IngestionRun | None,
    latest_snapshot: SourceHealthSnapshot | None,
    now: datetime,
) -> tuple[str, str]:
    """Return ``(status, note)`` for one source from its real DB rows."""
    if latest_run is not None:
        if latest_run.status == "failed":
            return "broken", "Latest ingestion run failed."
        if latest_run.status == "completed":
            completed_at = latest_run.completed_at or latest_run.started_at
            if completed_at is not None:
                age_minutes = (now - completed_at).total_seconds() / 60
                if age_minutes > _stale_after_minutes(source):
                    return (
                        "stale",
                        "Latest successful fetch is older than the staleness window.",
                    )
                return "live", "Latest ingestion run completed successfully."
            return "live", "Latest ingestion run completed successfully."
        if latest_run.status == "running":
            if latest_snapshot is not None:
                status = _snapshot_status(latest_snapshot)
                if status != "unknown":
                    return status, "Latest snapshot status (run still in progress)."
            return "unknown", _RUNNING_NOTE
        # Any other recorded run status: fall through to the snapshot.
    if latest_snapshot is not None:
        status = _snapshot_status(latest_snapshot)
        if status != "unknown":
            return status, "Latest source-health snapshot status."
    return "unknown", _NO_DATA_NOTE


def build_source_health_rows(
    sources: list[Source],
    runs: list[IngestionRun],
    snapshots: list[SourceHealthSnapshot],
    now: datetime,
) -> list[dict[str, Any]]:
    """One health row per source, plus rows for any run with no source.

    ``runs``/``snapshots`` are expected newest-first; only the newest
    row per source is used. Rows are never invented: a source with no
    run and no snapshot gets status ``unknown``.
    """
    runs_by_name: dict[str, IngestionRun] = {}
    for run in runs:
        runs_by_name.setdefault(run.source_name, run)
    snapshots_by_source: dict[str, SourceHealthSnapshot] = {}
    for snap in snapshots:
        snapshots_by_source.setdefault(str(snap.source_id), snap)

    rows: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for source in sources:
        seen_names.add(source.name)
        run = runs_by_name.get(source.name)
        snapshot = snapshots_by_source.get(str(source.id))
        status, note = classify_source_status(
            source=source, latest_run=run, latest_snapshot=snapshot, now=now
        )
        last_fetch = None
        if run is not None:
            last_fetch = run.completed_at or run.started_at
        elif snapshot is not None:
            last_fetch = snapshot.captured_at
        last_error = None
        if run is not None and run.error_message:
            last_error = run.error_message
        elif source.latest_error_message:
            last_error = source.latest_error_message
        rows.append(
            {
                "source_id": str(source.id),
                "name": source.name,
                "url": source.url,
                "status": status,
                "last_fetch_at": last_fetch.isoformat() if last_fetch else None,
                "parse_success_rate": _parse_rate(run, snapshot),
                "last_error": last_error,
                "consecutive_failures": int(source.consecutive_failures or 0),
                "note": note,
            }
        )

    # Ingestion runs for a source that is not (or no longer) in the
    # sources table still get a row — the data exists, so it is shown,
    # labelled as unregistered rather than dropped.
    for name, run in runs_by_name.items():
        if name in seen_names:
            continue
        status, note = classify_source_status(
            source=None, latest_run=run, latest_snapshot=None, now=now
        )
        rows.append(
            {
                "source_id": None,
                "name": name,
                "url": None,
                "status": status,
                "last_fetch_at": (run.completed_at or run.started_at).isoformat()
                if (run.completed_at or run.started_at)
                else None,
                "parse_success_rate": _parse_rate(run, None),
                "last_error": run.error_message,
                "consecutive_failures": None,
                "note": f"{note} (Source is not registered in the sources table.)",
            }
        )
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def summarize_statuses(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in STATUSES}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    counts["total"] = len(rows)
    return counts


@router.get("")
def list_source_health(
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    sources = (
        db.execute(select(Source).where(Source.org_id == context.org_id))
        .scalars()
        .all()
    )
    runs = (
        db.execute(
            select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(500)
        )
        .scalars()
        .all()
    )
    snapshots = (
        db.execute(
            select(SourceHealthSnapshot)
            .order_by(SourceHealthSnapshot.captured_at.desc())
            .limit(500)
        )
        .scalars()
        .all()
    )
    rows = build_source_health_rows(list(sources), list(runs), list(snapshots), now)
    return {
        "sources": rows,
        "count": len(rows),
        "generated_at": now.isoformat(),
        "note": (
            "Statuses come only from ingestion_runs and "
            "source_health_snapshots in the database. A source with no "
            "recorded run or snapshot is 'unknown', never assumed live."
        ),
    }


@router.get("/summary")
def source_health_summary(
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    result = list_source_health(context=context, db=db)
    return {
        "counts": summarize_statuses(result["sources"]),
        "generated_at": result["generated_at"],
    }
