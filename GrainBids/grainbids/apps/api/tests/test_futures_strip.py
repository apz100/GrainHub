"""Futures strip + ICE canola desk tests.

No live feed is wired, so these tests assert the honest contract
structure: every price/change/settle is null, ``available`` is False,
and the response says the licensed/delayed feed is not wired. If a
feed is ever wired, these tests must be updated to assert real values.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.futures import (  # noqa: E402
    CANOLA,
    STRIP_COMMODITIES,
    next_contracts,
    router as futures_router,
)


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(futures_router)
    return TestClient(app)


def test_next_contracts_for_corn_from_november() -> None:
    contracts = next_contracts("ZC", (3, 5, 7, 9, 12), date(2026, 11, 18), count=5)
    assert [c["symbol"] for c in contracts] == [
        "ZCZ26",
        "ZCH27",
        "ZCK27",
        "ZCN27",
        "ZCU27",
    ]
    assert contracts[0]["contract_month"] == "Dec 2026"
    assert all(c["price"] is None and c["change"] is None for c in contracts)


def test_next_contracts_for_canola_uses_ice_months() -> None:
    contracts = next_contracts("RS", (1, 3, 5, 7, 11), date(2026, 11, 18), count=4)
    assert [c["symbol"] for c in contracts] == ["RSX26", "RSF27", "RSH27", "RSK27"]
    assert all(c["month_code"] in {"F", "H", "K", "N", "X"} for c in contracts)


def test_strip_lists_all_grains_with_null_prices() -> None:
    payload = _client().get("/api/futures/strip").json()
    assert payload["available"] is False
    assert payload["feed_status"] == "not_wired"
    assert "10-15 min delayed" in payload["delay"]
    assert "is wired yet" in payload["note"]
    assert payload["as_of"] is None
    assert payload["source"] is None

    names = [block["commodity"] for block in payload["commodities"]]
    assert names == [row[0] for row in STRIP_COMMODITIES]
    assert names == [
        "Corn",
        "Soybeans",
        "Wheat (SRW)",
        "Wheat (HRW)",
        "Wheat (HRS)",
        "Oats",
    ]
    for block in payload["commodities"]:
        assert len(block["contracts"]) == 5
        assert block["exchange"] in {"CBOT", "KCBT", "MGEX"}
        for contract in block["contracts"]:
            assert contract["price"] is None
            assert contract["change"] is None
            assert contract["settle"] is None
            assert contract["symbol"].startswith(block["symbol_root"])


def test_strip_contract_months_are_not_in_the_past() -> None:
    payload = _client().get("/api/futures/strip").json()
    today = date.today()
    for block in payload["commodities"]:
        for contract in block["contracts"]:
            year = contract["year"]
            month_name = contract["contract_month"].split()[0]
            month = {
                "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
            }[month_name]
            assert (year, month) >= (today.year, today.month)


def test_canola_desk_is_ice_with_null_prices() -> None:
    payload = _client().get("/api/futures/canola").json()
    assert payload["desk"] == "ICE Canola Desk"
    assert payload["commodity"] == "Canola"
    assert payload["exchange"] == "ICE Futures Canada"
    assert payload["symbol_root"] == "RS"
    assert payload["unit"] == "CAD/tonne"
    assert payload["currency"] == "CAD"
    assert payload["available"] is False
    assert payload["feed_status"] == "not_wired"
    assert "is wired yet" in payload["note"]
    assert "ICE canola" in payload["note"]
    assert len(payload["contracts"]) == 5
    assert all(c["price"] is None for c in payload["contracts"])
    assert all(c["month_code"] in {"F", "H", "K", "N", "X"} for c in payload["contracts"])


def test_canola_definition_matches_expected_months() -> None:
    _commodity, exchange, root, months, _unit, _currency = CANOLA
    assert exchange == "ICE Futures Canada"
    assert root == "RS"
    assert months == (1, 3, 5, 7, 11)
