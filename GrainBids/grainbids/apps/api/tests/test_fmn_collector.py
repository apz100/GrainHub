"""Tests for the Farm Market News (AgriCharts) cash-bid collector (Cycle 10,
quotes feed in Cycle 11).

All parsing tests run against saved synthetic fixtures in
tests/fixtures/ — no live fetching inside pytest. Fixture values are
invented test data, not live prices.

One test (test_fmn_live_html_structure) reads the single saved live
copy at /tmp/fmn/fmn_cash.html when it exists and asserts structure
counts only (tables / rows / delivery points) — no prices. The live
quotes-feed test reads /tmp/fmn/jsquote.txt the same way (counts
only). Both skip when the scratch copies are absent.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import fmn_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIVE_HTML = Path("/tmp/fmn/fmn_cash.html")
LIVE_FEED = Path("/tmp/fmn/jsquote.txt")

# Fixture as-of date: the page publishes no trade date, so rows are
# dated with the fetch date.
AS_OF = "2026-11-19"

# Synthetic quotes mapping for the fixture (invented values only —
# not live prices). Deliberately omits ZWZ26, ZCZ27 and ZSX27 so the
# missing-quote rows can be checked: they must stay None, not invented.
QUOTES = {
    "ZCZ26": {"rawLast": "500.0", "change": "2.5", "exchange": "CBOT"},
    "ZSF27": {"rawLast": "1200.0", "change": "-1.25", "exchange": "CBOT"},
    "MWZ26": {"rawLast": "6.50", "change": "0.01", "exchange": "MIAX"},
    "ZWN27": {"rawLast": "600.0", "change": "1.5", "exchange": "CBOT"},
}

# Synthetic jsquote feed text (same JS-literal shape as the live feed:
# unquoted keys, single-quoted values, trailing commas).
FEED_TEXT = """var quotes = {
\t'ZCZ26': {
\t\tsymbol: 'ZCZ26',
\t\tname: 'Corn',
\t\texchange: 'CBOT',
\t\trawLast: '500.0',
\t\tchange: '2.5',
\t\tmonth: 'December 2026',
\t},
\t'MWZ26': {
\t\tsymbol: 'MWZ26',
\t\tname: 'Wheat',
\t\texchange: 'MIAX',
\t\trawLast: '6.50',
\t\tchange: '0.01',
\t\tmonth: 'December 2026',
\t},
};
"""


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(name: str = "fmn_sample.html") -> dict:
    return fmn_source.parse_fmn_html(_read(name), as_of=AS_OF)


# ---------------------------------------------------------------------------
# Normal row parse
# ---------------------------------------------------------------------------


def test_fmn_sample_parses_rows_with_source_and_date() -> None:
    result = _parse()
    assert result["status"] == "ok"
    assert result["company"] == "Farm Market News"
    assert result["location"] == "Alliston"
    rows = result["rows"]
    # 12 data rows: the empty Sunderland wheat table contributes none,
    # and the writeBidRow function definition up top contributes none.
    assert len(rows) == 12
    for row in rows:
        assert row["source"] == "fmn"
        assert row["date"] == AS_OF
        assert row["currency"] == "CAD"
        assert row["company"] == "Farm Market News"


def test_fmn_default_as_of_is_today_toronto() -> None:
    result = fmn_source.parse_fmn_html(_read("fmn_sample.html"))
    expected = datetime.now(ZoneInfo("America/Toronto")).date().isoformat()
    assert result["rows"][0]["date"] == expected


def test_fmn_normal_corn_row_fields() -> None:
    rows = _parse()["rows"]
    corn = next(
        r
        for r in rows
        if r["location"] == "Alliston"
        and r["commodity"] == "Corn"
        and r["delivery_month"] == "Nov 2026"
    )
    assert corn["name"] == "Corn"
    assert corn["delivery_month"] == "Nov 2026"
    assert corn["delivery_end"] == "Nov 2026"
    # Basis as published (cents scale), kept verbatim.
    assert corn["basis"] == 100
    # Futures price / change / cash price need the external quotes
    # feed, which is not in the static HTML — never invented.
    assert corn["futures_price"] is None
    assert corn["change"] is None
    assert corn["cash_price"] is None
    assert corn["cash_price_mt"] is None
    assert corn["last_trade"] is None
    # Futures month decoded from the contract symbol; symbol kept.
    assert corn["futures_symbol"] == "ZCZ26"
    assert corn["futures_month"] == "Dec 2026"
    # Settlement is the page's literal fallback on every row.
    assert corn["settlement"] == "0-0"
    assert corn["unit"] == "$/bu"
    assert "quotes feed" in corn["note"]


def test_fmn_new_crop_soy_row_fields() -> None:
    rows = _parse()["rows"]
    soy = next(
        r
        for r in rows
        if r["location"] == "Alliston"
        and r["commodity"] == "Soybeans"
        and r["delivery_month"] == "Oct 2027"
    )
    assert soy["name"] == "Soybeans"
    assert soy["delivery_month"] == "Oct 2027"
    assert soy["delivery_end"] == "Nov 2027"
    assert soy["basis"] == 250
    assert soy["futures_symbol"] == "ZSF27"
    assert soy["futures_month"] == "Jan 2027"
    assert soy["futures_price"] is None
    assert soy["cash_price"] is None


def test_fmn_regional_average_and_fob_locations_kept_verbatim() -> None:
    rows = _parse()["rows"]
    avg = next(r for r in rows if r["location"] == "Chatham-Kent Avg")
    assert avg["commodity"] == "Corn"
    assert avg["delivery_month"] == "Nov 2026"
    quebec = next(r for r in rows if r["location"] == "Quebec FOB")
    assert quebec["commodity"] == "Corn"
    assert quebec["delivery_month"] == "Nov 2026"
    assert quebec["delivery_end"] == "Dec 2026"


# ---------------------------------------------------------------------------
# Wheat-class rows
# ---------------------------------------------------------------------------


def test_fmn_wheat_class_rows() -> None:
    rows = _parse()["rows"]
    hrw_new = next(
        r for r in rows if r["name"] == "HRW New Crop Wheat"
    )
    assert hrw_new["commodity"] == "Wheat — HRW"
    assert hrw_new["name"] == "HRW New Crop Wheat"
    assert hrw_new["delivery_month"] == "Jul 2027"
    assert hrw_new["delivery_end"] == "Aug 2027"
    assert hrw_new["futures_symbol"] == "ZWN27"
    assert hrw_new["futures_month"] == "Jul 2027"
    assert hrw_new["basis"] == 110

    hrw_old = next(
        r for r in rows if r["name"] == "HRW Old Crop Wheat"
    )
    assert hrw_old["commodity"] == "Wheat — HRW"
    assert hrw_old["delivery_month"] == "Nov 2026"
    assert hrw_old["basis"] == -20
    assert hrw_old["futures_symbol"] == "ZWZ26"
    assert hrw_old["futures_month"] == "Dec 2026"

    srw_new = next(
        r for r in rows if r["name"] == "SRW New Crop Wheat"
    )
    assert srw_new["commodity"] == "Wheat — SRW"
    assert srw_new["basis"] == 130

    # HRS rows reference Minneapolis symbols (MW*).
    hrs_old = next(
        r for r in rows if r["name"] == "HRS Old Crop Wheat"
    )
    assert hrs_old["commodity"] == "Wheat — HRS"
    assert hrs_old["futures_symbol"] == "MWZ26"
    assert hrs_old["futures_month"] == "Dec 2026"
    assert hrs_old["basis"] == 95


# ---------------------------------------------------------------------------
# Barley / oats manual (cash-only) rows
# ---------------------------------------------------------------------------


def test_fmn_barley_oats_manual_rows() -> None:
    rows = _parse()["rows"]
    barley = next(
        r
        for r in rows
        if r["location"] == "Hensall HDC" and r["commodity"] == "Barley"
    )
    assert barley["name"] == "Barley"
    assert barley["delivery_month"] == "Nov 2026"
    # Cash-only row: the page's published manual value (basis arg /
    # 100), per tonne. No futures / basis / change is published.
    assert barley["cash_price"] == 280.0
    assert barley["cash_price_mt"] == 280.0
    assert barley["unit"] == "$/t"
    assert barley["basis"] is None
    assert barley["futures_price"] is None
    assert barley["futures_month"] is None
    assert barley["futures_symbol"] is None
    assert barley["change"] is None
    assert barley["settlement"] == "0-0"
    assert "manual" in barley["note"].lower()

    oats = next(
        r
        for r in rows
        if r["location"] == "Hensall HDC" and r["commodity"] == "Oats"
    )
    assert oats["cash_price"] == 310.0
    assert oats["cash_price_mt"] == 310.0
    assert oats["unit"] == "$/t"
    assert oats["basis"] is None


@pytest.mark.parametrize(
    "basis,rounding,expected",
    [
        (28000, 0.5, 280.0),
        (31000, 0.5, 310.0),
        (None, 0.5, None),
    ],
)
def test_fmn_manual_cash_rule(basis, rounding, expected) -> None:
    assert fmn_source.manual_cash_price(basis, rounding) == expected


# ---------------------------------------------------------------------------
# Delivery month labels
# ---------------------------------------------------------------------------


def test_fmn_delivery_month_labels_kept_verbatim() -> None:
    rows = _parse()["rows"]
    months = {r["delivery_month"] for r in rows}
    assert months == {"Nov 2026", "Jul 2027", "Oct 2027"}
    ends = {r["delivery_end"] for r in rows}
    assert ends == {"Nov 2026", "Aug 2027", "Nov 2027", "Dec 2026"}
    # Every row carries a delivery window.
    assert all(r["delivery_month"] and r["delivery_end"] for r in rows)


# ---------------------------------------------------------------------------
# Futures symbol decoding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "symbol,expected",
    [
        ("ZCZ26", "Dec 2026"),
        ("ZCZ27", "Dec 2027"),
        ("ZSF27", "Jan 2027"),
        ("ZSX27", "Nov 2027"),
        ("ZWN27", "Jul 2027"),
        ("ZWZ26", "Dec 2026"),
        ("MWU27", "Sep 2027"),
        ("MWZ26", "Dec 2026"),
        ("ZCH27", "Mar 2027"),
        ("ZSH27", "Mar 2027"),
        ("", None),
        (None, None),
        ("NOTASYMBOL", None),
    ],
)
def test_fmn_futures_month_from_symbol(symbol, expected) -> None:
    assert fmn_source.futures_month_from_symbol(symbol) == expected


# ---------------------------------------------------------------------------
# Empty / missing table handling
# ---------------------------------------------------------------------------


def test_fmn_empty_table_contributes_no_rows() -> None:
    result = _parse()
    assert result["status"] == "ok"
    assert not any(r["location"] == "Sunderland" for r in result["rows"])


def test_fmn_no_tables_is_unsupported() -> None:
    result = _parse("fmn_no_tables.html")
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_fmn_tables_but_no_rows_is_empty() -> None:
    result = _parse("fmn_empty_tables.html")
    assert result["status"] == "empty"
    assert result["rows"] == []


def test_fmn_blank_html_is_unsupported() -> None:
    result = fmn_source.parse_fmn_html(
        "<html><body><p>No tables here.</p></body></html>", as_of=AS_OF
    )
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_fmn_function_definition_produces_no_rows() -> None:
    # The fixture opens with the page's writeBidRow function
    # definition (bare-identifier arguments). It must not parse.
    rows = _parse()["rows"]
    assert not any(r["name"] == "name" for r in rows)
    assert all(r["name"] for r in rows)


# ---------------------------------------------------------------------------
# Quotes feed (Cycle 11)
# ---------------------------------------------------------------------------


def _parse_with_quotes(name: str = "fmn_sample.html") -> dict:
    return fmn_source.parse_fmn_html(
        _read(name), as_of=AS_OF, quotes=QUOTES
    )


def test_fmn_quotes_fill_corn_row() -> None:
    rows = _parse_with_quotes()["rows"]
    corn = next(
        r
        for r in rows
        if r["location"] == "Alliston"
        and r["commodity"] == "Corn"
        and r["delivery_month"] == "Nov 2026"
    )
    # CBOT quote in cents: rawLast 500.0 -> $5.00; change 2.5c -> $0.025.
    assert corn["futures_price"] == pytest.approx(5.00)
    assert corn["change"] == pytest.approx(0.025)
    # Cash rule: (500 + 100 basis) cents, whole-cent rounding -> $6.00.
    assert corn["cash_price"] == pytest.approx(6.00)
    assert corn["cash_price_mt"] is None
    assert corn["futures_month"] == "Dec 2026"
    assert "quotes feed" in corn["note"]


def test_fmn_quotes_fill_other_locations_same_symbol() -> None:
    rows = _parse_with_quotes()["rows"]
    chatham = next(r for r in rows if r["location"] == "Chatham-Kent Avg")
    assert chatham["futures_price"] == pytest.approx(5.00)
    # Basis 105: (500 + 105) cents -> $6.05.
    assert chatham["cash_price"] == pytest.approx(6.05)
    quebec = next(r for r in rows if r["location"] == "Quebec FOB")
    # Basis 115: (500 + 115) cents -> $6.15.
    assert quebec["cash_price"] == pytest.approx(6.15)


def test_fmn_quotes_fill_soy_row() -> None:
    rows = _parse_with_quotes()["rows"]
    soy = next(
        r
        for r in rows
        if r["location"] == "Alliston"
        and r["commodity"] == "Soybeans"
        and r["delivery_month"] == "Oct 2027"
    )
    assert soy["futures_price"] == pytest.approx(12.00)
    assert soy["change"] == pytest.approx(-0.0125)
    # (1200 + 250) cents -> $14.50.
    assert soy["cash_price"] == pytest.approx(14.50)


def test_fmn_quotes_fill_mw_row_in_dollars() -> None:
    rows = _parse_with_quotes()["rows"]
    hrs = next(r for r in rows if r["name"] == "HRS Old Crop Wheat")
    # Minneapolis quote arrives in dollars, not cents: rawLast as-is.
    assert hrs["futures_price"] == pytest.approx(6.50)
    assert hrs["change"] == pytest.approx(0.01)
    # MW cash rule: rawLast + basis/100, to 2dp -> 6.50 + 0.95 = $7.45.
    assert hrs["cash_price"] == pytest.approx(7.45)
    assert hrs["futures_month"] == "Dec 2026"


def test_fmn_quotes_fill_wheat_row() -> None:
    rows = _parse_with_quotes()["rows"]
    hrw_new = next(r for r in rows if r["name"] == "HRW New Crop Wheat")
    assert hrw_new["futures_price"] == pytest.approx(6.00)
    assert hrw_new["change"] == pytest.approx(0.015)
    # (600 + 110) cents -> $7.10.
    assert hrw_new["cash_price"] == pytest.approx(7.10)


def test_fmn_missing_quote_rows_stay_none() -> None:
    result = _parse_with_quotes()
    rows = result["rows"]
    # ZWZ26, ZCZ27 and ZSX27 are not in QUOTES — never invented.
    for name in ("HRW Old Crop Wheat",):
        row = next(r for r in rows if r["name"] == name)
        assert row["futures_price"] is None
        assert row["change"] is None
        assert row["cash_price"] is None
        assert "no quote for ZWZ26" in row["note"]
    new_crop_corn = next(
        r
        for r in rows
        if r["commodity"] == "Corn" and r["delivery_month"] == "Oct 2027"
    )
    assert new_crop_corn["futures_symbol"] == "ZCZ27"
    assert new_crop_corn["futures_price"] is None
    assert new_crop_corn["cash_price"] is None
    assert "no quote for ZCZ27" in new_crop_corn["note"]
    soy_nov = next(
        r
        for r in rows
        if r["commodity"] == "Soybeans" and r["delivery_month"] == "Nov 2026"
    )
    assert soy_nov["futures_symbol"] == "ZSX27"
    assert soy_nov["futures_price"] is None
    assert "no quote for ZSX27" in soy_nov["note"]
    assert result["notes"][-2] == (
        "quotes feed applied: 7 of 10 futures-linked rows filled; "
        "3 had no quote in the feed"
    )


def test_fmn_manual_rows_unchanged_with_quotes() -> None:
    rows = _parse_with_quotes()["rows"]
    barley = next(
        r
        for r in rows
        if r["location"] == "Hensall HDC" and r["commodity"] == "Barley"
    )
    assert barley["cash_price"] == 280.0
    assert barley["cash_price_mt"] == 280.0
    assert barley["unit"] == "$/t"
    assert barley["basis"] is None
    assert barley["futures_price"] is None
    assert barley["futures_symbol"] is None
    assert barley["change"] is None
    assert "manual" in barley["note"].lower()
    oats = next(
        r
        for r in rows
        if r["location"] == "Hensall HDC" and r["commodity"] == "Oats"
    )
    assert oats["cash_price"] == 310.0
    assert oats["futures_price"] is None


@pytest.mark.parametrize(
    "raw_last,basis,rounding,symbol,exchange,expected",
    [
        # CBOT cents: (raw + basis) rounded to whole cents, / 100.
        ("500.25", -25, 0.5, "ZCZ26", "CBOT", 4.75),
        ("500.75", -25, 0.5, "ZCZ26", "CBOT", 4.76),
        ("434.75", -35, 0.5, "ZCZ26", "CBOT", 4.00),
        ("500.0", 100, 0.5, "ZCZ26", "CBOT", 6.00),
        # No rounding step when rounding is None: straight / 100, to 2dp.
        ("500.25", -25, None, "ZCZ26", "CBOT", 4.75),
        # MW dollars: rawLast + basis/100, to 2dp.
        ("6.50", 95, 0.5, "MWZ26", "MIAX", 7.45),
        ("6.50", -20, 0.5, "MWZ26", "MIAX", 6.30),
        # WCE: rawLast in dollars -> price is rawLast * 100 cents.
        ("4.50", -25, 0.5, "ZCZ26", "WCE", 4.25),
        # Missing quote or basis -> None, never invented.
        (None, -25, 0.5, "ZCZ26", "CBOT", None),
        ("n/a", -25, 0.5, "ZCZ26", "CBOT", None),
        ("500.0", None, 0.5, "ZCZ26", "CBOT", None),
    ],
)
def test_fmn_quote_cash_price_rule(
    raw_last, basis, rounding, symbol, exchange, expected
) -> None:
    assert (
        fmn_source.quote_cash_price(
            raw_last, basis, rounding, symbol=symbol, exchange=exchange
        )
        == expected
    )


@pytest.mark.parametrize(
    "value,symbol,exchange,expected",
    [
        ("500.0", "ZCZ26", "CBOT", 5.00),
        ("2.5", "ZCZ26", "CBOT", 0.025),
        ("-1.25", "ZSF27", "CBOT", -0.0125),
        ("6.50", "MWZ26", "MIAX", 6.50),
        ("0.01", "MWZ26", "MIAX", 0.01),
        ("4.50", "ZCZ26", "WCE", 4.50),
        ("n/a", "ZCZ26", "CBOT", None),
        (None, "ZCZ26", "CBOT", None),
        (600.0, "ZWN27", "CBOT", 6.00),
    ],
)
def test_fmn_quote_to_dollars(value, symbol, exchange, expected) -> None:
    assert (
        fmn_source.quote_to_dollars(value, symbol=symbol, exchange=exchange)
        == expected
    )


def test_fmn_parse_quotes_feed_synthetic() -> None:
    quotes = fmn_source.parse_quotes_feed(FEED_TEXT)
    assert sorted(quotes) == ["MWZ26", "ZCZ26"]
    assert quotes["ZCZ26"]["rawLast"] == "500.0"
    # The field regex must not read "change" out of "exchange".
    assert quotes["ZCZ26"]["change"] == "2.5"
    assert quotes["ZCZ26"]["exchange"] == "CBOT"
    assert quotes["MWZ26"]["rawLast"] == "6.50"
    assert quotes["MWZ26"]["exchange"] == "MIAX"
    assert quotes["MWZ26"]["month"] == "December 2026"


def test_fmn_parse_quotes_feed_invalid_is_empty() -> None:
    assert fmn_source.parse_quotes_feed("") == {}
    assert fmn_source.parse_quotes_feed("<html>not a feed</html>") == {}
    assert fmn_source.parse_quotes_feed("var quotes = {};") == {}
    assert fmn_source.parse_quotes_feed("var quotes = {") == {}


# ---------------------------------------------------------------------------
# Fetch plumbing (mocked — no live HTTP in tests)
# ---------------------------------------------------------------------------


def test_fmn_fetch_cash_uses_verified_urls() -> None:
    html = _read("fmn_sample.html")
    with (
        patch.object(
            fmn_source, "fetch_fmn_html", return_value=html
        ) as mock_page,
        patch.object(
            fmn_source, "fetch_fmn_quotes", return_value=QUOTES
        ) as mock_feed,
    ):
        result = fmn_source.fetch_fmn_cash(as_of=AS_OF)
    mock_page.assert_called_once_with(fmn_source.FMN_URL)
    mock_feed.assert_called_once_with(fmn_source.FMN_QUOTES_URL)
    assert result["status"] == "ok"
    assert len(result["rows"]) == 12
    corn = next(
        r
        for r in result["rows"]
        if r["location"] == "Alliston"
        and r["commodity"] == "Corn"
        and r["delivery_month"] == "Nov 2026"
    )
    assert corn["futures_price"] == pytest.approx(5.00)
    assert corn["cash_price"] == pytest.approx(6.00)


def test_fmn_fetch_cash_feed_failure_falls_back_to_page_only() -> None:
    html = _read("fmn_sample.html")
    with (
        patch.object(fmn_source, "fetch_fmn_html", return_value=html),
        patch.object(
            fmn_source,
            "fetch_fmn_quotes",
            side_effect=requests.RequestException("boom"),
        ),
    ):
        result = fmn_source.fetch_fmn_cash(as_of=AS_OF)
    assert result["status"] == "ok"
    assert len(result["rows"]) == 12
    assert all(
        r["futures_price"] is None for r in result["rows"] if r["futures_symbol"]
    )
    assert "quotes feed fetch failed" in " ".join(result["notes"])


def test_fmn_fetch_cash_empty_feed_falls_back_to_page_only() -> None:
    html = _read("fmn_sample.html")
    with (
        patch.object(fmn_source, "fetch_fmn_html", return_value=html),
        patch.object(fmn_source, "fetch_fmn_quotes", return_value={}),
    ):
        result = fmn_source.fetch_fmn_cash(as_of=AS_OF)
    assert result["status"] == "ok"
    assert len(result["rows"]) == 12
    assert all(
        r["cash_price"] is None for r in result["rows"] if r["futures_symbol"]
    )
    assert "quotes feed returned no symbols" in " ".join(result["notes"])


# ---------------------------------------------------------------------------
# Live HTML structure sanity check (counts only, no prices)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not LIVE_HTML.exists(), reason="saved live copy /tmp/fmn/fmn_cash.html absent"
)
def test_fmn_live_html_structure() -> None:
    """Structure-only check against the one saved live fetch.

    Verified 2026-11-19: 204 bid tables, 453 rows, 87 delivery
    points in the default all-locations view. Counts only — no
    prices are asserted or copied anywhere.
    """
    html = LIVE_HTML.read_text(encoding="utf-8")
    result = fmn_source.parse_fmn_html(html, as_of="2026-11-19")
    assert result["status"] == "ok"
    assert len(result["rows"]) == 453
    assert len({r["location"] for r in result["rows"]}) == 87
    assert result["notes"][-1] == (
        "parsed 453 rows from 204 bid tables (87 delivery points)"
    )


@pytest.mark.skipif(
    not LIVE_HTML.exists() or not LIVE_FEED.exists(),
    reason="saved live copies /tmp/fmn/fmn_cash.html / /tmp/fmn/jsquote.txt absent",
)
def test_fmn_live_html_with_live_feed_fills_all_futures_rows() -> None:
    """Counts only — no prices asserted or copied anywhere.

    Saved live page (2026-11-19) + saved live jsquote feed
    (verified 2026-11-19, Cycle 11): 453 rows, 449 futures-linked
    rows all filled, 4 manual barley/oats rows unchanged.
    """
    quotes = fmn_source.parse_quotes_feed(
        LIVE_FEED.read_text(encoding="utf-8")
    )
    assert len(quotes) == 10
    result = fmn_source.parse_fmn_html(
        LIVE_HTML.read_text(encoding="utf-8"),
        as_of="2026-11-19",
        quotes=quotes,
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 453
    linked = [r for r in result["rows"] if r["futures_symbol"]]
    manual = [r for r in result["rows"] if r["futures_symbol"] is None]
    assert len(linked) == 449
    assert len(manual) == 4
    assert all(r["futures_price"] is not None for r in linked)
    assert all(r["cash_price"] is not None for r in linked)
    assert all(r["change"] is not None for r in linked)
    assert all(r["cash_price"] is not None for r in manual)
    assert all(r["futures_price"] is None for r in manual)
    assert result["notes"][-2] == (
        "quotes feed applied: 449 of 449 futures-linked rows filled; "
        "0 had no quote in the feed"
    )
