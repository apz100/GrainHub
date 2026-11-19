"""Tests for the wpDataTables cash-bid collector (Cycle 9).

All parsing tests run against saved synthetic fixtures in
tests/fixtures/ — no live fetching inside pytest. Fixture values are
invented test data, not live prices.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import wpdatatables_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(name: str = "wpdatatables_five_star_sample.html") -> dict:
    return wpdatatables_source.parse_wpdatatables_html(
        _read(name),
        site=wpdatatables_source.get_wpdatatables_site("five_star_coop"),
    )


# ---------------------------------------------------------------------------
# Normal row parse
# ---------------------------------------------------------------------------


def test_wpdatatables_sample_parses_rows_with_source_and_date() -> None:
    result = _parse()
    assert result["status"] == "ok"
    assert result["company"] == "Five Star Coop"
    assert result["location"] == "New Hampton"
    rows = result["rows"]
    # 7 data rows kept: all-dash row and repeated header row skipped.
    assert len(rows) == 7
    for row in rows:
        assert row["source"] == "five_star_coop"
        assert row["date"] == "2026-11-18"
        assert row["trade_datetime"] == "Nov 18, 2026, 1:15 PM CST"
        assert row["currency"] == "USD"
        assert row["unit"] == "$/bu"
        assert row["company"] == "Five Star Coop"


def test_wpdatatables_normal_row_fields() -> None:
    rows = _parse()["rows"]
    corn = next(
        r
        for r in rows
        if r["location"] == "New Hampton" and r["commodity"] == "Corn"
    )
    assert corn["delivery_month"] == "Nov 2026"
    assert corn["delivery_raw"] == "Nov 26"
    assert corn["cash_price"] == 4.10
    assert corn["basis"] == -0.40
    assert corn["change"] == -9.50
    # No futures published alongside the bids on this page.
    assert corn["futures_price"] is None
    assert corn["futures_month"] is None
    assert corn["last_trade"] is None
    assert corn["cash_price_mt"] is None
    assert corn["note"] == ""


def test_wpdatatables_third_party_location_kept_verbatim() -> None:
    rows = _parse()["rows"]
    agp = next(r for r in rows if r["location"] == "AGP Mason City")
    assert agp["commodity"] == "Soybeans"
    assert agp["cash_price"] == 11.20
    assert agp["delivery_month"] == "Jan 2027"


def test_wpdatatables_empty_bid_row_kept_with_note() -> None:
    rows = _parse()["rows"]
    thin = next(
        r
        for r in rows
        if r["location"] == "Ventura" and r["delivery_raw"] == "Mar 27"
    )
    assert thin["cash_price"] is None
    assert thin["basis"] is None
    assert thin["change"] == -11.00
    assert "Missing" in thin["note"]


# ---------------------------------------------------------------------------
# Fractional / decimal money handling
# ---------------------------------------------------------------------------


def test_wpdatatables_fractional_change_converts_to_decimal() -> None:
    rows = _parse()["rows"]
    frac = next(
        r
        for r in rows
        if r["location"] == "Ventura" and r["delivery_raw"] == "Feb 27"
    )
    # "-9-2" = -9 2/8 in the published unit.
    assert frac["change"] == -9.25
    # Decimal bid/basis on the same row parse normally.
    assert frac["cash_price"] == 4.15
    assert frac["basis"] == -0.38


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("4.10", 4.10),
        ("-0.40", -0.40),
        ("4", 4.0),
        ("$11.28", 11.28),
        ("433-2", 433.25),
        ("-2-2", -2.25),
        ("+0-6", 0.75),
        ("", None),
        ("-", None),
        ("—", None),
        (None, None),
    ],
)
def test_wpdatatables_money_parsing(raw: str | None, expected: float | None) -> None:
    assert wpdatatables_source._money(raw) == expected


# ---------------------------------------------------------------------------
# Inconsistent delivery labels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Every label observed live on the Five Star page, 2026-11-19.
        ("Nov 26", "Nov 2026"),
        ("Nov26", "Nov 2026"),
        ("Dec26", "Dec 2026"),
        ("Dec27", "Dec 2027"),
        ("Dec 27", "Dec 2027"),
        ("Jan27", "Jan 2027"),
        ("Jan 27", "Jan 2027"),
        ("Feb 27", "Feb 2027"),
        ("Mar 27", "Mar 2027"),
        ("Apr 27", "Apr 2027"),
        ("April 27", "Apr 2027"),
        ("May 27", "May 2027"),
        ("June 27", "Jun 2027"),
        ("July 27", "Jul 2027"),
        ("Oct 27.", "Oct 2027"),
        # Already canonical, and unknown labels, pass through verbatim.
        ("Nov 2026", "Nov 2026"),
        ("Spot", "Spot"),
        ("", None),
        (None, None),
    ],
)
def test_wpdatatables_delivery_label_normalisation(
    raw: str | None, expected: str | None
) -> None:
    assert wpdatatables_source.normalize_delivery_label(raw) == expected


def test_wpdatatables_fixture_delivery_labels_normalised() -> None:
    rows = _parse()["rows"]
    by_raw = {r["delivery_raw"]: r["delivery_month"] for r in rows}
    assert by_raw["Dec26"] == "Dec 2026"
    assert by_raw["Jan27"] == "Jan 2027"
    assert by_raw["April 27"] == "Apr 2027"
    assert by_raw["Oct 27."] == "Oct 2027"


def test_wpdatatables_unknown_delivery_label_kept_and_flagged() -> None:
    html = _read("wpdatatables_five_star_sample.html").replace(
        "Nov 26", "Spot", 1
    )
    result = wpdatatables_source.parse_wpdatatables_html(
        html,
        site=wpdatatables_source.get_wpdatatables_site("five_star_coop"),
    )
    assert result["status"] == "ok"
    spot = next(r for r in result["rows"] if r["delivery_raw"] == "Spot")
    assert spot["delivery_month"] == "Spot"
    assert any("Spot" in note for note in result["notes"])


# ---------------------------------------------------------------------------
# Futures tables must never be parsed as bids
# ---------------------------------------------------------------------------


def test_wpdatatables_futures_tables_skipped() -> None:
    result = _parse()
    rows = result["rows"]
    # The DTN WHEAT row in table_2 must not appear as a bid row.
    assert not any(r["commodity"] in ("WHEAT", "Wheat") for r in rows)
    assert not any("WHEAT" in (r.get("delivery_raw") or "") for r in rows)
    assert {r["commodity"] for r in rows} == {"Corn", "Soybeans"}


def test_wpdatatables_no_bid_table_is_unsupported() -> None:
    result = _parse("wpdatatables_no_table.html")
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_wpdatatables_empty_bid_table_is_empty() -> None:
    result = _parse("wpdatatables_empty_table.html")
    assert result["status"] == "empty"
    assert result["rows"] == []


def test_wpdatatables_blank_html_is_unsupported() -> None:
    result = wpdatatables_source.parse_wpdatatables_html(
        "<html><body><p>No tables here.</p></body></html>",
        site=wpdatatables_source.get_wpdatatables_site("five_star_coop"),
    )
    assert result["status"] == "unsupported"
    assert result["rows"] == []


# ---------------------------------------------------------------------------
# Fetch plumbing (mocked — no live HTTP in tests)
# ---------------------------------------------------------------------------


def test_wpdatatables_fetch_five_star_uses_verified_site() -> None:
    html = _read("wpdatatables_five_star_sample.html")
    with patch.object(
        wpdatatables_source, "fetch_wpdatatables_html", return_value=html
    ) as mock_get:
        result = wpdatatables_source.fetch_five_star_coop()
    mock_get.assert_called_once_with(
        wpdatatables_source.FIVE_STAR_URL
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 7


def test_wpdatatables_unknown_site_key_raises() -> None:
    with pytest.raises(KeyError):
        wpdatatables_source.get_wpdatatables_site("not_a_site")
