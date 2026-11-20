"""Licensed-feed plug-in tests (Cycle 40).

Proves a licensed feed (Barchart/DTN — parked 2026-11-19 at Adam's
request, not a blocker) can be added by config + one adapter, with
no changes to market search, advisor signals, or the research
dashboards:

- a synthetic adapter registered in ``ADAPTERS`` resolves through
  ``fetch_with_adapter`` (same shape as the ``andersons`` entry:
  mode ``"direct"``, source_class ``"api"``);
- seeding honours the ``[sources]`` toggles, so the synthetic key
  is seedable with no toggle entry (missing toggle = enabled),
  while the parked ``andersons`` adapter is skipped and never
  comes back as due;
- ``NormalizedPrice`` rows carrying a licensed-feed ``source_name``
  (``barchart/getGrainBids``, ``dtn/content-services``) surface in
  market search and on the public best-bid page with no route
  changes — both consumers read ``NormalizedPrice`` generically
  (market search / newsletter / market report via
  ``_load_preview_payload(..., source_name=None, ...)``; best-bids
  via a direct ``NormalizedPrice`` select with no source-name
  allowlist).

No network, no vendor, no key: the "feed" is a monkeypatched
function returning a canned DataFrame, and the downstream rows are
synthetic (Testville / Test Elevator Co.). Fixture names are neutral
synthetic names only.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import uuid

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.best_bids import router as best_bids_router  # noqa: E402
from app.api.routes.market_search import router as market_search_router  # noqa: E402
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.services.source_orchestration import list_due_sources, seed_sources_from_registry  # noqa: E402
from app.services.source_registry import ADAPTERS, SourceAdapter, fetch_with_adapter, get_adapter  # noqa: E402
from app.services.source_toggles import disabled_adapter_keys, is_adapter_enabled  # noqa: E402

ORG_ID = uuid.uuid4()
TEST_FEED_KEY = "test_licensed_feed"
TEST_FEED_ADAPTER = SourceAdapter(
    TEST_FEED_KEY, "usda_mirror_source", "fetch_usda_mirror", "direct", "api", 15, 90
)

# The adapter above points at an existing module only as a resolution
# address: the fetch function itself is monkeypatched in the test, so
# no real collector is ever called. This mirrors the andersons entry
# (mode "direct", source_class "api") — the shape a licensed-feed
# adapter would use (design doc §8, step 5).


def _fake_licensed_feed_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Location": "Testville",
                "Commodity": "Corn",
                "Delivery": "December 2026",
                "Futures Month": "December 2026",
                "Futures Price": 5.25,
                "Basis": 0.25,
                "Cash Price": 5.50,
            },
            {
                "Location": "Testville",
                "Commodity": "Soybeans",
                "Delivery": "January 2027",
                "Futures Month": "January 2027",
                "Futures Price": 11.00,
                "Basis": -0.50,
                "Cash Price": 10.50,
            },
        ]
    )


def test_synthetic_feed_adapter_resolves_through_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Config + one adapter is enough: the registry resolves and calls it."""
    monkeypatch.setattr(
        "app.platform.market_data.sources.usda_mirror_source.fetch_usda_mirror",
        _fake_licensed_feed_frame,
    )
    monkeypatch.setitem(ADAPTERS, TEST_FEED_KEY, TEST_FEED_ADAPTER)
    assert get_adapter(TEST_FEED_KEY) == TEST_FEED_ADAPTER
    frame = fetch_with_adapter(TEST_FEED_ADAPTER)
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 2
    assert list(frame["Commodity"]) == ["Corn", "Soybeans"]
    assert float(frame.iloc[0]["Cash Price"]) == pytest.approx(5.50)


def _sources_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.tables["sources"].create(bind=engine)
    return Session(bind=engine)


def test_synthetic_feed_adapter_is_seedable_and_andersons_is_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seeding honours toggles: the new key seeds, the parked one does not."""
    assert is_adapter_enabled("andersons") is False
    monkeypatch.setitem(ADAPTERS, TEST_FEED_KEY, TEST_FEED_ADAPTER)
    disabled_today = disabled_adapter_keys(sorted(ADAPTERS))
    assert "andersons" in disabled_today
    assert TEST_FEED_KEY not in disabled_today
    session = _sources_session()
    try:
        result = seed_sources_from_registry(session, org_id=ORG_ID)
        assert result.created == len(ADAPTERS) - len(disabled_today)
        assert "andersons" in result.skipped_disabled
        assert TEST_FEED_KEY not in result.skipped_disabled
        keys = {row.adapter_key for row in session.query(Source).all()}
        assert TEST_FEED_KEY in keys
        assert "andersons" not in keys
    finally:
        session.close()


def test_parked_andersons_row_never_comes_back_as_due(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defence in depth: a pre-existing andersons row must not be polled."""
    monkeypatch.setitem(ADAPTERS, TEST_FEED_KEY, TEST_FEED_ADAPTER)
    session = _sources_session()
    try:
        seed_sources_from_registry(session, org_id=ORG_ID)
        row = Source(
            org_id=ORG_ID,
            name="andersons",
            adapter_key="andersons",
            source_type="automated",
            polling_interval_minutes=10,
            timeout_seconds=60,
            max_retries=2,
            is_active=True,
        )
        session.add(row)
        session.commit()
        due = list_due_sources(session, now=datetime.now(timezone.utc))
        due_keys = {item.adapter_key for item in due}
        assert "andersons" not in due_keys
        assert TEST_FEED_KEY in due_keys
    finally:
        session.close()


