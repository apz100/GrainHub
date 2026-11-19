"""Tests for the two static-HTML Bushel shapes found by the Cycle 6 DTN sweep.

Ace Ethanol and Alliance Grain both serve a Bushel ``.cbmod`` widget in
static HTML (verified live 2026-11-19, one polite GET each). No new parser
was needed: the generic ``bushel_source.parse_bushel_html`` already handles
both shapes (7-column widget; Ace uses full month-year delivery labels,
Alliance uses compact "Nov26" labels and a town/site location h2). These
tests lock that in with synthetic fixtures — no live fetching inside
pytest, fixture values are invented test data, not live prices.

Neither site has a ``BUSHEL_SITES`` registry entry yet (coordinator
wiring); the tests use the ad-hoc ``company=`` / ``currency=`` path.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import bushel_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_bushel_ace_shape_parses_corn_month_year_labels() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_ace_sample.html"), company="Ace Ethanol", currency="USD"
    )
    assert result["status"] == "ok"
    assert result["company"] == "Ace Ethanol"
    assert result["location"] == "Ace Ethanol LLC"
    rows = result["rows"]
    assert len(rows) == 3
    assert {r["commodity"] for r in rows} == {"Corn"}
    first = next(r for r in rows if r["delivery_month"] == "Nov 2026")
    assert first["cash_price"] == 4.10
    assert first["basis"] == -0.30
    assert first["futures_price"] == 4.40
    assert first["change"] == -0.05
    assert first["futures_month"] == "Dec 26 Corn"
    assert first["last_trade"] == "10:00 AM"
    assert first["currency"] == "USD"
    assert first["unit"] == "$/bu"
    assert first["cash_price_mt"] is None
    assert first["note"] == ""
    assert any("Cash bids for" in n for n in result["notes"])


def test_bushel_alliance_shape_parses_two_commodities_compact_labels() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_alliance_sample.html"),
        company="Alliance Grain",
        currency="USD",
    )
    assert result["status"] == "ok"
    assert result["company"] == "Alliance Grain"
    assert result["location"] == "Gibson City - West"
    rows = result["rows"]
    assert len(rows) == 4
    assert {r["commodity"] for r in rows} == {"Corn", "Soybeans"}
    assert all(r["location"] == "Gibson City - West" for r in rows)
    corn = next(
        r
        for r in rows
        if r["commodity"] == "Corn" and r["delivery_month"] == "Nov26"
    )
    assert corn["cash_price"] == 4.05
    assert corn["basis"] == -0.35
    assert corn["futures_price"] == 4.40
    soy = next(
        r
        for r in rows
        if r["commodity"] == "Soybeans" and r["delivery_month"] == "Jan27"
    )
    assert soy["cash_price"] == 11.30
    assert soy["basis"] == -0.65
    assert soy["futures_price"] == 11.95
    assert soy["change"] == 0.03
    assert soy["currency"] == "USD"
    assert soy["unit"] == "$/bu"


def test_alliance_grain_registry_entry_updated_cycle34() -> None:
    """Cycle 34: the live page no longer serves Gibson City — it now
    serves Anchor/Cropsey/Colfax (same URL, still 10 rows). The
    registry default_location was updated to match; the fixture test
    above still parses the saved Cycle 6 Gibson City HTML."""
    site = bushel_source.get_bushel_site("alliance_grain")
    assert site.company == "Alliance Grain"
    assert site.url == "https://www.alliance-grain.com/cash-bids"
    assert site.currency == "USD"
    assert site.default_location == "Anchor/Cropsey/Colfax"
    assert "Anchor/Cropsey/Colfax" in site.notes
    assert site.verified is True
