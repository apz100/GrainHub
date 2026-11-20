"""Research cache + cached-route tests (Marathon Phase C, 2026-11-20).

The cache service is tested against real SQLite; the new routes are
tested with a standalone app (DB + request-context dependencies
overridden) and the USDA fetchers monkeypatched at the route module,
so no network and no API keys are involved. The fetcher payloads use
the live-verified FAS PSD world shape (overnight run, 2026-11-20:
corn 0440000 / 2026, production value 1291550).
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.api.routes.research as research_route  # noqa: E402
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.research_cache import ResearchCacheEntry  # noqa: E402
from app.services.research import ResearchKeyRequired, ResearchUpstreamError  # noqa: E402
from app.services.research_cache import get_or_fetch  # noqa: E402

ORG_ID = uuid.uuid4()


def _session() -> Session:
    # StaticPool + shared thread access: TestClient serves requests
    # from another thread, and an in-memory SQLite database lives
    # per-connection — without this the route sees an empty database.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.tables["research_cache_entries"].create(bind=engine)
    return Session(bind=engine)


# --- cache service -------------------------------------------------


def test_first_call_fetches_and_stores() -> None:
    session = _session()
    calls = {"n": 0}

    def fetcher():
        calls["n"] += 1
        return {"rows": [1, 2, 3]}

    try:
        result = get_or_fetch(
            session, dataset="fas_psd_world", cache_key="0440000/2026",
            source="USDA FAS PSD", fetcher=fetcher,
        )
        assert result.cache_state == "fetched"
        assert result.payload == {"rows": [1, 2, 3]}
        assert calls["n"] == 1
        stored = session.query(ResearchCacheEntry).count()
        assert stored == 1
    finally:
        session.close()


def test_second_call_hits_cache_without_fetching() -> None:
    session = _session()
    calls = {"n": 0}

    def fetcher():
        calls["n"] += 1
        return {"rows": [calls["n"]]}

    try:
        get_or_fetch(session, dataset="nass_series", cache_key="CORN/2026",
                     source="USDA NASS Quick Stats", fetcher=fetcher)
        result = get_or_fetch(session, dataset="nass_series", cache_key="CORN/2026",
                              source="USDA NASS Quick Stats", fetcher=fetcher)
        assert result.cache_state == "hit"
        assert result.payload == {"rows": [1]}
        assert calls["n"] == 1
    finally:
        session.close()


def test_stale_entry_refetches_and_fetch_failure_falls_back_to_stale() -> None:
    session = _session()
    try:
        entry = ResearchCacheEntry(
            dataset="fas_psd_world", cache_key="0440000/2026",
            payload={"rows": ["old"]}, source="USDA FAS PSD",
            fetched_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        session.add(entry)
        session.commit()

        refreshed = get_or_fetch(
            session, dataset="fas_psd_world", cache_key="0440000/2026",
            source="USDA FAS PSD", fetcher=lambda: {"rows": ["new"]},
        )
        assert refreshed.cache_state == "fetched"
        assert refreshed.payload == {"rows": ["new"]}

        # Age it again; a failing fetcher must serve the stale row,
        # labelled stale — never an exception, never fresh-looking.
        entry.fetched_at = datetime.now(timezone.utc) - timedelta(hours=48)
        session.commit()

        def boom():
            raise ResearchUpstreamError("upstream down")

        fallback = get_or_fetch(
            session, dataset="fas_psd_world", cache_key="0440000/2026",
            source="USDA FAS PSD", fetcher=boom,
        )
        assert fallback.cache_state == "stale"
        assert fallback.payload == {"rows": ["new"]}
    finally:
        session.close()


def test_fetch_failure_without_cache_propagates() -> None:
    session = _session()
    try:
        def boom():
            raise ResearchKeyRequired("no key")

        with pytest.raises(ResearchKeyRequired):
            get_or_fetch(session, dataset="fas_psd_world", cache_key="x/2026",
                         source="USDA FAS PSD", fetcher=boom)
        assert session.query(ResearchCacheEntry).count() == 0
    finally:
        session.close()


# --- routes --------------------------------------------------------


def _client(session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(research_route.router)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        org_id=ORG_ID, user_email="test@example.com", user_role="admin"
    )
    return TestClient(app)


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


def test_world_route_decodes_and_caches(monkeypatch) -> None:
    session = _session()
    calls = {"world": 0}
    monkeypatch.setattr(
        research_route, "fetch_fas_psd_world",
        lambda **kw: (calls.__setitem__("world", calls["world"] + 1), WORLD_ROWS)[1],
    )
    monkeypatch.setattr(
        research_route, "fetch_fas_psd_attribute_names",
        lambda **kw: {28: "Production", 176: "Ending Stocks"},
    )
    monkeypatch.setattr(
        research_route, "fetch_fas_psd_unit_names",
        lambda **kw: {8: "1000 MT"},
    )
    client = _client(session)
    try:
        first = client.get("/api/research/fas-psd/world?commodity_code=0440000&year=2026")
        assert first.status_code == 200
        body = first.json()
        assert body["cache"]["state"] == "fetched"
        metrics = {row["metric"]: row["value"] for row in body["rows"]}
        assert metrics == {"Production": 1291550.0, "Ending Stocks": 281938.0}
        assert body["rows"][0]["unit"] == "1000 MT"

        second = client.get("/api/research/fas-psd/world?commodity_code=0440000&year=2026")
        assert second.json()["cache"]["state"] == "hit"
        assert calls["world"] == 1  # upstream called once across both requests
    finally:
        session.close()


def test_world_route_key_required_is_503(monkeypatch) -> None:
    session = _session()

    def no_key(**kw):
        raise ResearchKeyRequired("FAS PSD needs a free data.gov API key")

    monkeypatch.setattr(research_route, "fetch_fas_psd_world", no_key)
    client = _client(session)
    try:
        response = client.get("/api/research/fas-psd/world?commodity_code=0440000&year=2026")
        assert response.status_code == 503
    finally:
        session.close()


def test_nass_series_route_caches_and_truncates(monkeypatch) -> None:
    session = _session()
    raw = [
        {"commodity_desc": "CORN", "year": 2026, "short_desc": f"record {i}", "Value": "1"}
        for i in range(10)
    ]
    monkeypatch.setattr(research_route, "fetch_nass_quick_stats", lambda **kw: raw)
    monkeypatch.setattr(
        research_route, "parse_nass_records",
        lambda records: [{"n": i} for i in range(len(records))],
    )
    client = _client(session)
    try:
        body = client.get("/api/research/nass/series?commodity=CORN&year=2026&limit=3").json()
        assert body["total_records"] == 10
        assert body["truncated"] is True
        assert len(body["records"]) == 3
        again = client.get("/api/research/nass/series?commodity=CORN&year=2026&limit=3").json()
        assert again["cache"]["state"] == "hit"
    finally:
        session.close()
