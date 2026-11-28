"""Tests for the DG Global own-JSON-API collector.

The fixture (tests/fixtures/dg_global_sample.json) is a RECORDED LIVE
response from https://dgglobal.ca/api/markets/cash-bids, fetched
2026-11-28 (200, ``available: true``, 5 Ontario destinations, 45
bids) and trimmed to two destinations (Becher, Princeton — one
delivery per type each, 6 bids) with the bid objects kept whole.
Values below are live prices as published 2026-11-28, not invented
test data. No live fetching inside pytest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import dg_global_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_sample_parses_rows_across_destinations_and_crops():
    result = dg_global_source.parse_dg_global_json(_read("dg_global_sample.json"))
    assert result["status"] == "ok"
    assert result["company"] == "DG Global"
    assert result["location"] == "Becher"  # first location in the payload
    assert len(result["rows"]) == 6
    assert sorted({row["location"] for row in result["rows"]}) == [
        "Becher",
        "Princeton",
    ]
    assert sorted({row["commodity"] for row in result["rows"]}) == [
        "Corn",
        "Soybeans",
        "Wheat — SRW",
    ]
    assert all(row["currency"] == "CAD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    # Delivery label is the delivery string as published ("Dec 2026").
    assert {row["delivery_month"] for row in result["rows"]} == {"Dec 2026"}
    assert all(row["delivery_start"] is None for row in result["rows"])
    assert all(row["delivery_end"] is None for row in result["rows"])
    assert any("updatedAt" in n for n in result["notes"])
    assert any("delayed" in n for n in result["notes"])


def test_tick_conversion_matches_published_cash():
    """cash = futures + basis on the live rows (validates the tick math)."""
    result = dg_global_source.parse_dg_global_json(_read("dg_global_sample.json"))
    corn = next(
        r
        for r in result["rows"]
        if r["location"] == "Becher" and r["commodity"] == "Corn"
    )
    # futures "463'0" -> $4.63, basis 1.15, cash 5.78 as published.
    assert corn["futures_price"] == pytest.approx(4.63)
    assert corn["basis"] == pytest.approx(1.15)
    assert corn["cash_price"] == pytest.approx(5.78)
    assert corn["cash_price"] == pytest.approx(
        corn["futures_price"] + corn["basis"], abs=0.01
    )
    assert corn["futures_month"] == "Mar 2027"
    assert corn["futures_symbol"] == "@C7H"
    # change "6'4" -> 6.5 cents -> $0.065, direction up -> positive.
    assert corn["change"] == pytest.approx(0.065)
    assert corn["futures_change"] == pytest.approx(0.065)
    # converted is the $/MT cash price as published.
    assert corn["cash_price_mt"] == pytest.approx(227.55)


def test_wheat_srw_canonicalised():
    result = dg_global_source.parse_dg_global_json(_read("dg_global_sample.json"))
    wheat = [r for r in result["rows"] if r["commodity"] == "Wheat — SRW"]
    assert len(wheat) == 2
    assert wheat[0]["cash_price"] == pytest.approx(7.11)


def test_bad_json_is_unsupported_not_a_crash():
    result = dg_global_source.parse_dg_global_json("not json at all")
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_empty_data_list_is_empty():
    result = dg_global_source.parse_dg_global_json(
        json.dumps({"available": True, "stale": False, "data": []})
    )
    assert result["status"] == "empty"
    assert result["rows"] == []


def test_fetch_uses_the_json_api(monkeypatch):
    """fetch_dg_global hits the DG Global API (mocked) and parses it."""
    calls = {}

    def fake_get(url, headers=None, timeout=None):
        calls["url"] = url

        class Resp:
            text = _read("dg_global_sample.json")

            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setattr(dg_global_source.requests, "get", fake_get)
    result = dg_global_source.fetch_dg_global()
    assert calls["url"] == dg_global_source.API_URL
    assert result["status"] == "ok"
    assert len(result["rows"]) == 6


def test_fetch_accepts_ignored_playwright_arg(monkeypatch):
    """The legacy orchestrator still calls fetchers with a Playwright
    instance; the JSON collector accepts and ignores it."""
    monkeypatch.setattr(
        dg_global_source,
        "fetch_dg_global_html",
        lambda url=dg_global_source.API_URL, timeout=30: _read(
            "dg_global_sample.json"
        ),
    )
    result = dg_global_source.fetch_dg_global(object())
    assert result["status"] == "ok"


def test_registry_entry_is_direct_dict():
    """The registry must call the JSON collector without a browser."""
    from app.services.source_registry import get_adapter

    adapter = get_adapter("dg_global")
    assert adapter.mode == "direct_dict"
    assert adapter.module == "dg_global_source"
    assert adapter.function == "fetch_dg_global"


def test_registry_direct_dict_runner_returns_rows(monkeypatch):
    """End-to-end through fetch_with_adapter with the HTTP layer mocked."""
    from app.services.source_registry import fetch_with_adapter, get_adapter

    def fake_get(url, headers=None, timeout=None):
        class Resp:
            text = _read("dg_global_sample.json")

            def raise_for_status(self):
                return None

        return Resp()

    monkeypatch.setattr(dg_global_source.requests, "get", fake_get)
    df = fetch_with_adapter(get_adapter("dg_global"))
    assert not df.empty
    assert len(df) == 6
    assert set(df["location"]) == {"Becher", "Princeton"}
