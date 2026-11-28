"""Tests for the generic AgriCharts cashbids.php-embed collector.

The twenty-one embed sites (Agtegra, Heritage Coop, Linn Coop, Midway
Coop, Ag State, Superior Ag — Cycle 7 — plus ALCIVIA and TGM,
Cycle 9, plus PRO Coop, Cycle 11, plus PRO Coop 21302, Hull Coop
and StateLine Coop, Cycle 12, plus CGB, Key Cooperative, Garden City
Coop, Farmward Cooperative, Farmers Cooperative Dorchester and Mid
Iowa Coop, 2026-11-27, plus Evergreen FS and Star of the West,
2026-11-28) all serve their bids from a
``cashbids-js.php`` endpoint whose response carries a ``var bids``
JSON payload (verified live, one polite GET per URL — see
``cashbids_embed_source.py``). The Cycle 7–13 tests lock the parser
in with synthetic fixtures — no live fetching inside pytest, fixture
values are invented test data, not live prices. The 2026-11-27 tests
use RECORDED LIVE fixtures: trimmed copies of the live
cashbids-js.php responses (1–2 location groups), so their values are
the published prices as of 2026-11-27, not invented test data. The
2026-11-28 tests (Evergreen FS, Star of the West) are recorded
live the same way.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

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


def test_registry_twenty_one_verified_sites_and_key_errors():
    sites = cashbids_embed_source.CASHBIDS_EMBED_SITES
    assert sorted(sites) == [
        "ag_state",
        "agtegra",
        "alcivia",
        "cgb",
        "dorchester",
        "evergreen_fs",
        "farmward",
        "garden_city",
        "heritage_coop",
        "hull_coop",
        "key_coop",
        "linn_coop",
        "mid_iowa",
        "midway_coop",
        "pro_coop",
        "pro_coop_21302",
        "pro_coop_21302b",
        "star_of_the_west",
        "stateline_coop",
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
    pro_coop = cashbids_embed_source.get_cashbids_embed_site("pro_coop")
    assert pro_coop.company == "PRO Coop"
    assert pro_coop.js_url.startswith(
        "https://procooperative.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=location&location=21297&commodity=&groupby=location"
    )
    assert pro_coop.js_url.endswith("&&acCnt=1")
    assert pro_coop.default_location == "AYRSHIRE.IA"  # 1 location, 21297
    pro_coop_21302 = cashbids_embed_source.get_cashbids_embed_site(
        "pro_coop_21302"
    )
    assert pro_coop_21302.company == "PRO Coop"
    assert pro_coop_21302.js_url.startswith(
        "https://procooperative.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=location&location=21302&commodity=&groupby=ccommodity"
    )
    assert pro_coop_21302.js_url.endswith("&&acCnt=1")
    assert pro_coop_21302.default_location == "MANSON.IA"  # 1 location, 21302
    pro_coop_21302b = cashbids_embed_source.get_cashbids_embed_site(
        "pro_coop_21302b"
    )
    assert pro_coop_21302b.company == "PRO Coop"
    assert pro_coop_21302b.js_url.startswith(
        "https://procooperative.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=location&location=21302&commodity=&groupby=ccommodity"
    )
    # Second 21302 embed: its fields list omits delivery_end.
    assert "delivery_end" not in pro_coop_21302b.js_url
    assert pro_coop_21302b.js_url.endswith("&&acCnt=1")
    assert pro_coop_21302b.default_location == "MANSON.IA"  # 1 location, 21302
    hull_coop = cashbids_embed_source.get_cashbids_embed_site("hull_coop")
    assert hull_coop.company == "Hull Coop"
    assert hull_coop.js_url.startswith(
        "https://hullcoopresp.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=&commodity=&groupby=ccommodity"
    )
    assert hull_coop.js_url.endswith("&&acCnt=1")
    assert hull_coop.default_location == "Hull"  # 1 location, filter=all
    stateline = cashbids_embed_source.get_cashbids_embed_site("stateline_coop")
    assert stateline.company == "StateLine Coop"
    assert stateline.js_url.startswith(
        "https://statelinecoop.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=&commodity=&groupby=location"
    )
    assert stateline.js_url.endswith("&&acCnt=1")
    assert stateline.default_location is None  # 11 locations, filter=all
    # 2026-11-27 — Farmbucks US-buyer sweep (recorded-live fixtures).
    cgb = cashbids_embed_source.get_cashbids_embed_site("cgb")
    assert cgb.company == "CGB"
    assert cgb.js_url.startswith(
        "https://cgb.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=79619&commodity&groupby=location"
    )
    # The loader's fields list and dateformat are unencoded (literal
    # commas, %m/%d/%Y) — kept verbatim in the js_url.
    assert "dateformat=%m/%d/%Y" in cgb.js_url
    assert cgb.js_url.endswith("&&acCnt=1")
    assert cgb.default_location == "CGB - MEEKERS LANDING"  # 1 location
    key_coop = cashbids_embed_source.get_cashbids_embed_site("key_coop")
    assert key_coop.company == "Key Cooperative"
    assert key_coop.js_url.startswith(
        "https://keycoop.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=&commodity=&groupby=location"
    )
    assert "setLocation=86090" in key_coop.js_url
    assert key_coop.js_url.endswith("&&acCnt=1")
    assert key_coop.default_location == "Barnes City"  # 1 location
    garden_city = cashbids_embed_source.get_cashbids_embed_site("garden_city")
    assert garden_city.company == "Garden City Coop"
    assert garden_city.js_url.startswith(
        "https://gccoop.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=62859&commodity=&groupby=location"
    )
    assert garden_city.js_url.endswith("&&acCnt=1")
    assert garden_city.default_location == "Garden City Elevator"  # 1 location
    farmward = cashbids_embed_source.get_cashbids_embed_site("farmward")
    assert farmward.company == "Farmward Cooperative"
    assert farmward.js_url.startswith(
        "https://farmward.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=&commodity=&groupby=location"
    )
    assert farmward.js_url.endswith("&&acCnt=1")
    assert farmward.default_location is None  # 10 locations, filter=all
    dorchester = cashbids_embed_source.get_cashbids_embed_site("dorchester")
    assert dorchester.company == "Farmers Cooperative Dorchester"
    assert dorchester.js_url.startswith(
        "https://farmersco-operative.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=28468&commodity=&groupby=commodity"
    )
    assert dorchester.js_url.endswith("&&acCnt=1")
    assert dorchester.default_location == "BEATRICE"  # 1 location
    mid_iowa = cashbids_embed_source.get_cashbids_embed_site("mid_iowa")
    assert mid_iowa.company == "Mid Iowa Coop"
    assert mid_iowa.js_url.startswith(
        "https://midiowa.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=&commodity=&groupby=location"
    )
    # The loader's fields list omits 'name' — the payload still
    # carries it on every row.
    assert "fields=delivery_start" in mid_iowa.js_url
    assert mid_iowa.js_url.endswith("&&acCnt=1")
    assert mid_iowa.default_location is None  # 30 locations, filter=all


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


# ---------------------------------------------------------------------------
# PRO Coop (Cycle 11) — location 21297, Ayrshire IA, Corn only
# ---------------------------------------------------------------------------


def test_pro_coop_sample_parses_ayrshire_corn_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("pro_coop")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_pro_coop_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "PRO Coop"
    # 4 cashbids in the payload minus 1 login-gated minus 1 inactive.
    assert len(result["rows"]) == 2
    assert result["location"] == "AYRSHIRE.IA"
    assert {row["location"] for row in result["rows"]} == {"AYRSHIRE.IA"}
    assert {row["commodity"] for row in result["rows"]} == {"Corn"}
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])


def test_pro_coop_units_conversions():
    site = cashbids_embed_source.get_cashbids_embed_site("pro_coop")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_pro_coop_sample.html"), site=site
    )
    dec = next(
        row
        for row in result["rows"]
        if row["futures_symbol"] == "ZCZ26"
    )
    # futures "500-0" = 500.0 cents -> $5.00; basis -25 cents -> -$0.25.
    assert dec["futures_price"] == pytest.approx(5.00)
    assert dec["basis"] == pytest.approx(-0.25)
    assert dec["cash_price"] == pytest.approx(4.75)
    assert dec["cash_price_mt"] == pytest.approx(175.25)
    assert dec["change"] == pytest.approx(-0.03)
    assert dec["futures_change"] == pytest.approx(-0.025)
    assert dec["futures_month"] == "Dec 2026"
    assert dec["delivery_month"] == "Nov 2026"
    mar = next(
        row
        for row in result["rows"]
        if row["futures_symbol"] == "ZCH27"
    )
    # futures "510-2" = 510.25 cents -> $5.1025; basis -30 cents.
    assert mar["futures_price"] == pytest.approx(5.1025)
    assert mar["basis"] == pytest.approx(-0.30)
    assert mar["futures_month"] == "Mar 2027"
    assert mar["delivery_month"] == "Mar 2027"


def test_pro_coop_login_gated_and_inactive_rows_skipped_and_noted():
    site = cashbids_embed_source.get_cashbids_embed_site("pro_coop")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_pro_coop_sample.html"), site=site
    )
    assert len(result["rows"]) == 2
    notes = " ".join(result["notes"])
    assert "1 login-gated" in notes
    assert "1 inactive" in notes


def test_fetch_pro_coop_uses_verified_url() -> None:
    html = _read("cashbids_embed_pro_coop_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_pro_coop()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("pro_coop").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "PRO Coop"
    assert len(result["rows"]) == 2


# ---------------------------------------------------------------------------
# Cycle 12 — PRO Coop 21302 (Manson, IA), Hull Coop, StateLine Coop
# ---------------------------------------------------------------------------


def test_pro_coop_21302_sample_parses_manson_corn_soybeans_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("pro_coop_21302")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_pro_coop_21302_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "PRO Coop"
    # 4 cashbids in the payload minus 1 login-gated.
    assert len(result["rows"]) == 3
    assert result["location"] == "MANSON.IA"
    assert {row["location"] for row in result["rows"]} == {"MANSON.IA"}
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    dec = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZCZ26"
    )
    # futures "500-0" = 500.0 cents -> $5.00; basis -25 cents -> -$0.25.
    assert dec["futures_price"] == pytest.approx(5.00)
    assert dec["basis"] == pytest.approx(-0.25)
    assert dec["cash_price"] == pytest.approx(4.75)
    assert dec["futures_month"] == "Dec 2026"
    assert dec["delivery_month"] == "Nov 2026"
    notes = " ".join(result["notes"])
    assert "1 login-gated" in notes


def test_fetch_pro_coop_21302_uses_verified_url() -> None:
    html = _read("cashbids_embed_pro_coop_21302_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_pro_coop_21302()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("pro_coop_21302").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "PRO Coop"
    assert result["location"] == "MANSON.IA"
    assert len(result["rows"]) == 3


# ---------------------------------------------------------------------------
# Cycle 13 — PRO Coop 21302, second embed (Manson, IA)
# ---------------------------------------------------------------------------


def test_pro_coop_21302b_sample_parses_manson_corn_soybeans_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("pro_coop_21302b")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_pro_coop_21302b_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "PRO Coop"
    # 4 cashbids in the payload minus 1 login-gated.
    assert len(result["rows"]) == 3
    assert result["location"] == "MANSON.IA"
    assert {row["location"] for row in result["rows"]} == {"MANSON.IA"}
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    dec = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZCZ26"
    )
    # futures "502-4" = 502.5 cents -> $5.025; basis -28 cents -> -$0.28.
    assert dec["futures_price"] == pytest.approx(5.025)
    assert dec["basis"] == pytest.approx(-0.28)
    assert dec["cash_price"] == pytest.approx(4.72)
    assert dec["futures_month"] == "Dec 2026"
    assert dec["delivery_month"] == "Nov 2026"
    # The second embed's fields list omits delivery_end, but the
    # payload still carries it on every row — pin that here.
    assert all(row["delivery_end"] is not None for row in result["rows"])
    assert dec["delivery_end"] == "11/30/2026"
    notes = " ".join(result["notes"])
    assert "1 login-gated" in notes


def test_fetch_pro_coop_21302b_uses_verified_url() -> None:
    html = _read("cashbids_embed_pro_coop_21302b_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_pro_coop_21302b()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("pro_coop_21302b").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "PRO Coop"
    assert result["location"] == "MANSON.IA"
    assert len(result["rows"]) == 3


def test_hull_coop_sample_parses_groupby_commodity_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("hull_coop")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_hull_coop_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "Hull Coop"
    # 4 cashbids in the payload minus 1 login-gated.
    assert len(result["rows"]) == 3
    assert result["location"] == "Hull"
    # groupby=ccommodity: groups are named Corn / Soybeans, so the row
    # location must come from location_name, not the group name.
    assert {row["location"] for row in result["rows"]} == {"Hull"}
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    dec = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZCZ26"
    )
    # futures "440-0" = 440.0 cents -> $4.40; basis -30 cents -> -$0.30.
    assert dec["futures_price"] == pytest.approx(4.40)
    assert dec["basis"] == pytest.approx(-0.30)
    assert dec["cash_price"] == pytest.approx(4.10)
    assert dec["futures_month"] == "Dec 2026"
    assert dec["delivery_month"] == "Nov 2026"
    notes = " ".join(result["notes"])
    assert "1 login-gated" in notes


def test_fetch_hull_coop_uses_verified_url() -> None:
    html = _read("cashbids_embed_hull_coop_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_hull_coop()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("hull_coop").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "Hull Coop"
    assert result["location"] == "Hull"
    assert len(result["rows"]) == 3


def test_stateline_coop_sample_parses_multi_location_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("stateline_coop")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_stateline_coop_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "StateLine Coop"
    # 5 cashbids in the payload minus 1 inactive.
    assert len(result["rows"]) == 4
    assert {row["location"] for row in result["rows"]} == {
        "Armstrong",
        "Blue Earth",
    }
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    assert result["location"] == "Armstrong"  # first row's location
    dec = next(
        row
        for row in result["rows"]
        if row["location"] == "Armstrong" and row["commodity"] == "Corn"
    )
    # futures "440-0" = $4.40; basis -28 cents -> -$0.28.
    assert dec["futures_price"] == pytest.approx(4.40)
    assert dec["basis"] == pytest.approx(-0.28)
    assert dec["cash_price"] == pytest.approx(4.12)
    notes = " ".join(result["notes"])
    assert "1 inactive" in notes


def test_fetch_stateline_coop_uses_verified_url() -> None:
    html = _read("cashbids_embed_stateline_coop_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_stateline_coop()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("stateline_coop").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "StateLine Coop"
    assert len(result["rows"]) == 4


# ---------------------------------------------------------------------------
# 2026-11-27 — Farmbucks US-buyer sweep: CGB, Key Cooperative,
# Garden City Coop, Farmward Cooperative, Farmers Cooperative
# Dorchester, Mid Iowa Coop. Fixtures are RECORDED LIVE (trimmed copies
# of the live cashbids-js.php responses, 1-2 groups each), so the
# asserted values are the published prices as of 2026-11-27.
# ---------------------------------------------------------------------------


def test_cgb_sample_parses_meekers_landing_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("cgb")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_cgb_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "CGB"
    assert len(result["rows"]) == 14
    assert result["location"] == "CGB - MEEKERS LANDING"
    assert {row["location"] for row in result["rows"]} == {
        "CGB - MEEKERS LANDING"
    }
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    assert sum(1 for row in result["rows"] if row["commodity"] == "Corn") == 7
    assert sum(1 for row in result["rows"] if row["commodity"] == "Soybeans") == 7
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    corn = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZCH27"
    )
    # futures "463-0" = 463.0 cents -> $4.63; basis -32 cents -> -$0.32.
    assert corn["futures_price"] == pytest.approx(4.63)
    assert corn["basis"] == pytest.approx(-0.32)
    assert corn["cash_price"] == pytest.approx(4.31)
    assert corn["cash_price_mt"] == pytest.approx(169.68)
    assert corn["change"] == pytest.approx(0.06)
    assert corn["futures_change"] == pytest.approx(0.065)
    assert corn["futures_month"] == "Mar 2027"
    # Delivery windows start mid-month on this feed (11/16/2026).
    assert corn["delivery_start"] == "11/16/2026"
    assert corn["delivery_end"] == "11/30/2026"
    assert corn["delivery_month"] == "Nov 2026"
    # The feed labels soybeans "Beans" (ZSF27) — mapped to Soybeans.
    soy = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZSF27"
    )
    assert soy["commodity"] == "Soybeans"
    assert soy["futures_price"] == pytest.approx(12.6625)
    assert soy["basis"] == pytest.approx(-0.08)
    assert soy["cash_price"] == pytest.approx(12.59)


def test_fetch_cgb_uses_verified_url() -> None:
    html = _read("cashbids_embed_cgb_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_cgb()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("cgb").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "CGB"
    assert result["location"] == "CGB - MEEKERS LANDING"
    assert len(result["rows"]) == 14


def test_key_coop_sample_parses_barnes_city_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("key_coop")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_key_coop_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "Key Cooperative"
    assert len(result["rows"]) == 14
    assert result["location"] == "Barnes City"
    assert {row["location"] for row in result["rows"]} == {"Barnes City"}
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    assert sum(1 for row in result["rows"] if row["commodity"] == "Corn") == 8
    assert sum(1 for row in result["rows"] if row["commodity"] == "Soybeans") == 6
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    corn = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZCZ26"
    )
    # futures "446-6" = 446.75 cents -> $4.4675; basis -33 cents.
    assert corn["futures_price"] == pytest.approx(4.4675)
    assert corn["basis"] == pytest.approx(-0.33)
    assert corn["cash_price"] == pytest.approx(4.14)
    assert corn["cash_price_mt"] == pytest.approx(162.885987)
    assert corn["change"] == pytest.approx(0.07)
    assert corn["futures_change"] == pytest.approx(0.07)
    assert corn["futures_month"] == "Dec 2026"
    assert corn["delivery_start"] == "11/01/2026"
    assert corn["delivery_end"] == "11/30/2026"
    assert corn["delivery_month"] == "Nov 2026"


def test_fetch_key_coop_uses_verified_url() -> None:
    html = _read("cashbids_embed_key_coop_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_key_coop()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("key_coop").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "Key Cooperative"
    assert result["location"] == "Barnes City"
    assert len(result["rows"]) == 14


def test_garden_city_sample_parses_elevator_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("garden_city")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_garden_city_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "Garden City Coop"
    assert len(result["rows"]) == 7
    assert result["location"] == "Garden City Elevator"
    assert {row["location"] for row in result["rows"]} == {
        "Garden City Elevator"
    }
    assert {row["commodity"] for row in result["rows"]} == {
        "Corn",
        "Milo",
        "Hard Red Wheat",
        "Hard White Wheat",
    }
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    corn = next(
        row for row in result["rows"] if row["commodity"] == "Corn"
    )
    # futures "463-0" = $4.63; basis +5 cents -> +$0.05.
    assert corn["futures_price"] == pytest.approx(4.63)
    assert corn["basis"] == pytest.approx(0.05)
    assert corn["cash_price"] == pytest.approx(4.68)
    assert corn["futures_month"] == "Mar 2027"
    assert corn["delivery_start"] == "09/01/2026"
    assert corn["delivery_end"] == "12/01/2026"
    assert corn["delivery_month"] == "Sep 2026"
    # "Hard Red Wheat" / "Hard White Wheat" are not in COMMODITY_MAP —
    # they are kept exactly as published.
    hrw = next(
        row for row in result["rows"] if row["commodity"] == "Hard Red Wheat"
    )
    assert hrw["futures_symbol"] == "KEH27"
    assert hrw["futures_price"] == pytest.approx(6.36)
    assert hrw["basis"] == pytest.approx(-0.75)
    assert hrw["cash_price"] == pytest.approx(5.61)


def test_fetch_garden_city_uses_verified_url() -> None:
    html = _read("cashbids_embed_garden_city_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_garden_city()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("garden_city").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "Garden City Coop"
    assert result["location"] == "Garden City Elevator"
    assert len(result["rows"]) == 7


def test_farmward_sample_parses_multi_location_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("farmward")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_farmward_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "Farmward Cooperative"
    # Fixture is trimmed to the first 2 of the 10 live location groups
    # (Clements, Comfrey) — 40 of the 200 live rows.
    assert len(result["rows"]) == 40
    assert {row["location"] for row in result["rows"]} == {
        "Farmward Cooperative - Clements",
        "Farmward Cooperative - Comfrey",
    }
    assert result["location"] == "Farmward Cooperative - Clements"
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    assert sum(1 for row in result["rows"] if row["commodity"] == "Corn") == 20
    assert sum(1 for row in result["rows"] if row["commodity"] == "Soybeans") == 20
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    corn = next(
        row
        for row in result["rows"]
        if row["location"] == "Farmward Cooperative - Clements"
        and row["futures_symbol"] == "ZCH27"
    )
    # futures "463-0" = $4.63; basis -75 cents -> -$0.75.
    assert corn["futures_price"] == pytest.approx(4.63)
    assert corn["basis"] == pytest.approx(-0.75)
    assert corn["cash_price"] == pytest.approx(3.88)
    assert corn["cash_price_mt"] == pytest.approx(152.748671)
    assert corn["futures_month"] == "Mar 2027"
    assert corn["delivery_start"] == "10/01/2026"
    assert corn["delivery_end"] == "11/30/2026"
    assert corn["delivery_month"] == "Oct 2026"


def test_fetch_farmward_uses_verified_url() -> None:
    html = _read("cashbids_embed_farmward_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_farmward()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("farmward").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "Farmward Cooperative"
    assert result["location"] == "Farmward Cooperative - Clements"
    assert len(result["rows"]) == 40


def test_dorchester_sample_parses_groupby_commodity_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("dorchester")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_dorchester_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "Farmers Cooperative Dorchester"
    # Fixture is trimmed to the CORN + MILO groups (20 of the 32 live
    # rows; the live BEANS + WHEAT groups are not reproduced here).
    assert len(result["rows"]) == 20
    # groupby=commodity: groups are named CORN / MILO, so the row
    # location must come from location_name, not the group name.
    assert {row["location"] for row in result["rows"]} == {"BEATRICE"}
    assert result["location"] == "BEATRICE"
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Milo"}
    assert sum(1 for row in result["rows"] if row["commodity"] == "Corn") == 10
    assert sum(1 for row in result["rows"] if row["commodity"] == "Milo") == 10
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    corn = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZCH27"
    )
    # futures "463-0" = $4.63; basis -45 cents -> -$0.45.
    assert corn["futures_price"] == pytest.approx(4.63)
    assert corn["basis"] == pytest.approx(-0.45)
    assert corn["cash_price"] == pytest.approx(4.18)
    assert corn["cash_price_mt"] == pytest.approx(164.56)
    assert corn["futures_month"] == "Mar 2027"
    assert corn["delivery_start"] == "11/01/2026"
    assert corn["delivery_end"] == "11/30/2026"
    assert corn["delivery_month"] == "Nov 2026"
    milo = next(
        row for row in result["rows"] if row["commodity"] == "Milo"
    )
    assert milo["basis"] == pytest.approx(-0.65)
    assert milo["cash_price"] == pytest.approx(3.98)


def test_fetch_dorchester_uses_verified_url() -> None:
    html = _read("cashbids_embed_dorchester_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_dorchester()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("dorchester").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "Farmers Cooperative Dorchester"
    assert result["location"] == "BEATRICE"
    assert len(result["rows"]) == 20


def test_mid_iowa_sample_parses_reference_location_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("mid_iowa")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_mid_iowa_sample.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "Mid Iowa Coop"
    # Fixture is trimmed to the first 2 of the 30 live location groups
    # (ADM CEDAR RAPIDS, ADM DSM) — 6 of the 129 live rows.
    assert len(result["rows"]) == 6
    assert {row["location"] for row in result["rows"]} == {
        "ADM CEDAR RAPIDS",
        "ADM DSM",
    }
    assert result["location"] == "ADM CEDAR RAPIDS"  # first row's location
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    assert sum(1 for row in result["rows"] if row["commodity"] == "Corn") == 3
    assert sum(1 for row in result["rows"] if row["commodity"] == "Soybeans") == 3
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    # ADM / Cargill / POET reference locations are recorded exactly as
    # published, not expanded or remapped.
    corn = next(
        row
        for row in result["rows"]
        if row["location"] == "ADM CEDAR RAPIDS" and row["commodity"] == "Corn"
    )
    # futures "446-6" = $4.4675; basis +3 cents -> +$0.03.
    assert corn["futures_price"] == pytest.approx(4.4675)
    assert corn["basis"] == pytest.approx(0.03)
    assert corn["cash_price"] == pytest.approx(4.50)
    assert corn["cash_price_mt"] == pytest.approx(177.06)
    assert corn["futures_month"] == "Dec 2026"
    assert corn["delivery_start"] == "11/01/2026"
    assert corn["delivery_month"] == "Nov 2026"
    soy = next(
        row
        for row in result["rows"]
        if row["location"] == "ADM DSM" and row["commodity"] == "Soybeans"
    )
    # The loader's fields list omits 'name', but the payload still
    # carries it — the commodity still parses.
    assert soy["futures_symbol"] == "ZSF27"
    assert soy["futures_price"] == pytest.approx(12.6625)
    assert soy["basis"] == pytest.approx(-0.30)
    assert soy["cash_price"] == pytest.approx(12.36)


def test_fetch_mid_iowa_uses_verified_url() -> None:
    html = _read("cashbids_embed_mid_iowa_sample.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_mid_iowa()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("mid_iowa").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "Mid Iowa Coop"
    assert result["location"] == "ADM CEDAR RAPIDS"
    assert len(result["rows"]) == 6


# ---------------------------------------------------------------------------
# 2026-11-28 — Evergreen FS (fsgrain, filter=all, 38 locations) and
# Star of the West (sotw, Quincy MI location 9388). Fixtures are
# RECORDED LIVE responses, trimmed (see the fixture headers) — values
# below are live prices as published 2026-11-28, not invented data.
# ---------------------------------------------------------------------------


def test_registry_new_sites_evergreen_and_star_use_verified_live_js_urls():
    evergreen = cashbids_embed_source.get_cashbids_embed_site("evergreen_fs")
    assert evergreen.company == "Evergreen FS"
    assert evergreen.js_url.startswith(
        "https://fsgrain.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=all&location=&commodity=&groupby=location"
    )
    assert evergreen.js_url.endswith("noscript=1&&acCnt=1")
    # dateformat is %m/%d (no year) on this site.
    assert "dateformat=%25m%2F%25d&months=8" in evergreen.js_url
    assert evergreen.default_location is None  # 38 locations, filter=all
    star = cashbids_embed_source.get_cashbids_embed_site("star_of_the_west")
    assert star.company == "Star of the West Milling"
    assert star.js_url.startswith(
        "https://sotw.agricharts.com/inc/cashbids/cashbids-js.php"
        "?filter=location&location=9388&commodity=&groupby=location"
    )
    assert star.js_url.endswith("noscript=1&&acCnt=1")
    assert star.default_location == "Quincy, MI"  # Quincy embed only


def test_evergreen_fs_sample_parses_multi_location_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("evergreen_fs")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_evergreen_fs.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "Evergreen FS"
    # Trimmed fixture: Ashton + Bourbonnais groups, 16 rows each.
    assert len(result["rows"]) == 32
    assert result["location"] == "Ashton"  # first row's location
    assert {row["location"] for row in result["rows"]} == {
        "Ashton",
        "Bourbonnais",
    }
    assert {row["commodity"] for row in result["rows"]} == {"Corn", "Soybeans"}
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    dec = next(
        row
        for row in result["rows"]
        if row["location"] == "Ashton"
        and row["commodity"] == "Corn"
        and row["futures_symbol"] == "ZCZ26"
    )
    # futures "446-6" = 446.75 cents -> $4.4675; basis -30 cents.
    assert dec["futures_price"] == pytest.approx(4.4675)
    assert dec["basis"] == pytest.approx(-0.30)
    assert dec["cash_price"] == pytest.approx(4.1675)
    assert dec["futures_month"] == "Dec 2026"
    assert dec["futures_change"] == pytest.approx(0.07)
    assert dec["change"] == pytest.approx(0.07)
    # dateformat %m/%d (no year): the delivery label is carried verbatim.
    assert dec["delivery_month"] == "11/27"
    assert dec["delivery_start"] == "11/27"
    assert dec["delivery_end"] == "11/30"
    jan = next(
        row
        for row in result["rows"]
        if row["location"] == "Ashton"
        and row["delivery_start"] == "01/01"
    )
    assert jan["delivery_month"] == "01/01"
    assert jan["futures_month"] == "Mar 2027"
    assert jan["futures_price"] == pytest.approx(4.63)
    assert jan["basis"] == pytest.approx(-0.39)


def test_fetch_evergreen_fs_uses_verified_url() -> None:
    html = _read("cashbids_embed_evergreen_fs.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_evergreen_fs()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("evergreen_fs").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "Evergreen FS"
    assert result["location"] == "Ashton"
    assert len(result["rows"]) == 32


def test_star_of_the_west_sample_parses_quincy_red_wheat_rows():
    site = cashbids_embed_source.get_cashbids_embed_site("star_of_the_west")
    result = cashbids_embed_source.parse_cashbids_embed_html(
        _read("cashbids_embed_star_of_the_west.html"), site=site
    )
    assert result["status"] == "ok"
    assert result["company"] == "Star of the West Milling"
    assert len(result["rows"]) == 2
    assert result["location"] == "Quincy, MI"
    assert {row["location"] for row in result["rows"]} == {"Quincy, MI"}
    assert {row["commodity"] for row in result["rows"]} == {"Red Wheat"}
    assert all(row["currency"] == "USD" for row in result["rows"])
    assert all(row["unit"] == "$/bu" for row in result["rows"])
    dec = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZWH27"
    )
    # futures "591-0" = 591.0 cents -> $5.91; basis -35 cents.
    assert dec["futures_price"] == pytest.approx(5.91)
    assert dec["basis"] == pytest.approx(-0.35)
    assert dec["cash_price"] == pytest.approx(5.56)
    assert dec["futures_month"] == "Mar 2027"
    assert dec["delivery_month"] == "Nov 2026"
    assert dec["delivery_start"] == "11/27/2026"
    jul = next(
        row for row in result["rows"] if row["futures_symbol"] == "ZWN27"
    )
    # futures "606-6" = 606.75 cents -> $6.0675.
    assert jul["futures_price"] == pytest.approx(6.0675)
    assert jul["cash_price"] == pytest.approx(5.72)
    assert jul["delivery_month"] == "Jul 2027"


def test_fetch_star_of_the_west_uses_verified_url() -> None:
    html = _read("cashbids_embed_star_of_the_west.html")
    with patch.object(
        cashbids_embed_source,
        "fetch_cashbids_embed_html",
        return_value=html,
    ) as mock_get:
        result = cashbids_embed_source.fetch_star_of_the_west()
    mock_get.assert_called_once_with(
        cashbids_embed_source.get_cashbids_embed_site("star_of_the_west").js_url
    )
    assert result["status"] == "ok"
    assert result["company"] == "Star of the West Milling"
    assert result["location"] == "Quincy, MI"
    assert len(result["rows"]) == 2
