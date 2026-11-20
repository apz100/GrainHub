"""Per-location Bushel probes (Cycle 12).

Winchester 3440: the second Wheaton Grain embed target
(/cashbidssingle-3440?embed=y) serves a standard wrapped 7-column
Bushel .cbmod widget — 5 rows, Soybeans only — but the location h2 is
"Georgetown", not Winchester: 3440 is Wheaton's Georgetown location
(3439 is Winchester). Verified live 2026-11-19.

Skyland 2730: the first ID from the 14-location picker on the default
page serves a standard wrapped 7-column .cbmod widget — 6 rows (Corn
2, Milo 1, Red Wheat 2, Soybeans 1, Cunningham Area), the same rows
as the default /cashbidssingle- page: 2730 is Cunningham Area's own
per-location ID. Verified live 2026-11-19.

Smithfield 1666 (Bentonville, NC): the first Smithfield location
verified — a standard wrapped 7-column .cbmod widget, 3 rows
(Soybeans 1, Wheat 1, Corn 1), location h2 "Bentonville, NC" mapped
to "Bentonville". Verified live 2026-11-19.

All three parsed by the existing generic parser with no changes.
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


def test_winchester_3440_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("winchester_3440")
    assert site.company == "Winchester Ag"
    assert site.url == "https://www.wheatongrain.com/cashbidssingle-3440?embed=y"
    assert site.currency == "USD"
    assert site.default_location == "Georgetown"
    assert site.verified is True


def test_winchester_3440_fixture_parses_five_soybean_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_winchester_3440_sample.html"),
        site=bushel_source.get_bushel_site("winchester_3440"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Winchester Ag"
    assert result["location"] == "Georgetown"
    rows = result["rows"]
    assert len(rows) == 5
    assert all(r["commodity"] == "Soybeans" for r in rows)
    assert [r["delivery_month"] for r in rows] == [
        "Nov",
        "Dec",
        "Jan",
        "Mch",
        "O/N 2027",
    ]
    assert rows[0]["cash_price"] == 11.90
    assert rows[4]["cash_price"] == 11.20
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_winchester_3440_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_winchester_3440_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_winchester_3440()
    fetch_html.assert_called_once_with(
        "https://www.wheatongrain.com/cashbidssingle-3440?embed=y"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 5
    assert result["rows"][0]["location"] == "Georgetown"


def test_skyland_2730_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2730")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2730"
    assert site.currency == "USD"
    assert site.default_location == "Cunningham Area"
    assert site.verified is True


def test_skyland_2730_fixture_parses_six_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2730_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2730"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Cunningham Area"
    rows = result["rows"]
    assert len(rows) == 6
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
        "Soybeans",
    ]
    assert rows[0]["cash_price"] == 4.20
    assert rows[2]["cash_price"] == 3.85
    assert rows[5]["cash_price"] == 11.40
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2730_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2730_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2730()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2730"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 6
    assert result["rows"][0]["location"] == "Cunningham Area"


def test_smithfield_bentonville_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("smithfield_bentonville")
    assert site.company == "Smithfield Grain"
    assert site.url == "https://smithfieldgrain.com/cashbidssingle-1666"
    assert site.currency == "USD"
    assert site.default_location == "Bentonville"
    assert site.verified is True


def test_smithfield_bentonville_fixture_parses_three_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_smithfield_bentonville_sample.html"),
        site=bushel_source.get_bushel_site("smithfield_bentonville"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Smithfield Grain"
    assert result["location"] == "Bentonville"
    rows = result["rows"]
    assert len(rows) == 3
    assert [r["commodity"] for r in rows] == ["Soybeans", "Wheat", "Corn"]
    # The live page's location h2 is "Bentonville, NC"; the registry
    # entry maps it to the town name.
    assert all(r["location"] == "Bentonville" for r in rows)
    assert [r["delivery_month"] for r in rows] == [
        "Nov/Dec Delivery",
        "June Delivery",
        "November",
    ]
    assert rows[0]["cash_price"] == 11.90
    assert rows[1]["cash_price"] == 5.50
    assert rows[2]["cash_price"] == 4.85
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_smithfield_bentonville_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_smithfield_bentonville_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_smithfield_bentonville()
    fetch_html.assert_called_once_with(
        "https://smithfieldgrain.com/cashbidssingle-1666"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 3
    assert result["rows"][0]["location"] == "Bentonville"
