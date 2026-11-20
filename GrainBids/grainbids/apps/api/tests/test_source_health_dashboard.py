"""Source-health dashboard tests.

Route tests run the source_health router standalone with the DB and
request-context dependencies overridden by fakes (same pattern as
tests/test_advisor.py). The fake session dispatches on the queried
table so the routes only ever see real rows the test put in.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.source_health import (  # noqa: E402
    classify_source_status,
    router as source_health_router,
)
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.ingestion_run import IngestionRun  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.models.source_health_snapshot import SourceHealthSnapshot  # noqa: E402

ORG_ID = uuid.uuid4()


def _now() -> datetime:
    # Anchor fixtures to the real clock: the routes classify against
    # datetime.now(timezone.utc), so fixed dates would drift stale.
    return datetime.now(timezone.utc)


def _source(name: str, **overrides) -> Source:
    values = {
        "id": uuid.uuid4(),
        "org_id": ORG_ID,
        "name": name,
        "url": f"https://example.com/{name.lower().replace(' ', '-')}",
        "polling_interval_minutes": 15,
        "consecutive_failures": 0,
        "latest_error_message": None,
    }
    values.update(overrides)
    return Source(**values)


def _run(name: str, *, status: str, minutes_ago: int, **overrides) -> IngestionRun:
    started = _now() - timedelta(minutes=minutes_ago)
    values = {
        "id": uuid.uuid4(),
        "source_name": name,
        "source_identifier": "https://example.com",
        "started_at": started,
        "completed_at": started if status != "running" else None,
        "status": status,
        "trigger_type": "manual",
        "parse_success_rate": Decimal("0.950"),
        "error_message": None,
    }
    values.update(overrides)
    return IngestionRun(**values)


def _snapshot(source: Source, *, status: str, minutes_ago: int) -> SourceHealthSnapshot:
    return SourceHealthSnapshot(
        id=uuid.uuid4(),
        source_id=source.id,
        captured_at=_now() - timedelta(minutes=minutes_ago),
        parse_success_rate=Decimal("0.900"),
        stale_age_minutes=10,
        schema_drift_incidents=0,
        status=status,
    )


class _FakeScalars:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeSession:
    def __init__(self, *, sources, runs, snapshots) -> None:
        self._sources = sources
        self._runs = runs
        self._snapshots = snapshots

    def execute(self, query):
        text = str(query)
        if "source_health_snapshots" in text:
            return _FakeResult(self._snapshots)
        if "ingestion_runs" in text:
            return _FakeResult(self._runs)
        return _FakeResult(self._sources)


def _client(*, sources, runs, snapshots) -> TestClient:
    app = FastAPI()
    app.include_router(source_health_router)
    session = _FakeSession(sources=sources, runs=runs, snapshots=snapshots)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        org_id=ORG_ID, user_email=None, user_role="member"
    )
    return TestClient(app)


def _row_by_name(payload: dict, name: str) -> dict:
    return next(row for row in payload["sources"] if row["name"] == name)


def test_unknown_when_no_runs_or_snapshots() -> None:
    source = _source("Test Elevator Co.")
    client = _client(sources=[source], runs=[], snapshots=[])
    payload = client.get("/api/source-health").json()
    row = _row_by_name(payload, "Test Elevator Co.")
    assert row["status"] == "unknown"
    assert "No ingestion data" in row["note"]
    assert row["last_fetch_at"] is None
    assert row["parse_success_rate"] is None
    assert row["last_error"] is None


def test_live_when_recent_completed_run() -> None:
    source = _source("AgriCharts FMN")
    run = _run("AgriCharts FMN", status="completed", minutes_ago=10)
    client = _client(sources=[source], runs=[run], snapshots=[])
    row = _row_by_name(client.get("/api/source-health").json(), "AgriCharts FMN")
    assert row["status"] == "live"
    assert row["parse_success_rate"] == 0.95
    assert row["last_fetch_at"] == run.completed_at.isoformat()


def test_stale_when_last_success_is_old() -> None:
    source = _source("DG Global")
    run = _run("DG Global", status="completed", minutes_ago=60 * 49)
    client = _client(sources=[source], runs=[run], snapshots=[])
    row = _row_by_name(client.get("/api/source-health").json(), "DG Global")
    assert row["status"] == "stale"


def test_broken_when_latest_run_failed_and_error_reported() -> None:
    source = _source(
        "Bunge Hamilton", consecutive_failures=2, latest_error_message="404 Not Found"
    )
    run = _run(
        "Bunge Hamilton",
        status="failed",
        minutes_ago=30,
        error_message="404 Not Found",
        parse_success_rate=None,
    )
    client = _client(sources=[source], runs=[run], snapshots=[])
    row = _row_by_name(client.get("/api/source-health").json(), "Bunge Hamilton")
    assert row["status"] == "broken"
    assert row["last_error"] == "404 Not Found"
    assert row["consecutive_failures"] == 2


def test_running_run_with_snapshot_falls_back_to_snapshot() -> None:
    source = _source("Great Lakes Grain")
    run = _run("Great Lakes Grain", status="running", minutes_ago=5)
    snapshot = _snapshot(source, status="live", minutes_ago=20)
    client = _client(sources=[source], runs=[run], snapshots=[snapshot])
    row = _row_by_name(client.get("/api/source-health").json(), "Great Lakes Grain")
    assert row["status"] == "live"


def test_running_run_without_snapshot_is_unknown() -> None:
    source = _source("Collwest Grain")
    run = _run("Collwest Grain", status="running", minutes_ago=5)
    client = _client(sources=[source], runs=[run], snapshots=[])
    row = _row_by_name(client.get("/api/source-health").json(), "Collwest Grain")
    assert row["status"] == "unknown"
    assert "in progress" in row["note"]


def test_unregistered_run_source_still_gets_a_row() -> None:
    run = _run("Orphan Feed", status="completed", minutes_ago=10)
    client = _client(sources=[], runs=[run], snapshots=[])
    payload = client.get("/api/source-health").json()
    assert payload["count"] == 1
    row = payload["sources"][0]
    assert row["name"] == "Orphan Feed"
    assert row["source_id"] is None
    assert row["status"] == "live"
    assert "not registered" in row["note"]


def test_summary_counts_by_status() -> None:
    live = _source("AgriCharts FMN")
    stale = _source("DG Global")
    broken = _source("Bunge Hamilton")
    unknown = _source("Test Elevator Co.")
    runs = [
        _run("AgriCharts FMN", status="completed", minutes_ago=10),
        _run("DG Global", status="completed", minutes_ago=60 * 49),
        _run("Bunge Hamilton", status="failed", minutes_ago=30),
    ]
    client = _client(sources=[live, stale, broken, unknown], runs=runs, snapshots=[])
    counts = client.get("/api/source-health/summary").json()["counts"]
    assert counts == {"live": 1, "stale": 1, "broken": 1, "unknown": 1, "total": 4}


def test_empty_database_reports_zero_sources() -> None:
    client = _client(sources=[], runs=[], snapshots=[])
    payload = client.get("/api/source-health").json()
    assert payload["sources"] == []
    assert payload["count"] == 0
    counts = client.get("/api/source-health/summary").json()["counts"]
    assert counts["total"] == 0


def test_classify_prefers_latest_run_over_snapshot() -> None:
    source = _source("AgriCharts FMN")
    run = _run("AgriCharts FMN", status="failed", minutes_ago=5)
    snapshot = _snapshot(source, status="live", minutes_ago=60)
    status, _note = classify_source_status(
        source=source, latest_run=run, latest_snapshot=snapshot, now=_now()
    )
    assert status == "broken"
