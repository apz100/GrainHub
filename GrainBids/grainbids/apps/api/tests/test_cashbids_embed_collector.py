"""Tests for the generic AgriCharts cashbids.php-embed collector.

The eight embed sites (Agtegra, Heritage Coop, Linn Coop, Midway
Coop, Ag State, Superior Ag — Cycle 7 — plus ALCIVIA and TGM,
Cycle 9) all serve their bids from a ``cashbids-js.php`` endpoint
whose response carries a ``var bids`` JSON payload (verified live
2026-11-19, one polite GET per URL — see ``cashbids_embed_source.py``).
These tests lock the parser in with synthetic fixtures — no live
fetching inside pytest, fixture values are invented test data, not
live prices.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import cashbids_embed_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_sample_parses_rows_groupby_location():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_sample.html"),
        company="Agtegra",
        currency="USD",
        default_location="Hecla",
    )
    assert result["status"] == "ok"
    assert result["company"] == "Agtegra"
    # 6 cashbids in the payload minus 1 login-gated minus 1 inactive.
    assert len(result["rows"]) == 4
    assert result["location"] == "Hecla"
    locations = sorted({row["location"] for row in result["rows"]})
    assert locations == ["Hecla", "Warner"]
    assert sorted({row["commodity"] for row in result["rows"]}) == [
        "Corn",
        "Soybeans",
    ]
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])


def test_units_conversions_cents_and_fractional_futures():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_sample.html"), company="Agtegra"
    )
    corn = next(
        row
        for row in result["rows"]
        if row["commodity"] == "Corn" and row["location"] == "Hecla"
        and row["delivery_month"] == "Nov 2026"
    )
    # futures "500-0" = 500.0 cents -> $5.00; basis -25 cents -> -$0.25.
    assert corn["futures_price"] == pytest.approx(5.00)
    assert corn["basis"] == pytest.approx(-0.25)
    assert corn["cash_price"] == pytest.approx(4.75)
    assert corn["cash_price_mt"] == pytest.approx(175.25)
    # change comes from rawchange (dollars), not the fractional field.
    assert corn["change"] == pytest.approx(-0.03)
    # futures change "-2-4" = -2.5 cents -> -$0.025.
    assert corn["futures_change"] == pytest.approx(-0.025)
    assert corn["futures_month"] == "Dec 2026"
    assert corn["futures_symbol"] == "ZCZ26"
    assert corn["delivery_start"] == "11/01/2026"
    assert corn["delivery_end"] == "11/30/2026"


def test_fractional_futures_soybeans():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_sample.html"), company="Agtegra"
    )
    soy = next(
        row for row in result["rows"] if row["commodity"] == "Soybeans"
    )
    # futures "1212-4" = 1212.5 cents -> $12.125; basis -40 cents.
    assert soy["futures_price"] == pytest.approx(12.125)
    assert soy["basis"] == pytest.approx(-0.40)
    assert soy["futures_change"] == pytest.approx(-0.04)


def test_delivery_month_label_from_delivery_start():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_sample.html"), company="Agtegra"
    )
    new_crop = next(
        row
        for row in result["rows"]
        if row["delivery_start"] == "10/01/2027"
    )
    assert new_crop["delivery_month"] == "Oct 2027"
    assert new_crop["futures_month"] == "Dec 2027"


def test_login_gated_and_inactive_rows_skipped_and_noted():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_sample.html"), company="Agtegra"
    )
    assert len(result["rows"]) == 4
    notes = " ".join(result["notes"])
    assert "1 login-gated" in notes
    assert "1 inactive" in notes


def test_groupby_commodity_uses_location_name_not_group_name():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_groupby_commodity_sample.html"),
        company="Ag State",
        currency="USD",
        default_location="A.C.",
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 3
    # Group names are commodities ("Corn" / "Soybeans") — they must
    # never leak into the location field.
    assert all(row["location"] == "A.C." for row in result["rows"])
    assert result["location"] == "A.C."
    assert sorted({row["commodity"] for row in result["rows"]}) == [
        "Corn",
        "Soybeans",
    ]
    # Grade-prefixed label "#2 Yellow Corn" canonicalizes to Corn.
    assert sum(1 for row in result["rows"] if row["commodity"] == "Corn") == 2
    jan_row = next(
        row for row in result["rows"] if row["delivery_start"] == "01/01/2027"
    )
    assert jan_row["delivery_month"] == "Jan 2027"
    assert jan_row["futures_month"] == "Mar 2027"
    assert jan_row["futures_price"] == pytest.approx(5.1525)


def test_no_payload_is_unsupported_not_table_parsed():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_no_payload.html"), company="Agtegra"
    )
    assert result["status"] == "unsupported"
    assert result["rows"] == []
    assert "var bids" in " ".join(result["notes"])


def test_empty_payload_is_empty():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_empty_bids.html"), company="Agtegra"
    )
    assert result["status"] == "empty"
    assert result["rows"] == []


def test_alcivia_groupby_location_rows_across_locations():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_alcivia_sample.html"),
        company="ALCIVIA",
        currency="USD",
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 3
    assert result["location"] == "BALDWIN"
    assert sorted({row["location"] for row in result["rows"]}) == [
        "BALDWIN",
        "EVANSVILLE",
    ]
    assert sorted({row["commodity"] for row in result["rows"]}) == [
        "Corn",
        "Soybeans",
        "Wheat",
    ]
    corn = next(
        row for row in result["rows"] if row["commodity"] == "Corn"
    )
    # futures "410-0" = 410.0 cents -> $4.10; basis -30 cents.
    assert corn["futures_price"] == pytest.approx(4.10)
    assert corn["basis"] == pytest.approx(-0.30)
    assert corn["cash_price"] == pytest.approx(3.80)
    assert corn["delivery_month"] == "Nov 2026"


def test_tgm_groupby_commodity_beans_maps_to_soybeans():
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_tgm_sample.html"),
        company="TGM",
        currency="USD",
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 3
    # Group names are commodities ("Corn" / "Beans" / "White Corn") —
    # they must never leak into the location field.
    assert sorted({row["location"] for row in result["rows"]}) == [
        "Arcola",
        "Neoga",
    ]
    assert result["location"] == "Arcola"
    # TGM labels soybeans "Beans" (ZS symbols on the live rows).
    beans = next(
        row for row in result["rows"] if row["location"] == "Neoga"
    )
    assert beans["commodity"] == "Soybeans"
    assert beans["futures_symbol"] == "ZSF27"
    assert beans["delivery_month"] == "Jan 2027"
    # "White Corn" is a distinct published label — kept as-is.
    white = next(
        row for row in result["rows"] if row["commodity"] == "White Corn"
    )
    assert white["location"] == "Arcola"
    assert white["futures_price"] == pytest.approx(4.20)


def test_registry_eight_verified_sites_and_key_errors():
    sites = cashbids_embed_source.CASHBIDS_EMBED_SITES
    assert sorted(sites) == [
        "ag_state",
        "agtegra",
        "alcivia",
        "heritage_coop",
        "linn_coop",
        "midway_coop",
        "superior_ag",
        "tgm",
    ]
    for key, site in sites.items():
        assert site.verified is True
        assert "cashbids-js.php" in site.js_url
        assert site.js_url.startswith("https://")
        assert ".agricharts.com/inc/cashbids/" in site.js_url
        assert site.currency == "USD"
    with pytest.raises(KeyError):
        cashbids_embed_source.get_cashbids_embed_site("no_such_site")
    assert cashbids_embed_source.get_cashbids_embed_site("AgTeGra").key == "agtegra"


def test_registry_new_sites_use_verified_live_js_urls():
    alcivia = cashbids_embed_source.get_cashbids_embed_site("alcivia")
    assert alcivia.company == "ALCIVIA"
    assert alcivia.js_url.startswith(
        "https://alciviacoop.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=&commodity=&groupby=location"
    )
    assert alcivia.js_url.endswith("&&acCnt=1")
    assert alcivia.default_location is None  # 15 locations, filter=all
    tgm = cashbids_embed_source.get_cashbids_embed_site("tgm")
    assert tgm.company == "TGM"
    assert tgm.js_url.startswith(
        "https://totalgrain.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=&commodity=&groupby=ccommodity"
    )
    assert tgm.js_url.endswith("&&acCnt=1")
    assert tgm.default_location is None  # 24 locations, filter=all


def test_site_parse_path_uses_registry_defaults_for_new_sites():
    alcivia = cashbids_embed_source.get_cashbids_embed_site("alcivia")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_alcivia_sample.html"), site=alcivia
    )
    assert result["company"] == "ALCIVIA"
    assert result["status"] == "ok"
    assert len(result["rows"]) == 3
    tgm = cashbids_embed_source.get_cashbids_embed_site("tgm")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_tgm_sample.html"), site=tgm
    )
    assert result["company"] == "TGM"
    assert result["status"] == "ok"
    assert {row["commodity"] for row in result["rows"]} == {
        "Corn",
        "Soybeans",
        "White Corn",
    }


def test_site_parse_path_uses_registry_defaults():
    site = cashbids_embed_source.get_cashbids_embed_site("heritage_coop")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_groupby_commodity_sample.html"), site=site
    )
    assert result["company"] == "Heritage Cooperative"
    assert result["status"] == "ok"
