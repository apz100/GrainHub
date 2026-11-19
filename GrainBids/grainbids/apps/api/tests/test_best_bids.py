"""Tests for the public best-bid page API.

Route tests run the best_bids router standalone with the DB
dependency overridden by a fake session (same pattern as
test_advisor.py). Critically, no request-context override is
installed and no auth headers are sent: the endpoint must work
publicly. No real database, no external calls, no invented bids.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.best_bids import router as best_bids_router  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402

COMPANY_A = uuid.uuid4()
COMPANY_B = uuid.uuid4()


class _FakeResult:
    def __init__(self, *, rows=None) -> None:
        self._rows = list(rows or [])

    def all(self):
        return list(self._rows)


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


def _make_snapshot(captured_at):
    return PriceSnapshot(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        commodity_id=uuid.uuid4(),
        captured_at=captured_at,
    )


def _make_price(captured_at, **overrides):
    values = {
        "snapshot_id": uuid.uuid4(),
        "location": "North Gower",
        "commodity_name": "Corn",
        "cash_price_bu": Decimal("5.00"),
        "cash_price_mt": Decimal("196.85"),
        "basis": Decimal("0.50"),
        "futures_month": "July 2026",
        "delivery_label": "July 2026",
        "source_name": "Great Lakes Grain",
        "composite_key": "north gower|corn|july 2026|",
        "company_id": COMPANY_A,
    }
    values.update(overrides)
    return NormalizedPrice(**values)


def _pair(captured_at, **overrides):
    return (_make_price(captured_at, **overrides), _make_snapshot(captured_at))


def _make_client(db):
    # Deliberately no get_request_context override and no auth headers:
    # this endpoint is public.
    test_app = FastAPI()
    test_app.include_router(best_bids_router)

    def override_db():
        yield db

    test_app.dependency_overrides[get_db] = override_db
    return TestClient(test_app)


def test_best_bids_works_without_auth_headers() -> None:
    captured = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    rows = [_pair(captured, cash_price_bu=Decimal("5.25"))]
    client = _make_client(_FakeSession(price_rows=rows))
    response = client.get("/api/best-bids")  # no headers at all
    assert response.status_code == 200
    body = response.json()
    assert body["bid_count"] == 1
    bid = body["groups"][0]["bids"][0]
    assert bid["company_name"] == "Great Lakes Grain"
    assert bid["location"] == "North Gower"
    assert bid["cash_price_bu"] == 5.25
    assert bid["basis"] == 0.5
    assert bid["currency"] is None
    assert bid["unit"] == "bu"
    assert bid["quote_date"] == "2026-11-18"
    assert bid["source"] == "Great Lakes Grain"
    assert bid["commodity_name"] == "Corn"
    assert body["groups"][0]["delivery_month"] == "July 2026"


def test_best_bids_returns_empty_groups_when_no_prices_exist() -> None:
    client = _make_client(_FakeSession(price_rows=[]))
    response = client.get("/api/best-bids")
    assert response.status_code == 200
    assert response.json()["groups"] == []
    assert response.json()["bid_count"] == 0
    response = client.get("/api/best-bids", params={"commodity": "corn"})
    assert response.status_code == 200
    assert response.json()["groups"] == []


def test_best_bids_keeps_one_row_per_company_the_highest() -> None:
    captured = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    rows = [
        _pair(captured, cash_price_bu=Decimal("5.00"), company_id=COMPANY_A, source_name="Great Lakes Grain"),
        _pair(captured, cash_price_bu=Decimal("5.40"), company_id=COMPANY_A, source_name="Great Lakes Grain"),
        _pair(captured, cash_price_bu=Decimal("5.20"), company_id=COMPANY_B, source_name="Ingredion"),
    ]
    companies = [(COMPANY_A, "Great Lakes Grain"), (COMPANY_B, "Ingredion")]
    client = _make_client(_FakeSession(price_rows=rows, companies=companies))
    response = client.get("/api/best-bids")
    assert response.status_code == 200
    body = response.json()
    assert body["bid_count"] == 2
    bids = body["groups"][0]["bids"]
    assert [bid["company_name"] for bid in bids] == ["Great Lakes Grain", "Ingredion"]
    assert [bid["cash_price_bu"] for bid in bids] == [5.40, 5.20]


def test_best_bids_groups_by_commodity_and_delivery_month() -> None:
    captured = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    rows = [
        _pair(captured, commodity_name="Corn", delivery_label="July 2026", futures_month="July 2026"),
        _pair(
            captured,
            commodity_name="Soybeans",
            delivery_label="November 2026",
            futures_month="November 2026",
            cash_price_bu=Decimal("12.00"),
            company_id=COMPANY_B,
            source_name="Ingredion",
        ),
    ]
    client = _make_client(_FakeSession(price_rows=rows))
    response = client.get("/api/best-bids")
    assert response.status_code == 200
    groups = response.json()["groups"]
    assert {(g["commodity"], g["delivery_month"]) for g in groups} == {
        ("Corn", "July 2026"),
        ("Soybeans", "November 2026"),
    }


def test_best_bids_filters_by_commodity_and_respects_limit() -> None:
    captured = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    rows = [
        _pair(captured, commodity_name="Corn", cash_price_bu=Decimal("5.00")),
        _pair(
            captured,
            commodity_name="Soybeans",
            cash_price_bu=Decimal("12.00"),
            company_id=COMPANY_B,
            source_name="Ingredion",
        ),
    ]
    client = _make_client(_FakeSession(price_rows=rows))
    body = client.get("/api/best-bids", params={"commodity": "soy"}).json()
    assert body["bid_count"] == 1
    assert body["groups"][0]["commodity"] == "Soybeans"

    body = client.get("/api/best-bids", params={"limit": 1}).json()
    assert body["bid_count"] == 1
    assert body["groups"][0]["bids"][0]["cash_price_bu"] == 12.00


def test_best_bids_response_contains_no_user_data() -> None:
    captured = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    client = _make_client(_FakeSession(price_rows=[_pair(captured)]))
    response = client.get("/api/best-bids")
    assert response.status_code == 200
    lowered = response.text.lower()
    for forbidden in ("watchlist", "alert", "user", "password", "email", "account"):
        assert forbidden not in lowered
