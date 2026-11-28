"""Tests for the Luckey Farmers own-JSON-API collector.

The fixture (tests/fixtures/luckey_sample.json) is a RECORDED LIVE
response from https://widgets-admin.luckeyfarmers.com/api/v1/cashbids,
fetched 2026-11-28 (200, 14 locations, 77 bids) and trimmed to two
locations (Curtice, 6 bids; Haskins, Wheat-only, 2 bids) with the
bid objects kept whole. Values below are live prices as published
2026-11-28, not invented test data. No live fetching inside pytest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import luckey_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_sample_parses_rows_across_locations_and_crops():
    result = luckey_source.parse_luckey_json(_read("luckey_sample.json"))
    assert result["status"] == "ok"
    assert result["company"] == "Luckey Farmers"
    assert result["location"] == "Curtice"  # first location in the payload
    assert len(result["rows"]) == 8
    assert sorted({row["location"] for row in result["rows"]}) == [
        "Curtice",
        "Haskins",
    ]
    # The API publishes "Soybean" (singular) — canonicalised to Soybeans.
    assert sorted({row["commodity"] for row in result["rows"]}) == [
        "Corn",
        "Soybeans",
        "Wheat",
    ]
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    # Delivery label is the bid "name" as published, not a month.
    assert sorted({row["delivery_month"] for row in result["rows"]}) == [
        "Cash",
        "NC 27",
    ]
    assert all(row["delivery_start"] is None for row in result["rows"])
    assert all(row["delivery_end"] is None for row in result["rows"])
    # Haskins is Wheat-only in the live payload.
    assert {row["commodity"] for row in result["rows"] if row["location"] == "Haskins"} == {
        "Wheat"
    }
    assert any("lastUpdatedAt" in n for n in result["notes"])
    assert any("2 location(s)" in n for n in result["notes"])


def test_tick_conversions_fractional_cents_to_dollars():
    # CBOT fractional cents with an apostrophe separator, eighths:
    # "446'6" = 446 6/8 cents -> $4.4675.
    assert luckey_source._tick_dollars("446'6") == pytest.approx(4.4675)
    assert luckey_source._tick_dollars("7'0") == pytest.approx(0.07)
    assert luckey_source._tick_dollars("1266'2") == pytest.approx(12.6625)
    assert luckey_source._tick_dollars("491'0") == pytest.approx(4.91)
    assert luckey_source._tick_dollars("22'2") == pytest.approx(0.2225)
    assert luckey_source._tick_dollars("") is None
    assert luckey_source._tick_dollars(None) is None


def test_curtice_corn_cash_values():
    result = luckey_source.parse_luckey_json(_read("luckey_sample.json"))
    corn = next(
        row
        for row in result["rows"]
        if row["location"] == "Curtice"
        and row["commodity"] == "Corn"
        and row["delivery_month"] == "Cash"
    )
    assert corn["cash_price"] == pytest.approx(4.29)
    assert corn["basis"] == pytest.approx(-0.18)
    # futuresPriceTick "446'6" -> $4.4675; futuresChangeTick "7'0"
    # with futuresChangeSign 1 -> +$0.07.
    assert corn["futures_price"] == pytest.approx(4.4675)
    assert corn["futures_month"] == "Dec 26"
    assert corn["futures_symbol"] == "ZCZ26"
    assert corn["futures_change"] == pytest.approx(0.07)
    assert corn["change"] == pytest.approx(0.07)
    # Cash = futures + basis, as published: 4.4675 - 0.18 = 4.2875 ~ 4.29.
    assert corn["cash_price"] == pytest.approx(
        corn["futures_price"] + corn["basis"], abs=0.01
    )
    assert corn["expiration"] == "2026-12-13T19:00:00.000-05:00"
    assert corn["note"] == ""


def test_curtice_new_crop_and_soybean_values():
    result = luckey_source.parse_luckey_json(_read("luckey_sample.json"))
    nc_corn = next(
        row
        for row in result["rows"]
        if row["location"] == "Curtice"
        and row["commodity"] == "Corn"
        and row["delivery_month"] == "NC 27"
    )
    # futuresPriceTick "491'0" -> $4.91; change "6'4" sign 1 -> +$0.065.
    assert nc_corn["cash_price"] == pytest.approx(4.48)
    assert nc_corn["basis"] == pytest.approx(-0.43)
    assert nc_corn["futures_price"] == pytest.approx(4.91)
    assert nc_corn["futures_month"] == "Dec 27"
    assert nc_corn["futures_symbol"] == "ZCZ27"
    assert nc_corn["change"] == pytest.approx(0.065)
    soy = next(
        row
        for row in result["rows"]
        if row["location"] == "Curtice"
        and row["commodity"] == "Soybeans"
        and row["delivery_month"] == "Cash"
    )
    # futuresPriceTick "1266'2" -> $12.6625; change "22'2" -> +$0.2225.
    assert soy["cash_price"] == pytest.approx(12.31)
    assert soy["basis"] == pytest.approx(-0.35)
    assert soy["futures_price"] == pytest.approx(12.6625)
    assert soy["futures_month"] == "Jan 27"
    assert soy["futures_symbol"] == "ZSF27"
    assert soy["change"] == pytest.approx(0.2225)


def test_haskins_wheat_only_rows():
    result = luckey_source.parse_luckey_json(_read("luckey_sample.json"))
    wheat = next(
        row
        for row in result["rows"]
        if row["location"] == "Haskins" and row["delivery_month"] == "Cash"
    )
    assert wheat["commodity"] == "Wheat"
    assert wheat["cash_price"] == pytest.approx(5.52)
    assert wheat["basis"] == pytest.approx(-0.15)
    # futuresPriceTick "566'4" -> $5.665; change "1'0" sign 1 -> +$0.01.
    assert wheat["futures_price"] == pytest.approx(5.665)
    assert wheat["futures_month"] == "Dec 26"
    assert wheat["futures_symbol"] == "ZWZ26"
    assert wheat["change"] == pytest.approx(0.01)


def test_change_sign_flips_negative_and_zero():
    # futuresChangeSign is the sign authority; the live 2026-11-28
    # snapshot had sign 1 on every bid, so -1 / 0 are exercised
    # synthetically against the documented convention.
    payload = {
        "data": {
            "locationId1": {
                "name": "Curtice",
                "cropId1": {
                    "name": "Corn",
                    "bids": [
                        {
                            "name": "Cash",
                            "basis": "-0.18",
                            "symbol": "ZCZ26",
                            "currentBid": "4.29",
                            "futuresMonth": "Dec 26",
                            "futuresPriceTick": "446'6",
                            "futuresChangeTick": "7'0",
                            "futuresChangeSign": -1,
                            "expiration": "2026-12-13T19:00:00.000-05:00",
                        },
                        {
                            "name": "NC 27",
                            "basis": "-0.43",
                            "symbol": "ZCZ27",
                            "currentBid": "4.48",
                            "futuresMonth": "Dec 27",
                            "futuresPriceTick": "491'0",
                            "futuresChangeTick": "6'4",
                            "futuresChangeSign": 0,
                            "expiration": "2027-12-13T19:00:00.000-05:00",
                        },
                    ],
                },
            }
        },
        "lastUpdatedAt": "2026-11-27T16:59:40.000-05:00",
    }
    result = luckey_source.parse_luckey_json(json.dumps(payload))
    assert result["status"] == "ok"
    assert len(result["rows"]) == 2
    assert result["rows"][0]["change"] == pytest.approx(-0.07)
    assert result["rows"][0]["futures_change"] == pytest.approx(-0.07)
    assert result["rows"][1]["change"] == pytest.approx(0.0)


def test_missing_fields_become_none_with_note():
    payload = {
        "data": {
            "locationId1": {
                "name": "Curtice",
                "cropId1": {
                    "name": "Corn",
                    "bids": [
                        {"name": "Cash", "currentBid": "4.29"},
                    ],
                },
            }
        }
    }
    result = luckey_source.parse_luckey_json(json.dumps(payload))
    assert result["status"] == "ok"
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["cash_price"] == pytest.approx(4.29)
    assert row["basis"] is None
    assert row["futures_price"] is None
    assert row["change"] is None
    assert "Bid only" in row["note"]


def test_invalid_json_is_unsupported():
    result = luckey_source.parse_luckey_json("<html>not json</html>")
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_missing_data_object_is_unsupported():
    result = luckey_source.parse_luckey_json(json.dumps({"kind": "normal"}))
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_empty_data_is_empty():
    result = luckey_source.parse_luckey_json(json.dumps({"data": {}}))
    assert result["status"] == "empty"
    assert result["rows"] == []


def test_fetch_luckey_uses_api_url_and_contact_user_agent() -> None:
    class _FakeResponse:
        text = _read("luckey_sample.json")

        def raise_for_status(self) -> None:
            pass

    with patch(
        "app.platform.market_data.sources.luckey_source.requests.get"
    ) as fake_get:
        fake_get.return_value = _FakeResponse()
        result = luckey_source.fetch_luckey()
    fake_get.assert_called_once()
    args, kwargs = fake_get.call_args
    assert args[0] == luckey_source.API_URL
    assert args[0] == "https://widgets-admin.luckeyfarmers.com/api/v1/cashbids"
    assert kwargs["headers"]["User-Agent"] == luckey_source.CONTACT_USER_AGENT
    assert result["status"] == "ok"
    assert result["company"] == "Luckey Farmers"
    assert len(result["rows"]) == 8
