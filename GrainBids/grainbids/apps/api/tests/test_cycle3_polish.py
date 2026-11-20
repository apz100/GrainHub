"""Cycle 3 polish tests.

1. Basis tracker consumes source-health data: every ranked / unranked /
   history row carries ``source_status`` (healthy / stale / broken /
   unknown) derived from the same real ingestion data as the
   source-health dashboard. "healthy" is the dashboard's "live".
2. Report calendar is wired to research ingestion status: every event
   carries ``ingestion_status`` from real ``ResearchReport`` rows, and
   the response carries a top-level ``ingestion_status`` summary per
   report. Absent rows are "not ingested yet"; no database at all is
   "unknown".

Route tests run the routers standalone with fake sessions (same
TestClient / dependency-override pattern as the Cycle 2 tests), so
nothing here needs a real database.
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

from app.api.routes.basis import router as basis_router  # noqa: E402
from app.api.routes.report_calendar import (  # noqa: E402
    _optional_session,
    build_ingestion_status,
    ingestion_status_for_report,
    router as calendar_router,
)
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.ingestion_run import IngestionRun  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.research_report import ResearchReport  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.models.source_health_snapshot import SourceHealthSnapshot  # noqa: E402

ORG_ID = uuid.uuid4()
TESTVILLE_ID = uuid.uuid4()
RUSSELL_ID = uuid.uuid4()


def _now() -> datetime:
    # Anchor fixtures to the real clock: source-health classification
    # compares run times against datetime.now(timezone.utc).
    return datetime.now(timezone.utc)


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Basis fixtures
# ---------------------------------------------------------------------------


def _make_price(**overrides):
    values = {
        "snapshot_id": uuid.uuid4(),
        "location": "Testville",
        "location_id": TESTVILLE_ID,
        "commodity_name": "Corn",
        "source_name": "Test Elevator Co.",
        "delivery_label": "December 2026",
        "futures_month": "Dec 2026",
        "futures_price": Decimal("4.79"),
        "basis": Decimal("1.40"),
        "cash_price_bu": Decimal("6.19"),
        "cash_price_mt": Decimal("243.79"),
        "composite_key": "testville|corn|dec 2026|dec 2026",
        "is_canonical": True,
    }
    values.update(overrides)
    return NormalizedPrice(**values)


def _make_snapshot(captured_at: datetime) -> PriceSnapshot:
    return PriceSnapshot(
        source_id=uuid.uuid4(),
        commodity_id=uuid.uuid4(),
        captured_at=captured_at,
    )


def _make_location(**overrides):
    values = {
        "id": TESTVILLE_ID,
        "org_id": ORG_ID,
        "name": "Testville",
        "canonical_key": "testville",
        "latitude": 45.05,
        "longitude": -75.55,
    }
    values.update(overrides)
    return Location(**values)


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

    def all(self):
        return list(self._rows)

    def scalars(self):
        return _FakeScalars(self._rows)


class _BasisFakeSession:
    """Dispatches on the queried table.

    The price-pairs query joins the sources table, so it must be
    matched on "normalized_prices" before the plain "sources" check.
    """

    def __init__(self, *, price_pairs=None, locations=None, sources=None, runs=None, snapshots=None) -> None:
        self._price_pairs = price_pairs or []
        self._locations = locations or []
        self._sources = sources or []
        self._runs = runs or []
        self._snapshots = snapshots or []

    def execute(self, query):
        text = str(query)
        if "locations" in text:
            return _FakeResult(self._locations)
        if "source_health_snapshots" in text:
            return _FakeResult(self._snapshots)
        if "ingestion_runs" in text:
            return _FakeResult(self._runs)
        if "normalized_prices" in text:
            return _FakeResult(self._price_pairs)
        return _FakeResult(self._sources)


def _basis_client(session: _BasisFakeSession) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(basis_router)

    def override_db():
        yield session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_request_context] = lambda: RequestContext(
        org_id=ORG_ID, user_email=None, user_role="admin"
    )
    return TestClient(test_app)


def _tracker_pairs():
    return [
        (_make_price(), _make_snapshot(_dt(2026, 11, 17))),
        (
            _make_price(
                location="Russell",
                location_id=RUSSELL_ID,
                source_name="DG Global",
                cash_price_bu=Decimal("6.60"),
                composite_key="russell|corn|dec 2026|dec 2026",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
        (
            _make_price(
                location="NoCoord Town",
                location_id=uuid.uuid4(),
                source_name="Bunge Hamilton",
                futures_price=None,
                composite_key="nocoord town|corn|dec 2026|dec 2026",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
    ]


def _tracker_locations():
    return [
        _make_location(),
        _make_location(
            id=RUSSELL_ID, name="Russell", canonical_key="russell",
            latitude=45.26, longitude=-75.36,
        ),
    ]


def test_tracker_row_source_status_healthy_when_recent_run() -> None:
    live_source = _source("Test Elevator Co.")
    stale_source = _source("DG Global")
    broken_source = _source("Bunge Hamilton")
    run_live = _run("Test Elevator Co.", status="completed", minutes_ago=10)
    run_stale = _run("DG Global", status="completed", minutes_ago=60 * 49)
    run_broken = _run("Bunge Hamilton", status="failed", minutes_ago=30)
    session = _BasisFakeSession(
        price_pairs=_tracker_pairs(),
        locations=_tracker_locations(),
        sources=[live_source, stale_source, broken_source],
        runs=[run_live, run_stale, run_broken],
        snapshots=[],
    )
    client = _basis_client(session)
    try:
        response = client.get("/api/basis/tracker", params={"commodity": "corn"})
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    by_location = {row["location"]: row for row in body["ranked"] + body["unranked"]}
    # "healthy" is the source-health dashboard's "live".
    assert by_location["Testville"]["source_status"]["status"] == "healthy"
    assert by_location["Russell"]["source_status"]["status"] == "stale"
    assert by_location["NoCoord Town"]["source_status"]["status"] == "broken"
    # Unranked rows (missing futures price) still carry a source status.
    assert by_location["NoCoord Town"]["missing_reason"] == "missing_futures_price"
    assert body["source_statuses"] == {
        "Test Elevator Co.": "healthy",
        "DG Global": "stale",
        "Bunge Hamilton": "broken",
    }
    assert "live" in body["source_status_note"]
    assert "healthy" in body["source_status_note"]


def test_tracker_row_source_status_unknown_when_no_ingestion_data() -> None:
    session = _BasisFakeSession(
        price_pairs=_tracker_pairs(),
        locations=_tracker_locations(),
        sources=[
            _source("Test Elevator Co."),
            _source("DG Global"),
            _source("Bunge Hamilton"),
        ],
        runs=[],
        snapshots=[],
    )
    client = _basis_client(session)
    try:
        response = client.get("/api/basis/tracker", params={"commodity": "corn"})
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    for row in body["ranked"] + body["unranked"]:
        assert row["source_status"]["status"] == "unknown"
        assert "No ingestion data" in row["source_status"]["note"]
    assert set(body["source_statuses"].values()) == {"unknown"}


def test_tracker_row_source_status_unknown_for_unregistered_source() -> None:
    # The price row's source has no Source row and no ingestion run at
    # all: it must be unknown, never assumed healthy.
    session = _BasisFakeSession(
        price_pairs=[(_make_price(), _make_snapshot(_dt(2026, 11, 17)))],
        locations=_tracker_locations(),
        sources=[],
        runs=[],
        snapshots=[],
    )
    client = _basis_client(session)
    try:
        response = client.get("/api/basis/tracker", params={"commodity": "corn"})
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["ranked"][0]["source_status"]["status"] == "unknown"
    assert body["source_statuses"] == {"Test Elevator Co.": "unknown"}


def test_tracker_row_source_status_uses_snapshot_when_run_running() -> None:
    source = _source("Great Lakes Grain")
    run = _run("Great Lakes Grain", status="running", minutes_ago=5)
    snapshot = _snapshot(source, status="live", minutes_ago=20)
    session = _BasisFakeSession(
        price_pairs=[
            (
                _make_price(source_name="Great Lakes Grain"),
                _make_snapshot(_dt(2026, 11, 17)),
            )
        ],
        locations=_tracker_locations(),
        sources=[source],
        runs=[run],
        snapshots=[snapshot],
    )
    client = _basis_client(session)
    try:
        response = client.get("/api/basis/tracker", params={"commodity": "corn"})
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["ranked"][0]["source_status"]["status"] == "healthy"


def test_history_rows_carry_source_status() -> None:
    source = _source("Test Elevator Co.")
    run = _run("Test Elevator Co.", status="completed", minutes_ago=10)
    pairs = [
        (_make_price(cash_price_bu=Decimal("6.30")), _make_snapshot(_dt(2026, 11, 17))),
        (_make_price(cash_price_bu=Decimal("6.10")), _make_snapshot(_dt(2026, 11, 15))),
    ]
    session = _BasisFakeSession(
        price_pairs=pairs,
        locations=[],
        sources=[source],
        runs=[run],
        snapshots=[],
    )
    client = _basis_client(session)
    try:
        response = client.get(
            "/api/basis/history",
            params={"commodity": "corn", "location_id": str(TESTVILLE_ID)},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert [row["source_status"]["status"] for row in body["rows"]] == [
        "healthy",
        "healthy",
    ]
    assert "live" in body["source_status_note"]


# ---------------------------------------------------------------------------
# Report calendar fixtures
# ---------------------------------------------------------------------------


def _research_report(*, report_type: str, report_date: str, created_at: datetime, commodity: str = "Corn") -> ResearchReport:
    return ResearchReport(
        id=uuid.uuid4(),
        org_id=ORG_ID,
        report_type=report_type,
        commodity=commodity,
        report_date=report_date,
        vintage=report_date,
        source=f"USDA {report_type.replace('_', ' ').title()}",
        source_url=None,
        delay_label="Public release file; no delay beyond the release itself.",
        payload={"values": []},
        created_at=created_at,
    )


class _CalendarFakeSession:
    def __init__(self, *, reports=None) -> None:
        self._reports = reports or []

    def execute(self, query):
        assert "research_reports" in str(query)
        return _FakeResult(self._reports)


def _calendar_client(session: _CalendarFakeSession | None) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(calendar_router)
    if session is not None:
        test_app.dependency_overrides[_optional_session] = lambda: session
    return TestClient(test_app)


def _by_report(events: list[dict], report: str) -> list[dict]:
    return [event for event in events if event["report"] == report]


def test_build_ingestion_status_latest_row_wins() -> None:
    older = _research_report(
        report_type="wasde", report_date="2026-10-09", created_at=_dt(2026, 10, 9)
    )
    newer = _research_report(
        report_type="wasde", report_date="2026-11-10", created_at=_dt(2026, 11, 10)
    )
    statuses = build_ingestion_status([older, newer])
    assert statuses["wasde"]["status"] == "ingested"
    assert statuses["wasde"]["latest_report_date"] == "2026-11-10"
    assert statuses["wasde"]["ingested_at"] == _dt(2026, 11, 10).isoformat()
    assert statuses["wasde"]["source"] == "USDA Wasde"
    # A type with no rows at all is "not ingested yet", never invented.
    assert statuses["crop_progress"]["status"] == "not_ingested_yet"
    assert statuses["crop_progress"]["latest_report_date"] is None


def test_ingestion_status_for_report_without_collector() -> None:
    statuses = build_ingestion_status([])
    entry = ingestion_status_for_report("Prospective Plantings", statuses)
    assert entry["status"] == "not_ingested_yet"
    assert "No ingestion collector" in entry["note"]
    entry = ingestion_status_for_report("WASDE", statuses)
    assert entry["status"] == "not_ingested_yet"
    assert "No ingestion collector" not in entry["note"]


def test_calendar_events_carry_ingestion_status_from_real_rows() -> None:
    wasde = _research_report(
        report_type="wasde", report_date="2026-11-10", created_at=_dt(2026, 11, 10)
    )
    client = _calendar_client(_CalendarFakeSession(reports=[wasde]))
    try:
        payload = client.get("/api/research/calendar").json()
    finally:
        client.app.dependency_overrides.clear()
    wasde_events = _by_report(payload["events"], "WASDE")
    assert wasde_events
    assert all(
        event["ingestion_status"]["status"] == "ingested" for event in wasde_events
    )
    assert wasde_events[0]["ingestion_status"]["latest_report_date"] == "2026-11-10"
    assert wasde_events[0]["ingestion_status"]["source"] == "USDA Wasde"
    # Crop Progress has no ingested row: "not ingested yet".
    progress_events = _by_report(payload["events"], "Crop Progress")
    assert progress_events
    assert all(
        event["ingestion_status"]["status"] == "not_ingested_yet"
        for event in progress_events
    )
    # Top-level summary is keyed per report.
    assert payload["ingestion_status"]["WASDE"]["status"] == "ingested"
    assert payload["ingestion_status"]["Crop Progress"]["status"] == "not_ingested_yet"
    assert payload["ingestion_status"]["Prospective Plantings"]["status"] == "not_ingested_yet"
    assert "No ingestion collector" in payload["ingestion_status"]["Prospective Plantings"]["note"]
    assert payload["ingestion_status_note"]
    # The next event carries its ingestion status too.
    assert "ingestion_status" in payload["next_event"]


def test_calendar_ingestion_status_unknown_when_no_database() -> None:
    # No dependency override: _optional_session yields None, so the
    # calendar stays available and every status is "unknown".
    client = _calendar_client(None)
    try:
        payload = client.get("/api/research/calendar").json()
    finally:
        client.app.dependency_overrides.clear()
    assert all(
        event["ingestion_status"]["status"] == "unknown"
        for event in payload["events"]
        if event["report"] not in {"Prospective Plantings", "Acreage", "Small Grains Summary"}
    )
    # Report types with no collector at all are "not ingested yet" even
    # with no database: that fact comes from the code, not from rows.
    assert all(
        event["ingestion_status"]["status"] == "not_ingested_yet"
        for event in payload["events"]
        if event["report"] in {"Prospective Plantings", "Acreage", "Small Grains Summary"}
    )
    assert payload["ingestion_status"]["WASDE"]["status"] == "unknown"
    assert "no database available" in payload["ingestion_status_note"].lower()


def test_calendar_ingestion_status_empty_database_is_not_ingested_yet() -> None:
    client = _calendar_client(_CalendarFakeSession(reports=[]))
    try:
        payload = client.get("/api/research/calendar").json()
    finally:
        client.app.dependency_overrides.clear()
    assert payload["ingestion_status"]["WASDE"]["status"] == "not_ingested_yet"
    assert payload["ingestion_status"]["Export Sales"]["status"] == "not_ingested_yet"
