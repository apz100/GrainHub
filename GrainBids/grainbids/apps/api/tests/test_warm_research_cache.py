"""Scheduled USDA research-cache warmup job (app/jobs/warm_research_cache).

The job must write exactly the cache rows the research routes read:
same datasets, same cache keys, same decoded payloads. The strongest
check here is the route-equivalence test — after a warmup with mocked
upstream fetchers, the real routes answer from cache ("hit") with the
upstream fetchers replaced by tripwires, so any miss would fail loudly
instead of reaching the network. No network and no API keys are used.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.api.routes.research as research_route  # noqa: E402
import app.jobs.warm_research_cache as warmup  # noqa: E402
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.research_cache import ResearchCacheEntry  # noqa: E402
from app.services.research import ResearchKeyRequired, ResearchUpstreamError  # noqa: E402

ORG_ID = uuid.uuid4()
YEAR = 2026

WORLD_ROWS = [
    {
        "attributeId": 28, "calendarYear": 2026, "commodityCode": "0440000",
        "countryCode": "00", "marketYear": "2026", "month": "11",
        "unitId": 8, "value": 1291550.0,
    },
    {
        "attributeId": 176, "calendarYear": 2026, "commodityCode": "0440000",
        "countryCode": "00", "marketYear": "2026", "month": "11",
        "unitId": 8, "value": 281938.0,
    },
]

EXPECTED_KEYS = {
    ("fas_psd_attributes", "all"),
    ("fas_psd_units", "all"),
    ("fas_psd_world", "0440000/2026"),
    ("fas_psd_world", "2222000/2026"),
    ("fas_psd_world", "0410000/2026"),
    ("fas_psd_commodities", "0440000"),
    ("fas_psd_commodities", "2222000"),
    ("fas_psd_commodities", "0410000"),
    ("nass_series", "CORN/2026"),
    ("nass_series", "SOYBEANS/2026"),
    ("nass_series", "WHEAT/2026"),
}


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.tables["research_cache_entries"].create(bind=engine)
    return Session(bind=engine)


def _nass_raw(commodity: str, count: int = 3) -> list[dict]:
    return [
        {
            "commodity_desc": commodity, "statisticcat_desc": "YIELD",
            "year": YEAR, "state_name": "IOWA", "county_name": "",
            "Value": "179.6", "unit_desc": "BU / ACRE",
        }
        for _ in range(count)
    ]


def _patch_fetchers(monkeypatch, *, calls: dict | None = None):
    """Mock upstream fetchers at the job module; optionally count calls."""
    def counted(name):
        def wrap(fn):
            def inner(*args, **kwargs):
                if calls is not None:
                    calls[name] = calls.get(name, 0) + 1
                return fn(*args, **kwargs)
            return inner
        return wrap

    monkeypatch.setattr(
        warmup, "fetch_fas_psd_world",
        counted("world")(lambda **kw: WORLD_ROWS),
    )
    monkeypatch.setattr(
        warmup, "fetch_fas_psd_attribute_names",
        counted("attributes")(lambda **kw: {28: "Production", 176: "Ending Stocks"}),
    )
    monkeypatch.setattr(
        warmup, "fetch_fas_psd_unit_names",
        counted("units")(lambda **kw: {8: "1000 MT"}),
    )
    monkeypatch.setattr(
        warmup, "fetch_fas_psd",
        counted("commodities")(lambda **kw: [{"commodityCode": kw.get("commodity_code")}]),
    )
    monkeypatch.setattr(
        warmup, "fetch_nass_quick_stats",
        counted("nass")(lambda **kw: _nass_raw(str(kw.get("commodity", "CORN")))),
    )


def _run(monkeypatch, session: Session, **kwargs) -> int:
    monkeypatch.setattr(warmup, "get_sessionmaker", lambda: lambda: session)
    return warmup.run_once(year=YEAR, **kwargs)


def _keys(session: Session) -> set[tuple[str, str]]:
    return {
        (row.dataset, row.cache_key)
        for row in session.query(ResearchCacheEntry).all()
    }


def test_warmup_writes_all_expected_rows(monkeypatch) -> None:
    session = _session()
    try:
        _patch_fetchers(monkeypatch)
        assert _run(monkeypatch, session) == 0
        assert _keys(session) == EXPECTED_KEYS
        assert session.query(ResearchCacheEntry).count() == 11

        world = session.query(ResearchCacheEntry).filter_by(
            dataset="fas_psd_world", cache_key="0440000/2026"
        ).one()
        metrics = {row["metric"]: row["value"] for row in world.payload["rows"]}
        assert metrics == {"Production": 1291550.0, "Ending Stocks": 281938.0}
        assert world.payload["rows"][0]["unit"] == "1000 MT"

        nass = session.query(ResearchCacheEntry).filter_by(
            dataset="nass_series", cache_key="CORN/2026"
        ).one()
        assert nass.payload["total_records"] == 3
        assert nass.payload["records"][0]["commodity"] == "CORN"
    finally:
        session.close()


def test_warmup_is_idempotent(monkeypatch) -> None:
    session = _session()
    calls: dict[str, int] = {}
    try:
        _patch_fetchers(monkeypatch, calls=calls)
        assert _run(monkeypatch, session) == 0
        first_calls = dict(calls)
        assert first_calls == {
            "world": 3, "attributes": 1, "units": 1, "commodities": 3, "nass": 3,
        }
        assert _run(monkeypatch, session) == 0
        assert calls == first_calls  # fresh rows are never re-fetched
        assert session.query(ResearchCacheEntry).count() == 11
    finally:
        session.close()


def test_warmed_rows_are_what_the_routes_read(monkeypatch) -> None:
    """After warmup, the real routes answer "hit" without upstream."""
    session = _session()
    try:
        _patch_fetchers(monkeypatch)
        assert _run(monkeypatch, session) == 0

        def tripwire(*args, **kwargs):
            raise AssertionError("route must not call upstream after warmup")

        monkeypatch.setattr(research_route, "fetch_fas_psd_world", tripwire)
        monkeypatch.setattr(research_route, "fetch_fas_psd_attribute_names", tripwire)
        monkeypatch.setattr(research_route, "fetch_fas_psd_unit_names", tripwire)
        monkeypatch.setattr(research_route, "fetch_nass_quick_stats", tripwire)

        app = FastAPI()
        app.include_router(research_route.router)
        app.dependency_overrides[get_db] = lambda: session
        app.dependency_overrides[get_request_context] = lambda: RequestContext(
            org_id=ORG_ID, user_email="test@example.com", user_role="admin"
        )
        client = TestClient(app)

        world = client.get("/api/research/fas-psd/world?commodity_code=0440000&year=2026")
        assert world.status_code == 200
        assert world.json()["cache"]["state"] == "hit"
        metrics = {row["metric"]: row["value"] for row in world.json()["rows"]}
        assert metrics == {"Production": 1291550.0, "Ending Stocks": 281938.0}

        series = client.get("/api/research/nass/series?commodity=CORN&year=2026&limit=5")
        assert series.status_code == 200
        assert series.json()["cache"]["state"] == "hit"
        assert series.json()["total_records"] == 3
    finally:
        session.close()


def test_partial_failure_still_warms_the_rest(monkeypatch) -> None:
    session = _session()
    try:
        _patch_fetchers(monkeypatch)
        monkeypatch.setattr(
            warmup, "fetch_fas_psd_world",
            lambda **kw: (_ for _ in ()).throw(ResearchUpstreamError("FAS down")),
        )
        assert _run(monkeypatch, session) == 0  # some datasets warmed: run succeeds
        keys = _keys(session)
        assert ("fas_psd_world", "0440000/2026") not in keys
        assert len(keys) == 8  # 2 name tables + 3 catalogues + 3 NASS series
    finally:
        session.close()


def test_total_failure_exits_1(monkeypatch) -> None:
    session = _session()
    try:
        def no_key(**kw):
            raise ResearchKeyRequired("no key configured")

        for name in (
            "fetch_fas_psd_world", "fetch_fas_psd_attribute_names",
            "fetch_fas_psd_unit_names", "fetch_fas_psd", "fetch_nass_quick_stats",
        ):
            monkeypatch.setattr(warmup, name, no_key)
        assert _run(monkeypatch, session) == 1
        assert session.query(ResearchCacheEntry).count() == 0
    finally:
        session.close()


def test_dry_run_fetches_but_writes_nothing(monkeypatch) -> None:
    session = _session()
    calls: dict[str, int] = {}
    try:
        _patch_fetchers(monkeypatch, calls=calls)
        assert warmup.run_once(year=YEAR, dry_run=True) == 0
        # No cache in dry-run mode, so each world fetch resolves the
        # name tables directly (1 target call + 3 world calls each).
        assert calls == {
            "world": 3, "attributes": 4, "units": 4, "commodities": 3, "nass": 3,
        }
        assert session.query(ResearchCacheEntry).count() == 0
    finally:
        session.close()
