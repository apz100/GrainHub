"""Per-location Bushel probes (Cycle 15 batch A).

Smithfield 1676 (Red Springs), 1678 (Walstonburg), 1679
(Weeksville), 1681 (The Chief Feed Mill), 1682 (Laurinburg Feed
Mill): each serves a standard wrapped 7-column Bushel .cbmod
widget — the FAC shape, not Wheaton Grain's tabbed variant —
parsed by the existing generic parser with no changes. Verified
live 2026-11-19, one polite GET each. The list page itself was
recovered from the saved Cycle 11 page
(/tmp/cycle11/smithfield_fccp.html), so no GET was spent
re-fetching it; the 6 probes are the only GETs this batch.

Red Springs carries 1 row (Soybeans); Walstonburg carries 3 rows
(Corn + Soybeans + Wheat); Weeksville carries 2 rows (Soybeans +
Wheat); The Chief Feed Mill and Laurinburg Feed Mill each carry
2 rows (Corn + Wheat). Location h2s carry ", NC" and are mapped
to the town name, as with Bentonville (Cycle 12) — except 1681,
whose live h2 is "Rose Hill, NC" (the mill's town), mapped to
"Rose Hill". All five widget headers are dated Thursday,
November 19, 2026.

1675 (Raeford Elevator) is NOT registered: HTTP 200, but the
page is the generic site shell with an empty .cbmod widget — no
location h2, no header date, 0 rows parsed (status "empty").
The negative test below guards that.

Fixtures below are synthetic: same widget shapes as the live pages,
invented prices. No live fetching inside pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


def test_smithfield_red_springs_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_red_springs",
        "https://smithfieldgrain.com/cashbidssingle-1676",
        "Red Springs",
        "bushel_smithfield_red_springs_sample.html",
        ["Soybeans"],
        11.55,
    )


def test_smithfield_walstonburg_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_walstonburg",
        "https://smithfieldgrain.com/cashbidssingle-1678",
        "Walstonburg",
        "bushel_smithfield_walstonburg_sample.html",
        ["Corn", "Soybeans", "Wheat"],
        4.47,
    )


def test_smithfield_weeksville_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_weeksville",
        "https://smithfieldgrain.com/cashbidssingle-1679",
        "Weeksville",
        "bushel_smithfield_weeksville_sample.html",
        ["Soybeans", "Wheat"],
        11.58,
    )


def test_smithfield_chief_feed_mill_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_chief_feed_mill",
        "https://smithfieldgrain.com/cashbidssingle-1681",
        "Rose Hill",
        "bushel_smithfield_chief_feed_mill_sample.html",
        ["Corn", "Wheat"],
        4.49,
    )


def test_smithfield_laurinburg_feed_mill_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_laurinburg_feed_mill",
        "https://smithfieldgrain.com/cashbidssingle-1682",
        "Laurinburg Feed Mill",
        "bushel_smithfield_laurinburg_feed_mill_sample.html",
        ["Corn", "Wheat"],
        4.51,
    )


def test_smithfield_raeford_not_registered_empty_widget() -> None:
    """1675 (Raeford) returned 200 with an empty .cbmod widget and
    0 parsed rows, so it has no registry entry; re-probe before
    ever registering it. The inline HTML below mirrors the live
    1675 page shape (generic shell, empty widget, no location h2
    or header date) — no /tmp scratch dependency."""
    with pytest.raises(KeyError):
        bushel_source.get_bushel_site("smithfield_raeford")
    result = bushel_source.parse_bushel_html(
        "<html><body><div class='cbmod'></div></body></html>",
        company="Smithfield Grain",
    )
    assert result["status"] == "empty"
    assert result["rows"] == []