class _FakeResult:
    def __init__(self, *, rows=None) -> None:
        self._rows = list(rows or [])

    def all(self):
        return list(self._rows)


class _PreviewFakeSession:
    """Serves the market-search preview query from canned (price, snapshot) pairs.

    The SQL is never executed (it contains Postgres-only functions),
    so dispatch is on the query text: location/company maps and the
    key-count query return empty; anything else returns the pairs.
    """

    def __init__(self, *, pairs=None) -> None:
        self._pairs = list(pairs or [])

    def execute(self, query):
        text = str(query)
        if "FROM locations" in text or "FROM companies" in text:
            return _FakeResult(rows=[])
        if "count(" in text:
            return _FakeResult(rows=[])
        return _FakeResult(rows=self._pairs)


def _make_feed_price(*, source_name: str, cash: str, commodity: str = "Corn") -> NormalizedPrice:
    return NormalizedPrice(
        snapshot_id=uuid.uuid4(),
        location="Testville",
        commodity_name=commodity,
        cash_price_bu=Decimal(cash),
        cash_price_mt=Decimal("216.54"),
        basis=Decimal("0.25"),
        futures_month="December 2026",
        futures_price=Decimal("5.25"),
        delivery_label="December 2026",
        delivery_end="December 2026",
        source_name=source_name,
        composite_key=f"testville|{commodity.lower()}|december 2026|december 2026",
        is_canonical=True,
    )


def _make_snapshot() -> PriceSnapshot:
    return PriceSnapshot(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        commodity_id=uuid.uuid4(),
        captured_at=datetime(2026, 11, 19, 12, tzinfo=timezone.utc),
    )


def _make_market_search_client(db) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(market_search_router)

    def override_db():
        yield db

    def override_context():
        return RequestContext(org_id=ORG_ID, user_email=None, user_role="admin")

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_request_context] = override_context
    return TestClient(test_app)


def test_feed_rows_surface_in_market_search_with_no_route_change() -> None:
    """Market search reads NormalizedPrice generically: feed rows appear."""
    pairs = [
        (_make_feed_price(source_name="barchart/getGrainBids", cash="5.50"), _make_snapshot()),
        (_make_feed_price(source_name="dtn/content-services", cash="5.40"), _make_snapshot()),
    ]
    client = _make_market_search_client(_PreviewFakeSession(pairs=pairs))
    response = client.get("/api/market-search", params={"commodity": "Corn"})
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    rows = [row for group in body["groups"] for row in group["rows"]]
    assert len(rows) == 2
    assert {row["location"] for row in rows} == {"Testville"}
    assert {float(row["cash_price_bu"]) for row in rows} == {5.50, 5.40}
    sources = {str(row["source_name"]).lower() for row in rows}
    assert any("barchart" in source for source in sources)
    assert any("dtn" in source for source in sources)


class _BestBidsFakeSession:
    """Dispatches on the queried table: price rows, companies, locations."""

    def __init__(self, *, price_rows=None) -> None:
        self._price_rows = list(price_rows or [])

    def execute(self, query):
        text = str(query)
        if "FROM companies" in text or "FROM locations" in text:
            return _FakeResult(rows=[])
        return _FakeResult(rows=self._price_rows)


def _make_best_bids_client(db) -> TestClient:
    # Deliberately no request-context override and no auth headers:
    # this endpoint is public.
    test_app = FastAPI()
    test_app.include_router(best_bids_router)

    def override_db():
        yield db

    test_app.dependency_overrides[get_db] = override_db
    return TestClient(test_app)


def test_feed_rows_surface_on_public_best_bids_with_no_route_change() -> None:
    """The public best-bid page shows feed rows under their own source name."""
    captured = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)
    pairs = [
        (
            _make_feed_price(source_name="barchart/getGrainBids", cash="5.50"),
            PriceSnapshot(
                id=uuid.uuid4(),
                source_id=uuid.uuid4(),
                commodity_id=uuid.uuid4(),
                captured_at=captured,
            ),
        ),
        (
            _make_feed_price(source_name="dtn/content-services", cash="5.40"),
            PriceSnapshot(
                id=uuid.uuid4(),
                source_id=uuid.uuid4(),
                commodity_id=uuid.uuid4(),
                captured_at=captured,
            ),
        ),
    ]
    client = _make_best_bids_client(_BestBidsFakeSession(price_rows=pairs))
    response = client.get("/api/best-bids")  # no headers at all
    assert response.status_code == 200
    body = response.json()
    assert body["bid_count"] == 2
    bids = [bid for group in body["groups"] for bid in group["bids"]]
    assert {bid["source"] for bid in bids} == {
        "barchart/getGrainBids",
        "dtn/content-services",
    }
    assert {float(bid["cash_price_bu"]) for bid in bids} == {5.50, 5.40}
