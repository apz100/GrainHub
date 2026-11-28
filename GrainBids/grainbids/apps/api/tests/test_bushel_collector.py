"""Tests for the generic Bushel-pattern collector (Cycle 4).

All parsing tests run against saved synthetic fixtures in
tests/fixtures/ — no live fetching inside pytest. Fixture values are
invented test data, not live prices.
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


# ---------------------------------------------------------------------------
# FAC shape: 7-column widget, month delivery labels, multi-location
# ---------------------------------------------------------------------------


def test_bushel_fac_widget_parses_seven_columns_and_locations() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_fac_sample.html"), site=bushel_source.get_bushel_site("fac")
    )
    assert result["status"] == "ok"
    assert result["company"] == "FAC"
    assert result["location"] == "Arcadia"
    rows = result["rows"]
    assert len(rows) == 5  # all-dash placeholder row is skipped
    arcadia_corn = next(
        r
        for r in rows
        if r["commodity"] == "Corn"
        and r["location"] == "Arcadia"
        and r["delivery_month"] == "November '26"
    )
    assert arcadia_corn["cash_price"] == 3.98
    assert arcadia_corn["basis"] == -0.35
    assert arcadia_corn["futures_price"] == 4.3325
    assert arcadia_corn["change"] == -2.25
    assert arcadia_corn["futures_month"] == "Dec 26 Corn"
    assert arcadia_corn["last_trade"] == "10:54 AM"
    assert arcadia_corn["currency"] == "USD"
    assert arcadia_corn["unit"] == "$/bu"
    assert arcadia_corn["cash_price_mt"] is None
    assert arcadia_corn["note"] == ""
    # Forward month label is carried verbatim.
    far = next(
        r
        for r in rows
        if r["commodity"] == "Corn" and r["delivery_month"] == "Oct. / Nov. '27"
    )
    assert far["cash_price"] == 4.25
    # Second location on the same page gets its own rows.
    schleswig = [r for r in rows if r["location"] == "Schleswig"]
    assert len(schleswig) == 1
    assert schleswig[0]["cash_price"] == 3.90
    assert any("Cash bids for" in n for n in result["notes"])


def test_bushel_fac_footer_table_is_not_read_as_bids() -> None:
    # The FAC page's only <table> is the "Data provided by Bushel"
    # footer. The widget must win; the footer must not add rows.
    result = bushel_source.parse_bushel_html(
        _read("bushel_fac_sample.html"), site=bushel_source.get_bushel_site("fac")
    )
    assert result["status"] == "ok"
    assert all(r["commodity"] in ("Corn", "Soybeans") for r in result["rows"])


# ---------------------------------------------------------------------------
# Collwest shape: 5-column widget, crop-year labels, thin rows, CAD/t
# ---------------------------------------------------------------------------


def test_bushel_collwest_widget_parses_five_columns_and_thin_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_collwest_sample.html"),
        site=bushel_source.get_bushel_site("collwest"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Collwest Grain"
    assert result["location"] == "Collingwood"
    rows = result["rows"]
    assert len(rows) == 5
    corn = next(
        r for r in rows if r["commodity"] == "Corn" and r["delivery_month"] == "2026 Crop"
    )
    assert corn["cash_price"] == 5.58
    assert corn["basis"] == 1.25
    assert corn["futures_price"] == 4.3325
    assert corn["currency"] == "CAD"
    assert corn["unit"] == "$/bu"
    assert corn["cash_price_mt"] is None
    assert corn["note"] == ""
    # Thin Bid-only rows are kept, with explicit Nones + a reason.
    barley = next(r for r in rows if r["commodity"] == "Barley")
    assert barley["cash_price"] == 280.00
    assert barley["basis"] is None
    assert barley["futures_price"] is None
    assert barley["change"] is None
    assert "Bid only" in barley["note"]
    oats = next(r for r in rows if r["commodity"] == "Oats")
    assert oats["cash_price"] == 340.00
    assert oats["basis"] is None
    assert "Bid only" in oats["note"]


def test_bushel_collwest_per_tonne_units() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_collwest_sample.html"),
        site=bushel_source.get_bushel_site("collwest"),
    )
    rows = result["rows"]
    canola = next(r for r in rows if r["commodity"] == "Canola")
    assert canola["cash_price"] == 720.30
    assert canola["unit"] == "$/t"
    # Per-tonne bid is the published number, not a conversion.
    assert canola["cash_price_mt"] == 720.30
    barley = next(r for r in rows if r["commodity"] == "Barley")
    assert barley["unit"] == "$/t"
    assert barley["cash_price_mt"] == 280.00
    corn = next(r for r in rows if r["commodity"] == "Corn")
    assert corn["unit"] == "$/bu"


def test_bushel_futures_market_table_is_not_read_as_bids() -> None:
    # Collwest's market_table is a futures table (Contract / Last /
    # Chg). With no widget it must not be mistaken for cash bids.
    html = """
    <html><body><table class="market_table">
      <tr><td colspan="8">Corn</td></tr>
      <tr><th>Contract</th><th>Last</th><th>Chg</th><th>High</th><th>Low</th><th>Open</th><th>Time</th><th></th></tr>
      <tr><td>Dec 26</td><td>4.3325</td><td>-2.25</td><td>4.3625</td><td>4.3225</td><td>468-4</td><td>10:54</td><td></td></tr>
    </table></body></html>
    """
    result = bushel_source.parse_bushel_html(html, company="Test Co")
    assert result["status"] == "unsupported"
    assert result["rows"] == []
    assert any("Delivery/Bid" in n for n in result["notes"])


# ---------------------------------------------------------------------------
# Real-<table> fallback (documented standardTable / market_table forms)
# ---------------------------------------------------------------------------


def test_bushel_standard_table_fallback_parses_seven_columns() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_table_sample.html"), company="Table Co", currency="USD"
    )
    assert result["status"] == "ok"
    rows = result["rows"]
    assert len(rows) == 3  # all-dash row skipped
    corn = next(
        r for r in rows if r["commodity"] == "Corn" and r["delivery_month"] == "November '26"
    )
    assert corn["cash_price"] == 3.98
    assert corn["basis"] == -0.35
    assert corn["futures_month"] == "Dec 26 Corn"
    assert corn["last_trade"] == "10:54 AM"
    soy = next(r for r in rows if r["commodity"] == "Soybeans")
    assert soy["cash_price"] == 11.41
    assert any("table" in n for n in result["notes"])


def test_bushel_market_table_fallback_parses_five_columns() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_market_table_sample.html"),
        site=bushel_source.get_bushel_site("collwest"),
    )
    assert result["status"] == "ok"
    rows = result["rows"]
    assert len(rows) == 3
    corn_2027 = next(
        r for r in rows if r["commodity"] == "Corn" and r["delivery_month"] == "2027 Crop"
    )
    assert corn_2027["cash_price"] == 5.70
    assert corn_2027["currency"] == "CAD"
    barley = next(r for r in rows if r["commodity"] == "Barley")
    assert barley["cash_price"] == 280.00
    assert barley["unit"] == "$/t"
    assert barley["basis"] is None
    assert "Bid only" in barley["note"]


# ---------------------------------------------------------------------------
# Cycle 5 shapes: 6-column widget, fractional quotes, classless h2,
# "Cash Price" header, grade-prefixed labels, HRW without "(protein in)"
# ---------------------------------------------------------------------------


def test_bushel_money_parses_fractional_eighths() -> None:
    # CBOT-style fractional quotes (Chandler, Forest River): whole
    # cents + eighths, converted to decimal in the published unit.
    assert bushel_source._money("433-2") == 433.25
    assert bushel_source._money("-2-2") == -2.25
    assert bushel_source._money("+0-6") == 0.75
    assert bushel_source._money("630-0") == 630.0
    # Decimal quotes are untouched.
    assert bushel_source._money("4.3325") == 4.3325
    assert bushel_source._money("-0.35") == -0.35
    assert bushel_source._money("-2.25") == -2.25
    assert bushel_source._money("") is None
    assert bushel_source._money("—") is None


def test_bushel_chandler_six_columns_fractional_and_classless_h2() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_chandler_sample.html"),
        site=bushel_source.get_bushel_site("chandler_feed"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Chandler Feed"
    # The location h2 carries no class on this site; it still counts.
    assert result["location"] == "Chandler"
    rows = result["rows"]
    assert len(rows) == 3
    corn = next(
        r for r in rows if r["commodity"] == "Corn" and r["delivery_month"] == "Nov"
    )
    assert corn["cash_price"] == 4.11
    assert corn["basis"] == -0.42
    assert corn["futures_price"] == 452.5  # "452-4" in fractional cents
    assert corn["change"] == -1.5  # "-1-4"
    assert corn["futures_month"] == "Dec 26 Corn"
    assert corn["last_trade"] is None  # 6-col layout has no Last Trade
    assert corn["currency"] == "USD"
    assert corn["unit"] == "$/bu"
    oats = next(r for r in rows if r["commodity"] == "Oats")
    assert oats["delivery_month"] == "Cash"
    assert oats["futures_price"] == 399.25  # "399-2"
    assert oats["change"] == -0.25  # "-0-2"


def test_bushel_forest_river_cash_price_header_and_grade_labels() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_forest_river_sample.html"),
        site=bushel_source.get_bushel_site("forest_river"),
    )
    assert result["status"] == "ok"
    assert result["location"] == "Forest River"
    rows = result["rows"]
    assert len(rows) == 2
    wheat = next(r for r in rows if r["commodity"] == "Wheat — HRS")
    # First section heads Bid as "Cash Price" with a blank Delivery
    # header; the delivery/grade label and the bid must still parse.
    assert wheat["delivery_month"] == "#1 HRS"
    assert wheat["cash_price"] == 6.05
    assert wheat["basis"] == -0.45
    assert wheat["futures_price"] == 650.5  # "650-4"
    assert wheat["change"] == 1.25  # "+1-2"
    assert wheat["futures_month"] == "Dec 26 MIAX Spring Wheat"
    corn = next(r for r in rows if r["commodity"] == "Corn")
    assert corn["delivery_month"] == "#2 yellow"
    assert corn["cash_price"] == 3.71


def test_bushel_rugby_five_columns_classless_h2_and_hrs_label() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_rugby_sample.html"),
        site=bushel_source.get_bushel_site("rugby"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Rugby Farmers Elevator"
    # Classless h2 "Rugby & York Bids" maps to the home town; the page
    # covers Rugby & York (see the registry note).
    assert result["location"] == "Rugby"
    rows = result["rows"]
    assert len(rows) == 3
    wheat = next(r for r in rows if r["commodity"] == "Wheat — HRS")
    assert wheat["delivery_month"] == "Nov"
    assert wheat["cash_price"] == 5.88
    assert wheat["futures_price"] == 6.5
    assert wheat["futures_month"] is None  # 5-col layout
    corn = next(r for r in rows if r["commodity"] == "Corn")
    assert corn["cash_price"] == 3.66
    assert corn["currency"] == "USD"


def test_bushel_almota_hrw_label_and_thin_barley_per_tonne() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_almota_sample.html"),
        site=bushel_source.get_bushel_site("almota"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Almota Elevator"
    assert result["location"] == "Colfax"
    rows = result["rows"]
    assert len(rows) == 3
    hrw = next(r for r in rows if r["commodity"] == "Wheat — HRW")
    assert hrw["delivery_month"] == "November"
    assert hrw["cash_price"] == 6.71
    assert hrw["futures_month"] == "Dec 26 KCBT Red Wheat"
    sww = next(r for r in rows if r["commodity"] == "Wheat — SWW")
    assert sww["cash_price"] == 6.32
    # Barley is Bid-only at per-tonne scale on this site.
    barley = next(r for r in rows if r["commodity"] == "Barley")
    assert barley["cash_price"] == 172.00
    assert barley["unit"] == "$/t"
    assert barley["cash_price_mt"] == 172.00
    assert barley["basis"] is None
    assert "Bid only" in barley["note"]


# ---------------------------------------------------------------------------
# Empty / unsupported / fetch behaviour
# ---------------------------------------------------------------------------


def test_bushel_empty_widget_is_empty() -> None:
    html = (
        "<html><body><div class='cbmod'>"
        "<div class='cashBidLocation'><h2 class='fcControls'>Arcadia</h2></div>"
        "</div></body></html>"
    )
    result = bushel_source.parse_bushel_html(html, company="FAC")
    assert result["status"] == "empty"
    assert result["rows"] == []


def test_bushel_no_widget_or_table_is_unsupported() -> None:
    result = bushel_source.parse_bushel_html(
        "<html><body><p>Cash bids coming soon.</p></body></html>", company="FAC"
    )
    assert result["status"] == "unsupported"
    assert result["rows"] == []
    assert any("no cash-bid widget" in n.lower() for n in result["notes"])


def test_bushel_fetch_uses_contact_user_agent() -> None:
    class _FakeResponse:
        text = "<html></html>"

        def raise_for_status(self) -> None:
            pass

    with patch("app.platform.market_data.sources.bushel_source.requests.get") as fake_get:
        fake_get.return_value = _FakeResponse()
        bushel_source.fetch_bushel_html(bushel_source.FAC_URL)
    _, kwargs = fake_get.call_args
    assert kwargs["headers"]["User-Agent"] == bushel_source.CONTACT_USER_AGENT
    assert fake_get.call_args.args[0] == bushel_source.FAC_URL


def test_bushel_unverified_site_refuses_to_fetch() -> None:
    # Unverified catalogue entries must not be scraped blind. All
    # registry sites are verified as of Cycle 5, so the guard is
    # exercised with a synthetic unverified entry.
    draft = bushel_source.BushelSite(
        key="draft_site",
        company="Draft Co",
        url="https://example.invalid/",
        currency="USD",
    )
    with patch.dict(bushel_source.BUSHEL_SITES, {"draft_site": draft}):
        result = bushel_source.fetch_bushel_site("draft_site")
        assert result["status"] == "unsupported"
        assert result["rows"] == []
        assert any("not verified" in n for n in result["notes"])
        with patch(
            "app.platform.market_data.sources.bushel_source.requests.get"
        ) as fake_get:
            bushel_source.fetch_bushel_site("draft_site")
        fake_get.assert_not_called()


def test_bushel_unknown_site_key_raises() -> None:
    try:
        bushel_source.get_bushel_site("nope")
    except KeyError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("expected KeyError")


# ---------------------------------------------------------------------------
# Farmbucks batch (2026-11-28): recorded live fixtures — values are the
# live prices at capture time, trimmed to the .cbmod widget.
# ---------------------------------------------------------------------------


def test_bushel_jennie_o_thirteen_corn_rows_faribault_medford() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_jennie_o_sample.html"),
        site=bushel_source.get_bushel_site("jennie_o"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Jennie-O Turkey Store"
    assert result["location"] == "Faribault/Medford"
    rows = result["rows"]
    assert len(rows) == 13
    assert {r["commodity"] for r in rows} == {"Corn"}
    assert {r["location"] for r in rows} == {"Faribault/Medford"}
    assert all(r["currency"] == "USD" and r["unit"] == "$/bu" for r in rows)
    dec = next(r for r in rows if r["delivery_month"] == "Dec 26")
    assert dec["cash_price"] == 4.06
    assert dec["basis"] == -0.56
    assert dec["futures_price"] == 4.625
    assert dec["futures_month"] == "Mar 27 Corn"
    assert dec["last_trade"] == "12:05 PM"
    assert dec["note"] == ""
    assert any("Cash bids for Friday, November 27, 2026" in n for n in result["notes"])


def test_bushel_midland_eight_rows_brownell_white_wheat_passthrough() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_midland_sample.html"),
        site=bushel_source.get_bushel_site("midland"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Midland Marketing"
    assert result["location"] == "Brownell"
    rows = result["rows"]
    assert len(rows) == 8
    assert {r["commodity"] for r in rows} == {"Corn", "Milo", "Wheat", "White Wheat"}
    assert all(len([r for r in rows if r["commodity"] == c]) == 2 for c in ("Corn", "Milo", "Wheat", "White Wheat"))
    assert all(r["currency"] == "USD" and r["unit"] == "$/bu" for r in rows)
    wheat_cash = next(
        r for r in rows if r["commodity"] == "Wheat" and r["delivery_month"] == "Cash"
    )
    assert wheat_cash["cash_price"] == 5.47
    assert wheat_cash["basis"] == -0.6
    assert wheat_cash["futures_price"] == 6.0725
    assert wheat_cash["futures_month"] == "Dec 26 KCBT Red Wheat"
    # "White Wheat" is not in COMMODITY_MAP and passes through as-is.
    white = next(r for r in rows if r["commodity"] == "White Wheat")
    assert white["delivery_month"] == "Cash"
    assert white["cash_price"] == 5.47
    assert any("Cash bids for Friday, November 27, 2026" in n for n in result["notes"])
