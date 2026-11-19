"""Basis tracker tests (Cycle 2).

Service tests run the pure functions on fabricated NormalizedPrice rows;
route tests run the basis router standalone with a dispatching fake
session (same TestClient / dependency-override pattern as the advisor
tests), so nothing here needs a real database.

Coordinates used below are the same approximate test values already used
by test_market_search.py (Testville ~45.05, -75.55; Russell ~45.26,
-75.36, ~30 km apart). No production coordinates are asserted.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.basis import router as basis_router  # noqa: E402
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.services.basis_tracker import (  # noqa: E402
    build_basis_history,
    compute_basis_for_row,
    find_default_origin,
    rank_basis,
)

ORG_ID = uuid.uuid4()
NORTH_GOWER_ID = uuid.uuid4()
RUSSELL_ID = uuid.uuid4()
NO_COORD_ID = uuid.uuid4()


def _make_price(**overrides):
    values = {
        "snapshot_id": uuid.uuid4(),
        "location": "Testville",
        "location_id": NORTH_GOWER_ID,
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
        "id": NORTH_GOWER_ID,
        "org_id": ORG_ID,
        "name": "Testville",
        "canonical_key": "testville",
        "latitude": 45.05,
        "longitude": -75.55,
    }
    values.update(overrides)
    return Location(**values)


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Service: basis math and missing data
# ---------------------------------------------------------------------------


def test_basis_is_cash_minus_futures_per_bushel() -> None:
    computed = compute_basis_for_row(_make_price())
    assert computed.basis == pytest.approx(1.40)
    assert computed.cash_price_bu == pytest.approx(6.19)
    assert computed.futures_price == pytest.approx(4.79)
    assert computed.missing_reason is None
    assert computed.unit == "bu"
    assert computed.futures_month == "Dec 2026"


def test_missing_futures_price_returns_explicit_reason() -> None:
    computed = compute_basis_for_row(_make_price(futures_price=None))
    assert computed.basis is None
    assert computed.missing_reason == "missing_futures_price"
    assert computed.cash_price_bu == pytest.approx(6.19)


def test_missing_cash_price_returns_explicit_reason() -> None:
    computed = compute_basis_for_row(_make_price(cash_price_bu=None))
    assert computed.basis is None
    assert computed.missing_reason == "missing_cash_price"
    assert computed.futures_price == pytest.approx(4.79)


def test_missing_both_prices_returns_explicit_reason() -> None:
    computed = compute_basis_for_row(
        _make_price(cash_price_bu=None, futures_price=None)
    )
    assert computed.basis is None
    assert computed.missing_reason == "missing_cash_and_futures_prices"


def test_stored_basis_is_cross_checked_not_trusted() -> None:
    matching = compute_basis_for_row(_make_price())
    assert matching.basis_matches_stored is True
    assert matching.stored_basis == pytest.approx(1.40)

    mismatched = compute_basis_for_row(_make_price(basis=Decimal("2.00")))
    assert mismatched.basis == pytest.approx(1.40)  # recomputed value wins
    assert mismatched.basis_matches_stored is False
    assert "differs from recomputed basis" in mismatched.data_quality


def test_legacy_cents_stored_basis_is_normalised() -> None:
    # Legacy rows stored basis as cents (140 instead of 1.40).
    computed = compute_basis_for_row(_make_price(basis=Decimal("140")))
    assert computed.stored_basis == pytest.approx(1.40)
    assert computed.basis_matches_stored is True


def test_unit_mismatch_is_refused_not_converted() -> None:
    computed = compute_basis_for_row(_make_price(), row_unit="mt")
    assert computed.basis is None
    assert computed.missing_reason == "unit_mismatch"
    assert "Unit mismatch" in computed.data_quality


def test_currency_mismatch_is_refused_not_converted() -> None:
    computed = compute_basis_for_row(
        _make_price(), expected_currency="CAD", row_currency="USD"
    )
    assert computed.basis is None
    assert computed.missing_reason == "currency_mismatch"
    assert "Currency mismatch" in computed.data_quality


def test_currency_is_not_invented_when_not_stored() -> None:
    computed = compute_basis_for_row(_make_price())
    assert computed.currency is None
    assert "Currency is not stored" in computed.data_quality


# ---------------------------------------------------------------------------
# Service: history ordering and ranking
# ---------------------------------------------------------------------------


def test_history_is_sorted_oldest_first() -> None:
    pairs = [
        (_make_price(cash_price_bu=Decimal("6.30")), _make_snapshot(_dt(2026, 11, 17))),
        (_make_price(cash_price_bu=Decimal("6.10")), _make_snapshot(_dt(2026, 11, 15))),
        (_make_price(cash_price_bu=Decimal("6.19")), _make_snapshot(_dt(2026, 11, 16))),
    ]
    history = build_basis_history(pairs, commodity="corn", location_id=NORTH_GOWER_ID)
    assert [row["quote_date"] for row in history["rows"]] == [
        "2026-11-15",
        "2026-11-16",
        "2026-11-17",
    ]
    assert [row["basis"] for row in history["rows"]] == [
        pytest.approx(1.31),
        pytest.approx(1.40),
        pytest.approx(1.51),
    ]
    assert history["row_count"] == 3
    assert history["missing_count"] == 0
    assert history["currency"] is None
    assert history["unit"] == "bu"


def test_history_keeps_uncomputable_rows_with_reason() -> None:
    pairs = [
        (_make_price(), _make_snapshot(_dt(2026, 11, 15))),
        (_make_price(futures_price=None), _make_snapshot(_dt(2026, 11, 16))),
    ]
    history = build_basis_history(pairs, commodity="corn")
    assert history["row_count"] == 2
    assert history["missing_count"] == 1
    assert history["rows"][1]["basis"] is None
    assert history["rows"][1]["missing_reason"] == "missing_futures_price"


def test_history_respects_limit() -> None:
    pairs = [
        (_make_price(), _make_snapshot(_dt(2026, 11, day)))
        for day in (15, 16, 17)
    ]
    history = build_basis_history(pairs, limit=2)
    assert history["row_count"] == 2
    assert history["rows"][0]["quote_date"] == "2026-11-15"


def test_ranking_is_strongest_basis_first_and_latest_only() -> None:
    pairs = [
        # Testville: two quotes; only the latest (weaker basis) ranks.
        (_make_price(cash_price_bu=Decimal("6.50")), _make_snapshot(_dt(2026, 11, 15))),
        (_make_price(cash_price_bu=Decimal("6.19")), _make_snapshot(_dt(2026, 11, 17))),
        # Russell: strongest basis.
        (
            _make_price(
                location="Russell",
                location_id=RUSSELL_ID,
                cash_price_bu=Decimal("6.60"),
                composite_key="russell|corn|dec 2026|dec 2026",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
        # Empty Town: no futures price, so unranked, not dropped silently.
        (
            _make_price(
                location="Empty Town",
                location_id=NO_COORD_ID,
                futures_price=None,
                composite_key="empty town|corn|dec 2026|dec 2026",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
    ]
    result = rank_basis(pairs, commodity="corn")
    assert [row["location"] for row in result["ranked"]] == ["Russell", "Testville"]
    assert [row["rank"] for row in result["ranked"]] == [1, 2]
    assert result["ranked"][0]["basis"] == pytest.approx(1.81)
    assert result["ranked"][1]["basis"] == pytest.approx(1.40)
    assert len(result["unranked"]) == 1
    assert result["unranked"][0]["location"] == "Empty Town"
    assert result["unranked"][0]["missing_reason"] == "missing_futures_price"
    assert "no origin coordinates" in result["data_quality"].casefold() or "all locations" in result["data_quality"]


def test_ranking_excludes_rows_outside_radius() -> None:
    locations = [
        _make_location(),
        _make_location(
            id=RUSSELL_ID, name="Russell", canonical_key="russell",
            latitude=45.26, longitude=-75.36,
        ),
    ]
    pairs = [
        (_make_price(), _make_snapshot(_dt(2026, 11, 17))),
        (
            _make_price(
                location="Russell",
                location_id=RUSSELL_ID,
                cash_price_bu=Decimal("6.60"),
                composite_key="russell|corn|dec 2026|dec 2026",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
        (
            _make_price(
                location="NoCoord Town",
                location_id=NO_COORD_ID,
                futures_price=None,
                composite_key="nocoord town|corn|dec 2026|dec 2026",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
    ]
    # Russell is ~30 km from Testville; a 10 km radius keeps only Testville.
    result = rank_basis(
        pairs,
        locations=locations,
        origin=(45.05, -75.55),
        radius_km=10,
        commodity="corn",
    )
    assert [row["location"] for row in result["ranked"]] == ["Testville"]
    assert result["ranked"][0]["distance_km"] == pytest.approx(0.0)
    assert result["excluded_outside_radius"] == 1
    assert result["excluded_unknown_distance"] == 1


def test_pilot_origin_is_found_from_stored_locations_only() -> None:
    assert find_default_origin([]) is None
    assert find_default_origin([_make_location(name="Russell", canonical_key="russell")]) is None
    pilot = find_default_origin([_make_location()])
    assert pilot is not None and pilot.name == "Testville"
    # A pilot match without coordinates is returned, never given invented ones.
    no_coord = find_default_origin(
        [_make_location(latitude=None, longitude=None)]
    )
    assert no_coord is not None
    assert no_coord.latitude is None


def test_empty_state_for_history_and_ranking() -> None:
    history = build_basis_history([], commodity="corn")
    assert history["rows"] == []
    assert history["row_count"] == 0
    assert "No normalized price rows found" in history["data_quality"]

    ranked = rank_basis([], commodity="corn")
    assert ranked["ranked"] == []
    assert ranked["unranked"] == []
    assert ranked["row_count"] == 0


# ---------------------------------------------------------------------------
# Routes (fake session dispatching on the queried table, advisor pattern)
# ---------------------------------------------------------------------------


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


class _FakeSession:
    def __init__(self, *, price_pairs=None, locations=None) -> None:
        self._price_pairs = price_pairs or []
        self._locations = locations or []

    def execute(self, query):
        if "locations" in str(query):
            return _FakeResult(self._locations)
        return _FakeResult(self._price_pairs)


def _make_client(db):
    test_app = FastAPI()
    test_app.include_router(basis_router)

    def override_db():
        yield db

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
                cash_price_bu=Decimal("6.60"),
                composite_key="russell|corn|dec 2026|dec 2026",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
        (
            _make_price(
                location="NoCoord Town",
                location_id=NO_COORD_ID,
                futures_price=None,
                composite_key="nocoord town|corn|dec 2026|dec 2026",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
    ]


def _locations():
    return [
        _make_location(),
        _make_location(
            id=RUSSELL_ID, name="Russell", canonical_key="russell",
            latitude=45.26, longitude=-75.36,
        ),
    ]


def test_tracker_route_ranks_and_reports_provenance() -> None:
    client = _make_client(_FakeSession(price_pairs=_tracker_pairs(), locations=_locations()))
    try:
        response = client.get("/api/basis/tracker", params={"commodity": "corn"})
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["currency"] is None
    assert body["unit"] == "bu"
    assert body["origin"]["location"] == "Testville"
    assert body["origin"]["source"] == "pilot: Testville"
    assert [row["location"] for row in body["ranked"]] == ["Russell", "Testville"]
    assert body["ranked"][0]["rank"] == 1
    assert len(body["unranked"]) == 1
    assert body["unranked"][0]["location"] == "NoCoord Town"
    assert body["unranked"][0]["missing_reason"] == "missing_futures_price"
    first = body["ranked"][0]
    assert first["source"] == "Test Elevator Co."
    assert first["quote_date"] == "2026-11-17"
    assert first["futures_month"] == "Dec 2026"
    assert first["data_quality"]
    assert body["row_count"] == 2
    assert body["unranked_count"] == 1


def test_tracker_route_radius_excludes_far_and_unknown_locations() -> None:
    client = _make_client(_FakeSession(price_pairs=_tracker_pairs(), locations=_locations()))
    try:
        response = client.get(
            "/api/basis/tracker",
            params={"commodity": "corn", "radius_km": 10},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert [row["location"] for row in body["ranked"]] == ["Testville"]
    assert body["excluded_outside_radius"] == 1
    assert body["excluded_unknown_distance"] == 1


def test_tracker_route_filters_by_delivery_month() -> None:
    pairs = [
        (_make_price(), _make_snapshot(_dt(2026, 11, 17))),
        (
            _make_price(
                location="Russell",
                location_id=RUSSELL_ID,
                futures_month="Mar 2027",
                delivery_label="March 2027",
                cash_price_bu=Decimal("6.60"),
                composite_key="russell|corn|mar 2027|mar 2027",
            ),
            _make_snapshot(_dt(2026, 11, 17)),
        ),
    ]
    client = _make_client(_FakeSession(price_pairs=pairs, locations=_locations()))
    try:
        response = client.get(
            "/api/basis/tracker",
            params={"commodity": "corn", "delivery_month": "2026-12"},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    assert [row["location"] for row in response.json()["ranked"]] == ["Testville"]


def test_tracker_route_rejects_radius_without_resolvable_origin() -> None:
    client = _make_client(_FakeSession(price_pairs=_tracker_pairs(), locations=[]))
    try:
        response = client.get(
            "/api/basis/tracker",
            params={"commodity": "corn", "radius_km": 50},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "radius_km needs an origin" in response.json()["detail"]


def test_tracker_route_rejects_bad_delivery_month() -> None:
    client = _make_client(_FakeSession(price_pairs=_tracker_pairs(), locations=_locations()))
    try:
        response = client.get(
            "/api/basis/tracker",
            params={"commodity": "corn", "delivery_month": "not-a-month"},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 400


def test_tracker_route_empty_state() -> None:
    client = _make_client(_FakeSession(price_pairs=[], locations=[]))
    try:
        response = client.get("/api/basis/tracker", params={"commodity": "corn"})
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["ranked"] == []
    assert body["row_count"] == 0
    assert body["origin"] is None


def test_history_route_returns_oldest_first() -> None:
    pairs = [
        (_make_price(cash_price_bu=Decimal("6.30")), _make_snapshot(_dt(2026, 11, 17))),
        (_make_price(cash_price_bu=Decimal("6.10")), _make_snapshot(_dt(2026, 11, 15))),
    ]
    client = _make_client(_FakeSession(price_pairs=pairs, locations=[]))
    try:
        response = client.get(
            "/api/basis/history",
            params={"commodity": "corn", "location_id": str(NORTH_GOWER_ID)},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert [row["quote_date"] for row in body["rows"]] == ["2026-11-15", "2026-11-17"]
    assert body["rows"][0]["basis"] == pytest.approx(1.31)
    assert body["rows"][0]["source"] == "Test Elevator Co."
    assert body["currency"] is None
    assert body["unit"] == "bu"
    assert body["data_quality"]


def test_history_route_empty_state() -> None:
    client = _make_client(_FakeSession(price_pairs=[], locations=[]))
    try:
        response = client.get("/api/basis/history", params={"commodity": "corn"})
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == []
    assert body["row_count"] == 0
    assert "No normalized price rows found" in body["data_quality"]
