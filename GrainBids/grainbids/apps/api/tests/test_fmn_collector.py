"""Tests for the Farm Market News (AgriCharts) cash-bid collector (Cycle 10).

All parsing tests run against saved synthetic fixtures in
tests/fixtures/ — no live fetching inside pytest. Fixture values are
invented test data, not live prices.

One test (test_fmn_live_html_structure) reads the single saved live
copy at /tmp/fmn/fmn_cash.html when it exists and asserts structure
counts only (tables / rows / delivery points) — no prices. It skips
when the scratch copy is absent.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import fmn_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LIVE_HTML = Path("/tmp/fmn/fmn_cash.html")

# Fixture as-of date: the page publishes no trade date, so rows are
# dated with the fetch date.
AS_OF = "2026-11-19"


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
# Fetch plumbing (mocked — no live HTTP in tests)
# ---------------------------------------------------------------------------


def test_fmn_fetch_cash_uses_verified_url() -> None:
    html = _read("fmn_sample.html")
    with patch.object(
        fmn_source, "fetch_fmn_html", return_value=html
    ) as mock_get:
        result = fmn_source.fetch_fmn_cash(as_of=AS_OF)
    mock_get.assert_called_once_with(fmn_source.FMN_URL)
    assert result["status"] == "ok"
    assert len(result["rows"]) == 12


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
