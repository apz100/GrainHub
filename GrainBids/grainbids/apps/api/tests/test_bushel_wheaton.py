"""Wheaton Grain tests (Cycle 11 tabbed-widget gap fix).

One polite GET of https://www.wheatongrain.com (2026-11-19,
GrainHub-Research/1.0) returned 200 with a tabbed Bushel ``.cbmod``
widget in static HTML — easyResponsiveTabs, NO ``div.cbCommodity``
wrappers, bare ``h3.fcControls`` commodity headings followed by
sixColumnsBigFirst ul row groups, location in the resp-tabs-list tab
("Chippewa Falls"), no h2 at all — 5 rows (Corn 2 + Soybeans 3).
The generic parser returned "empty" against that shape before the
Cycle 11 fallback in ``_parse_widget`` / ``_parse_tabbed_widget``.

The fixture below is synthetic: same widget shape as the live page,
invented prices. No live fetching inside pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import bushel_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_wheaton_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("wheaton_grain")
    assert site.company == "Wheaton Grain"
    assert site.url == "https://www.wheatongrain.com"
    assert site.currency == "USD"
    assert site.default_location == "Chippewa Falls"
    assert site.verified is True


def test_wheaton_tabbed_widget_parses_five_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_wheaton_sample.html"),
        site=bushel_source.get_bushel_site("wheaton_grain"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Wheaton Grain"
    assert result["location"] == "Chippewa Falls"
    rows = result["rows"]
    assert len(rows) == 5
    assert all(r["location"] == "Chippewa Falls" for r in rows)
    assert all(r["currency"] == "USD" for r in rows)
    assert all(r["unit"] == "$/bu" for r in rows)
    assert all(r["cash_price"] is not None for r in rows)
    assert all(r["note"] == "" for r in rows)


def test_wheaton_mixed_commodity_headings_and_cash_header() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_wheaton_sample.html"),
        site=bushel_source.get_bushel_site("wheaton_grain"),
    )
    rows = result["rows"]
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Soybeans",
        "Soybeans",
        "Soybeans",
    ]
    # Corn section heads the Bid column "Cash" — still maps to cash_price.
    corn_nov = next(
        r
        for r in rows
        if r["commodity"] == "Corn" and r["delivery_month"] == "November"
    )
    assert corn_nov["cash_price"] == 3.80
    assert corn_nov["basis"] == -0.55
    assert corn_nov["futures_price"] == 4.35
    assert corn_nov["change"] == -1.00
    assert corn_nov["futures_month"] == "Dec 26 Corn"
    corn_dec = next(
        r
        for r in rows
        if r["commodity"] == "Corn" and r["delivery_month"] == "December"
    )
    assert corn_dec["cash_price"] == 3.85
    assert corn_dec["change"] == 2.00
    soy_jan = next(
        r
        for r in rows
        if r["commodity"] == "Soybeans" and r["delivery_month"] == "January"
    )
    assert soy_jan["cash_price"] == 11.50
    assert soy_jan["basis"] == -0.50
    assert soy_jan["futures_price"] == 12.00
    assert soy_jan["change"] == 0.00
    assert soy_jan["futures_month"] == "Jan 27 Soybeans"


def test_wheaton_header_rows_are_skipped() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_wheaton_sample.html"),
        site=bushel_source.get_bushel_site("wheaton_grain"),
    )
    rows = result["rows"]
    # The two fcControlsSubHdr header uls yield no rows: 5 data rows only.
    assert len(rows) == 5
    assert not any(r["delivery_month"] == "Delivery" for r in rows)
    assert not any(r["cash_price"] is None for r in rows)
    assert {r["delivery_month"] for r in rows} == {
        "November",
        "December",
        "January",
    }


def test_fetch_wheaton_grain_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_wheaton_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_wheaton_grain()
    fetch_html.assert_called_once_with("https://www.wheatongrain.com")
    assert result["status"] == "ok"
    assert len(result["rows"]) == 5
    assert result["rows"][0]["location"] == "Chippewa Falls"


def test_existing_wrapped_shapes_still_parse() -> None:
    """Regression: the tabbed fallback must not change the wrapped
    div.cbCommodity path — Synergy (6-col) and FAC (7-col) fixtures
    still parse to the same row counts as before the Cycle 11 change."""
    synergy = bushel_source.parse_bushel_html(
        _read("bushel_synergy_sample.html"),
        site=bushel_source.get_bushel_site("synergy"),
    )
    assert synergy["status"] == "ok"
    assert len(synergy["rows"]) == 4
    assert {r["commodity"] for r in synergy["rows"]} == {"Corn", "Soybeans"}

    fac = bushel_source.parse_bushel_html(
        _read("bushel_fac_sample.html"),
        site=bushel_source.get_bushel_site("fac"),
    )
    assert fac["status"] == "ok"
    assert len(fac["rows"]) == 5
    assert {r["commodity"] for r in fac["rows"]} == {"Corn", "Soybeans"}
