"""Tests for price history + seasonal averages.

Route tests run the price_history router standalone with the DB
dependency overridden by a fake session (same pattern as
test_advisor.py). No real database, no external calls, no invented
prices: every expected number comes from rows built in the test.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.price_history import _seasonal_points, router as price_history_router  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402

COMPANY_ID = uuid.uuid4()
LOCATION_ID = uuid.uuid4()
OTHER_LOCATION_ID = uuid.uuid4()


class _FakeResult:
    def __init__(self, *, rows=None) -> None:
        self._rows = list(rows or [])

    def all(self):
        return list(self._rows)

    def scalars(self):
        raise AssertionError("scalars() should not be called by price history routes")


class _FakeSession:
    """Dispatches on the queried table: price rows, companies, locations."""

    def __init__(self, *, price_rows=None, companies=None, locations=None) -> None:
        self._price_rows = list(price_rows or [])
        self._companies = list(companies or [])
        self._locations = list(locations or [])

    def execute(self, query):
        text = str(query)
        if "FROM companies" in text:
            return _FakeResult(rows=self._companies)
        if "FROM locations" in text:
            return _FakeResult(rows=self._locations)
        return _FakeResult(rows=self._price_rows)


def _make_snapshot(captured_at, **overrides):
    values = {
        "id": uuid.uuid4(),
        "source_id": uuid.uuid4(),
        "commodity_id": uuid.uuid4(),
        "captured_at": captured_at,
    }
    values.update(overrides)
    return PriceSnapshot(**values)


def _make_price(captured_at, **overrides):
    values = {
        "snapshot_id": uuid.uuid4(),
        "location": "Testville",
        "commodity_name": "Corn",
        "cash_price_bu": Decimal("5.00"),
        "cash_price_mt": Decimal("196.85"),
        "basis": Decimal("0.50"),
        "futures_month": "July 2026",
        "delivery_label": "July 2026",
        "composite_key": "testville|corn|july 2026|",
        "location_id": LOCATION_ID,
        "company_id": COMPANY_ID,
    }
    values.update(overrides)
    return NormalizedPrice(**values)


def _make_client(db):
    test_app = FastAPI()
    test_app.include_router(price_history_router)

    def override_db():
        yield db

    test_app.dependency_overrides[get_db] = override_db
    return TestClient(test_app)


def _now():
    return datetime.now(timezone.utc)


def _pair(days_ago, **price_overrides):
    captured = _now() - timedelta(days=days_ago)
    price = _make_price(captured, **price_overrides)
    snapshot = _make_snapshot(captured)
    return (price, snapshot)


def test_history_returns_points_sorted_by_date_with_price_fields() -> None:
    rows = [_pair(10, cash_price_bu=Decimal("5.10")), _pair(2, cash_price_bu=Decimal("5.30"))]
    client = _make_client(_FakeSession(price_rows=rows))
    response = client.get("/api/prices/history", params={"commodity": "corn"})
    assert response.status_code == 200
    body = response.json()
    assert body["point_count"] == 2
    assert [p["cash_price_bu"] for p in body["points"]] == [5.10, 5.30]
    point = body["points"][0]
    assert point["unit"] == "bu"
    assert point["currency"] is None
    assert point["futures_month"] == "July 2026"
    assert point["cash_price_mt"] == 196.85
    assert point["basis"] == 0.5
    assert point["commodity_name"] == "Corn"
    assert "currency is not stored" in body["note"].lower() or "no currency" in body["note"].lower()


def test_history_returns_empty_list_when_no_rows() -> None:
    client = _make_client(_FakeSession(price_rows=[]))
    response = client.get("/api/prices/history", params={"commodity": "corn"})
    assert response.status_code == 200
    body = response.json()
    assert body["point_count"] == 0
    assert body["points"] == []
    assert body["days"] == 90


def test_history_filters_by_location_id_and_days_window() -> None:
    rows = [
        _pair(5, location_id=LOCATION_ID, cash_price_bu=Decimal("5.00")),
        _pair(5, location_id=OTHER_LOCATION_ID, cash_price_bu=Decimal("5.50")),
        _pair(120, location_id=LOCATION_ID, cash_price_bu=Decimal("4.00")),
    ]
    client = _make_client(_FakeSession(price_rows=rows))
    response = client.get(
        "/api/prices/history",
        params={"commodity": "corn", "location_id": str(LOCATION_ID), "days": 90},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["point_count"] == 1
    assert body["points"][0]["cash_price_bu"] == 5.00
    assert body["points"][0]["location_id"] == str(LOCATION_ID)


def test_history_ignores_other_commodities_and_requires_commodity() -> None:
    rows = [_pair(3, commodity_name="Soybeans", cash_price_bu=Decimal("12.00"))]
    client = _make_client(_FakeSession(price_rows=rows))
    response = client.get("/api/prices/history", params={"commodity": "corn"})
    assert response.status_code == 200
    assert response.json()["points"] == []
    assert client.get("/api/prices/history", params={"commodity": "  "}).status_code == 400


def test_history_resolves_company_name_from_company_table() -> None:
    rows = [_pair(1)]
    session = _FakeSession(price_rows=rows, companies=[(COMPANY_ID, "Great Lakes Grain")])
    client = _make_client(session)
    response = client.get("/api/prices/history", params={"commodity": "corn"})
    assert response.status_code == 200
    assert response.json()["points"][0]["company_name"] == "Great Lakes Grain"


def test_seasonal_averages_same_week_across_years_without_inventing() -> None:
    # ISO week 10 in 2024/2025/2026: Mondays 2024-03-04, 2025-03-03, 2026-03-02.
    rows = []
    for captured, cash in [
        (datetime(2024, 3, 4, 12, tzinfo=timezone.utc), Decimal("5.00")),
        (datetime(2025, 3, 3, 12, tzinfo=timezone.utc), Decimal("6.00")),
        (datetime(2026, 3, 2, 12, tzinfo=timezone.utc), Decimal("7.00")),
    ]:
        rows.append((_make_price(captured, cash_price_bu=cash), _make_snapshot(captured)))
    client = _make_client(_FakeSession(price_rows=rows))
    response = client.get("/api/prices/seasonal", params={"commodity": "corn"})
    assert response.status_code == 200
    body = response.json()
    assert body["years_covered"] == 3
    assert body["years"] == [2024, 2025, 2026]
    assert body["point_count"] == 1
    point = body["points"][0]
    assert point["week"] == 10
    assert point["average_cash_price_bu"] == 6.00
    assert point["years"] == [2024, 2025, 2026]
    assert point["observations"] == 3
    assert "not invented" in body["note"].lower()
    assert "3 year" in body["note"]


def test_seasonal_returns_empty_points_when_no_rows() -> None:
    client = _make_client(_FakeSession(price_rows=[]))
    response = client.get("/api/prices/seasonal", params={"commodity": "corn"})
    assert response.status_code == 200
    body = response.json()
    assert body["years_covered"] == 0
    assert body["years"] == []
    assert body["points"] == []
    assert "not invented" in body["note"].lower()


def test_history_empty_state_names_source_and_date() -> None:
    # Cycle 17: an honest empty state names its source and the date
    # it was computed, so "no data" is dated, not a bare empty list.
    client = _make_client(_FakeSession(price_rows=[]))
    response = client.get("/api/prices/history", params={"commodity": "corn"})
    assert response.status_code == 200
    body = response.json()
    assert body["point_count"] == 0
    assert body["points"] == []
    assert "Normalized prices" in body["source"]
    assert body["as_of"] == _now().date().isoformat()
    # The same fields are present when rows do exist.
    rows = [_pair(2, cash_price_bu=Decimal("5.30"))]
    client = _make_client(_FakeSession(price_rows=rows))
    body = client.get("/api/prices/history", params={"commodity": "corn"}).json()
    assert body["point_count"] == 1
    assert "Normalized prices" in body["source"]
    assert body["as_of"] == _now().date().isoformat()


def test_seasonal_empty_state_names_source_and_date() -> None:
    # Cycle 17: seasonal averages come only from real normalized
    # prices; with none present the empty state is dated and sourced.
    client = _make_client(_FakeSession(price_rows=[]))
    response = client.get("/api/prices/seasonal", params={"commodity": "corn"})
    assert response.status_code == 200
    body = response.json()
    assert body["years_covered"] == 0
    assert body["points"] == []
    assert "Normalized prices" in body["source"]
    assert body["as_of"] == _now().date().isoformat()
    # And a seeded multi-year response carries the same fields.
    rows = []
    for captured, cash in [
        (datetime(2025, 3, 3, 12, tzinfo=timezone.utc), Decimal("6.00")),
        (datetime(2026, 3, 2, 12, tzinfo=timezone.utc), Decimal("7.00")),
    ]:
        rows.append((_make_price(captured, cash_price_bu=cash), _make_snapshot(captured)))
    client = _make_client(_FakeSession(price_rows=rows))
    body = client.get("/api/prices/seasonal", params={"commodity": "corn"}).json()
    assert body["point_count"] == 1
    assert body["points"][0]["average_cash_price_bu"] == 6.50
    assert body["points"][0]["years"] == [2025, 2026]
    assert "Normalized prices" in body["source"]
    assert body["as_of"] == _now().date().isoformat()


def test_seasonal_uses_only_the_five_most_recent_years() -> None:
    rows = []
    for year in (2020, 2021, 2022, 2023, 2024, 2025):
        captured = datetime(year, 3, 4, 12, tzinfo=timezone.utc)
        # 2021-03-04 is ISO week 9, not 10; value still counts per its own week.
        rows.append((_make_price(captured, cash_price_bu=Decimal("5.00")), _make_snapshot(captured)))
    points, years_used, _counts = _seasonal_points(rows)
    assert years_used == [2021, 2022, 2023, 2024, 2025]
    assert all(2020 not in point["years"] for point in points)
