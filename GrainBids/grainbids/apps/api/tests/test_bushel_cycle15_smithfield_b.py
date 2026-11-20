"""Per-location Bushel probes (Cycle 15, batch B).

Smithfield 1683 (Creswell), 1684 (Warsaw), 1685 (Harpster),
1686 (Morral), 1687 (Darlington), 1688 (Lake City): each serves a
standard wrapped 7-column Bushel .cbmod widget — the FAC shape,
not Wheaton Grain's tabbed variant — parsed by the existing
generic parser with no changes. Verified live 2026-11-19, one
polite GET each. The list page itself was recovered from the saved
Cycle 11 page (/tmp/cycle11/smithfield_fccp.html), so no GET was
spent re-fetching it; the 6 probes are the only GETs this task.

Creswell carries 2 Corn rows; Warsaw carries Corn + Wheat;
Harpster, Morral, Darlington and Lake City are thin 1-row pages
(Corn for Harpster, Soybeans for the other three). Location h2s
carry the state (", NC", ", OH", ", SC") and are mapped to the
town name, as with Bentonville (Cycle 12) — except Harpster,
whose live h2 is bare "Harpster" with no state suffix. All six
widget headers are dated Thursday, November 19, 2026 (fresh —
no Chadbourn-style lag).

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


def test_smithfield_creswell_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_creswell",
        "https://smithfieldgrain.com/cashbidssingle-1683",
        "Creswell",
        "bushel_smithfield_creswell_sample.html",
        ["Corn", "Corn"],
        4.52,
    )


def test_smithfield_warsaw_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_warsaw",
        "https://smithfieldgrain.com/cashbidssingle-1684",
        "Warsaw",
        "bushel_smithfield_warsaw_sample.html",
        ["Corn", "Wheat"],
        4.48,
    )


def test_smithfield_harpster_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_harpster",
        "https://smithfieldgrain.com/cashbidssingle-1685",
        "Harpster",
        "bushel_smithfield_harpster_sample.html",
        ["Corn"],
        4.63,
    )


def test_smithfield_morral_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_morral",
        "https://smithfieldgrain.com/cashbidssingle-1686",
        "Morral",
        "bushel_smithfield_morral_sample.html",
        ["Soybeans"],
        11.42,
    )


def test_smithfield_darlington_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_darlington",
        "https://smithfieldgrain.com/cashbidssingle-1687",
        "Darlington",
        "bushel_smithfield_darlington_sample.html",
        ["Soybeans"],
        11.55,
    )


def test_smithfield_lake_city_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_lake_city",
        "https://smithfieldgrain.com/cashbidssingle-1688",
        "Lake City",
        "bushel_smithfield_lake_city_sample.html",
        ["Soybeans"],
        11.38,
    )
