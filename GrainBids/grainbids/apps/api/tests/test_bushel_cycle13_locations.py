"""Per-location Bushel probes (Cycle 13).

Skyland 2731 / 2734 / 2740 / 2742 / 2754 / 2761 and Smithfield
1725 (Bladenboro), 1667 (Bladenboro Feed Mill), 2294 (Chadbourn),
1668 (Clarkton): each serves a standard wrapped 7-column Bushel
.cbmod widget — the FAC shape, not Wheaton Grain's tabbed variant —
parsed by the existing generic parser with no changes. Verified
live 2026-11-19, one polite GET each.

Skyland: every page carries Corn 2 + Milo 1 + Red Wheat 2;
Soybeans appears on 2740 only, White Wheat on 2740 / 2742 / 2761.
Smithfield: thin pages — Bladenboro, Chadbourn and Clarkton each
carry a single Soybeans row; Bladenboro Feed Mill carries Corn +
Wheat. Location h2s carry ", NC" and are mapped to the town name,
as with Bentonville (Cycle 12). Chadbourn's widget header is dated
Nov 18, 2026 — a day older than the other Cycle 13 pages.

Fixtures below are synthetic: same widget shapes as the live pages,
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


# ---------------------------------------------------------------------------
# Skyland — Conlen - Hartley (2731)
# ---------------------------------------------------------------------------


def test_skyland_2731_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2731")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2731"
    assert site.currency == "USD"
    assert site.default_location == "Conlen - Hartley"
    assert site.verified is True


def test_skyland_2731_fixture_parses_five_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2731_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2731"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Conlen - Hartley"
    rows = result["rows"]
    assert len(rows) == 5
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
    ]
    assert rows[0]["cash_price"] == 4.18
    assert rows[2]["cash_price"] == 3.82
    assert rows[4]["cash_price"] == 5.78
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2731_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2731_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2731()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2731"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 5
    assert result["rows"][0]["location"] == "Conlen - Hartley"


# ---------------------------------------------------------------------------
# Skyland — Etter (2734)
# ---------------------------------------------------------------------------


def test_skyland_2734_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2734")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2734"
    assert site.currency == "USD"
    assert site.default_location == "Etter"
    assert site.verified is True


def test_skyland_2734_fixture_parses_five_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2734_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2734"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Etter"
    rows = result["rows"]
    assert len(rows) == 5
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
    ]
    assert rows[0]["cash_price"] == 4.22
    assert rows[2]["cash_price"] == 3.88
    assert rows[4]["cash_price"] == 5.82
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2734_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2734_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2734()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2734"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 5
    assert result["rows"][0]["location"] == "Etter"


# ---------------------------------------------------------------------------
# Skyland — Moscow, Dermot, Kismet, Pleasant Valley (2740)
# ---------------------------------------------------------------------------


def test_skyland_2740_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2740")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2740"
    assert site.currency == "USD"
    assert site.default_location == "Moscow, Dermot, Kismet, Pleasant Valley"
    assert site.verified is True


def test_skyland_2740_fixture_parses_seven_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2740_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2740"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Moscow, Dermot, Kismet, Pleasant Valley"
    rows = result["rows"]
    assert len(rows) == 7
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
        "Soybeans",
        "White Wheat",
    ]
    assert rows[0]["cash_price"] == 4.25
    assert rows[5]["cash_price"] == 11.35
    # "White Wheat" is not in COMMODITY_MAP and passes through as-is,
    # like "Red Wheat" — no parser change for it.
    assert rows[6]["commodity"] == "White Wheat"
    assert rows[6]["cash_price"] == 5.95
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2740_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2740_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2740()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2740"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 7
    assert result["rows"][0]["location"] == (
        "Moscow, Dermot, Kismet, Pleasant Valley"
    )


# ---------------------------------------------------------------------------
# Skyland — Johnson - Ulysses - N Sublette (2742)
# ---------------------------------------------------------------------------


def test_skyland_2742_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2742")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2742"
    assert site.currency == "USD"
    assert site.default_location == "Johnson - Ulysses - N Sublette"
    assert site.verified is True


def test_skyland_2742_fixture_parses_seven_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2742_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2742"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Johnson - Ulysses - N Sublette"
    rows = result["rows"]
    assert len(rows) == 7
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
        "White Wheat",
        "White Wheat",
    ]
    assert rows[0]["cash_price"] == 4.19
    assert rows[5]["cash_price"] == 5.92
    assert rows[6]["cash_price"] == 6.12
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2742_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2742_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2742()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2742"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 7
    assert result["rows"][0]["location"] == "Johnson - Ulysses - N Sublette"


# ---------------------------------------------------------------------------
# Skyland — Olton Area (2754)
# ---------------------------------------------------------------------------


def test_skyland_2754_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2754")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2754"
    assert site.currency == "USD"
    assert site.default_location == "Olton Area"
    assert site.verified is True


def test_skyland_2754_fixture_parses_five_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2754_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2754"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Olton Area"
    rows = result["rows"]
    assert len(rows) == 5
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
    ]
    assert rows[0]["cash_price"] == 4.21
    assert rows[2]["cash_price"] == 3.87
    assert rows[4]["cash_price"] == 5.81
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2754_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2754_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2754()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2754"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 5
    assert result["rows"][0]["location"] == "Olton Area"


# ---------------------------------------------------------------------------
# Skyland — Elkhart - Hough - Rolla Area (2761)
# ---------------------------------------------------------------------------


def test_skyland_2761_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2761")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2761"
    assert site.currency == "USD"
    assert site.default_location == "Elkhart - Hough - Rolla Area"
    assert site.verified is True


def test_skyland_2761_fixture_parses_six_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2761_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2761"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Elkhart - Hough - Rolla Area"
    rows = result["rows"]
    assert len(rows) == 6
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
        "White Wheat",
    ]
    assert rows[0]["cash_price"] == 4.23
    assert rows[5]["cash_price"] == 5.96
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2761_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2761_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2761()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2761"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 6
    assert result["rows"][0]["location"] == "Elkhart - Hough - Rolla Area"


# ---------------------------------------------------------------------------
# Smithfield — Bladenboro (1725)
# ---------------------------------------------------------------------------


def test_smithfield_bladenboro_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("smithfield_bladenboro")
    assert site.company == "Smithfield Grain"
    assert site.url == "https://smithfieldgrain.com/cashbidssingle-1725"
    assert site.currency == "USD"
    assert site.default_location == "Bladenboro"
    assert site.verified is True


def test_smithfield_bladenboro_fixture_parses_one_soybean_row() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_smithfield_bladenboro_sample.html"),
        site=bushel_source.get_bushel_site("smithfield_bladenboro"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Smithfield Grain"
    assert result["location"] == "Bladenboro"
    rows = result["rows"]
    assert len(rows) == 1
    assert rows[0]["commodity"] == "Soybeans"
    # The live page's location h2 is "Bladenboro, NC"; the registry
    # entry maps it to the town name.
    assert rows[0]["location"] == "Bladenboro"
    assert rows[0]["delivery_month"] == "Nov/Dec Delivery"
    assert rows[0]["cash_price"] == 11.85
    assert rows[0]["currency"] == "USD"
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_smithfield_bladenboro_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_smithfield_bladenboro_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_smithfield_bladenboro()
    fetch_html.assert_called_once_with(
        "https://smithfieldgrain.com/cashbidssingle-1725"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 1
    assert result["rows"][0]["location"] == "Bladenboro"


# ---------------------------------------------------------------------------
# Smithfield — Bladenboro Feed Mill (1667)
# ---------------------------------------------------------------------------


def test_smithfield_bladenboro_feed_mill_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("smithfield_bladenboro_feed_mill")
    assert site.company == "Smithfield Grain"
    assert site.url == "https://smithfieldgrain.com/cashbidssingle-1667"
    assert site.currency == "USD"
    assert site.default_location == "Bladenboro Feed Mill"
    assert site.verified is True


def test_smithfield_bladenboro_feed_mill_fixture_parses_two_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_smithfield_bladenboro_feed_mill_sample.html"),
        site=bushel_source.get_bushel_site("smithfield_bladenboro_feed_mill"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Smithfield Grain"
    assert result["location"] == "Bladenboro Feed Mill"
    rows = result["rows"]
    assert len(rows) == 2
    assert [r["commodity"] for r in rows] == ["Corn", "Wheat"]
    # The live page's location h2 is "Bladenboro Feed Mill, NC".
    assert all(r["location"] == "Bladenboro Feed Mill" for r in rows)
    assert [r["delivery_month"] for r in rows] == [
        "November",
        "June Delivery",
    ]
    assert rows[0]["cash_price"] == 4.82
    assert rows[1]["cash_price"] == 5.45
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_smithfield_bladenboro_feed_mill_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_smithfield_bladenboro_feed_mill_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_smithfield_bladenboro_feed_mill()
    fetch_html.assert_called_once_with(
        "https://smithfieldgrain.com/cashbidssingle-1667"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 2
    assert result["rows"][0]["location"] == "Bladenboro Feed Mill"


# ---------------------------------------------------------------------------
# Smithfield — Chadbourn (2294)
# ---------------------------------------------------------------------------


def test_smithfield_chadbourn_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("smithfield_chadbourn")
    assert site.company == "Smithfield Grain"
    assert site.url == "https://smithfieldgrain.com/cashbidssingle-2294"
    assert site.currency == "USD"
    assert site.default_location == "Chadbourn"
    assert site.verified is True


def test_smithfield_chadbourn_fixture_parses_one_soybean_row() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_smithfield_chadbourn_sample.html"),
        site=bushel_source.get_bushel_site("smithfield_chadbourn"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Smithfield Grain"
    assert result["location"] == "Chadbourn"
    rows = result["rows"]
    assert len(rows) == 1
    assert rows[0]["commodity"] == "Soybeans"
    # The live page's location h2 is "Chadbourn, NC".
    assert rows[0]["location"] == "Chadbourn"
    assert rows[0]["delivery_month"] == "Nov/Dec Delivery"
    assert rows[0]["cash_price"] == 11.88
    assert rows[0]["currency"] == "USD"
    # The live widget header is dated Nov 18, 2026 — a day older
    # than the other Cycle 13 pages (Nov 19).
    assert any("November 18, 2026" in n for n in result["notes"])


def test_fetch_smithfield_chadbourn_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_smithfield_chadbourn_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_smithfield_chadbourn()
    fetch_html.assert_called_once_with(
        "https://smithfieldgrain.com/cashbidssingle-2294"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 1
    assert result["rows"][0]["location"] == "Chadbourn"


# ---------------------------------------------------------------------------
# Smithfield — Clarkton (1668)
# ---------------------------------------------------------------------------


def test_smithfield_clarkton_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("smithfield_clarkton")
    assert site.company == "Smithfield Grain"
    assert site.url == "https://smithfieldgrain.com/cashbidssingle-1668"
    assert site.currency == "USD"
    assert site.default_location == "Clarkton"
    assert site.verified is True


def test_smithfield_clarkton_fixture_parses_one_soybean_row() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_smithfield_clarkton_sample.html"),
        site=bushel_source.get_bushel_site("smithfield_clarkton"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Smithfield Grain"
    assert result["location"] == "Clarkton"
    rows = result["rows"]
    assert len(rows) == 1
    assert rows[0]["commodity"] == "Soybeans"
    # The live page's location h2 is "Clarkton, NC".
    assert rows[0]["location"] == "Clarkton"
    assert rows[0]["delivery_month"] == "Nov/Dec Delivery"
    assert rows[0]["cash_price"] == 11.92
    assert rows[0]["currency"] == "USD"
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_smithfield_clarkton_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_smithfield_clarkton_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_smithfield_clarkton()
    fetch_html.assert_called_once_with(
        "https://smithfieldgrain.com/cashbidssingle-1668"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 1
    assert result["rows"][0]["location"] == "Clarkton"
