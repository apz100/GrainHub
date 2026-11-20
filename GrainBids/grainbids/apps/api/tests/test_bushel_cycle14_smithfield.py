"""Per-location Bushel probes (Cycle 14).

Smithfield 1669 (Clinton), 1670 (Hobbsville), 1671 (Kinston),
1672 (LaGrange), 1673 (Morgan's Corner), 1674 (Mount Olive):
each serves a standard wrapped 7-column Bushel .cbmod widget —
the FAC shape, not Wheaton Grain's tabbed variant — parsed by the
existing generic parser with no changes. Verified live 2026-11-19,
one polite GET each. The list page itself was recovered from the
saved Cycle 11 page (/tmp/cycle11/smithfield_fccp.html), so no GET
was spent re-fetching it; the 6 probes are the only GETs this cycle.

Clinton, Hobbsville, Kinston, LaGrange and Mount Olive each carry
3 rows (Corn + Soybeans + Wheat); Morgan's Corner carries 2 rows
(Soybeans + Wheat). Location h2s carry ", NC" and are mapped to
the town name, as with Bentonville (Cycle 12); the live h2 for
1673 is "Morgans Corner, NC" (no apostrophe). All six widget
headers are dated Thursday, November 19, 2026.

Fixtures below are synthetic: same widget shapes as the live pages,
invented prices. No live fetching inside pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import bushel_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _check_site(key: str, url: str, location: str, fixture: str, commodities: list[str], first_bid: float) -> None:
    site = bushel_source.get_bushel_site(key)
    assert site.company == "Smithfield Grain"
    assert site.url == url
    assert site.currency == "USD"
    assert site.default_location == location
    assert site.verified is True
    result = bushel_source.parse_bushel_html(
        _read(fixture),
        site=site,
    )
    assert result["status"] == "ok"
    assert result["company"] == "Smithfield Grain"
    assert result["location"] == location
    rows = result["rows"]
    assert [r["commodity"] for r in rows] == commodities
    assert rows[0]["location"] == location
    assert rows[0]["cash_price"] == first_bid
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_smithfield_clinton_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_clinton",
        "https://smithfieldgrain.com/cashbidssingle-1669",
        "Clinton",
        "bushel_smithfield_clinton_sample.html",
        ["Corn", "Soybeans", "Wheat"],
        4.41,
    )


def test_smithfield_hobbsville_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_hobbsville",
        "https://smithfieldgrain.com/cashbidssingle-1670",
        "Hobbsville",
        "bushel_smithfield_hobbsville_sample.html",
        ["Corn", "Soybeans", "Wheat"],
        4.37,
    )


def test_smithfield_kinston_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_kinston",
        "https://smithfieldgrain.com/cashbidssingle-1671",
        "Kinston",
        "bushel_smithfield_kinston_sample.html",
        ["Corn", "Soybeans", "Wheat"],
        4.45,
    )


def test_smithfield_lagrange_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_lagrange",
        "https://smithfieldgrain.com/cashbidssingle-1672",
        "LaGrange",
        "bushel_smithfield_lagrange_sample.html",
        ["Corn", "Soybeans", "Wheat"],
        4.39,
    )


def test_smithfield_morgans_corner_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_morgans_corner",
        "https://smithfieldgrain.com/cashbidssingle-1673",
        "Morgans Corner",
        "bushel_smithfield_morgans_corner_sample.html",
        ["Soybeans", "Wheat"],
        11.60,
    )


def test_smithfield_mount_olive_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_mount_olive",
        "https://smithfieldgrain.com/cashbidssingle-1674",
        "Mount Olive",
        "bushel_smithfield_mount_olive_sample.html",
        ["Corn", "Soybeans", "Wheat"],
        4.43,
    )
