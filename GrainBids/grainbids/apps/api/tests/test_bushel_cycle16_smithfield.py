"""Per-location Bushel probes (Cycle 16).

Smithfield 1689 (Nichols), 1690 (Petersburg), 1691 (Waverly),
2064 (Kinston JCH), 2065 (Jones County), 2066 (Deep Run JCH):
each serves a standard wrapped 7-column Bushel .cbmod widget —
the FAC shape, not Wheaton Grain's tabbed variant — parsed by
the existing generic parser with no changes. Verified live
2026-11-19, one polite GET each. The list page itself was
recovered from the saved Cycle 11 page
(/tmp/cycle11/smithfield_fccp.html), so no GET was spent
re-fetching it; the 6 probes are the only GETs this task.

Nichols is a thin 1-row page (Soybeans); Petersburg carries
Corn + Wheat + 2 Soybeans rows; Waverly is the fattest
Smithfield page yet at 7 rows (Corn 3, Wheat 2, Grain Sorghum
2 — the first Smithfield page to carry Grain Sorghum, published
as "Sorghum" in the widget header and normalized by the parser);
Kinston JCH and Jones County each carry Corn + Wheat +
Soybeans; Deep Run JCH carries Corn + Wheat. Location h2s
carry the state (", SC", ", VA", ", NC") and are mapped to the
town name, as with Bentonville (Cycle 12) — except the two JCH
h2s, "Kinston JCH, NC" and "Deep Run JCH, NC", which are
mapped to "Kinston JCH" / "Deep Run JCH" so the 2064 target
stays distinct from smithfield_kinston (1671, Kinston
Elevator). All six widget headers are dated Thursday,
November 19, 2026 (fresh — no Chadbourn-style lag). No empty
widget in this batch, so there is no negative test here (the
Raeford empty-widget case is covered in
test_bushel_cycle15_smithfield.py).

Fixtures below are synthetic: same widget shapes as the live
pages, invented prices. No live fetching inside pytest.
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


def test_smithfield_nichols_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_nichols",
        "https://smithfieldgrain.com/cashbidssingle-1689",
        "Nichols",
        "bushel_smithfield_nichols_sample.html",
        ["Soybeans"],
        11.47,
    )


def test_smithfield_petersburg_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_petersburg",
        "https://smithfieldgrain.com/cashbidssingle-1690",
        "Petersburg",
        "bushel_smithfield_petersburg_sample.html",
        ["Corn", "Wheat", "Soybeans", "Soybeans"],
        4.41,
    )


def test_smithfield_waverly_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_waverly",
        "https://smithfieldgrain.com/cashbidssingle-1691",
        "Waverly",
        "bushel_smithfield_waverly_sample.html",
        ["Corn", "Corn", "Corn", "Wheat", "Wheat", "Grain Sorghum", "Grain Sorghum"],
        4.39,
    )


def test_smithfield_kinston_jch_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_kinston_jch",
        "https://smithfieldgrain.com/cashbidssingle-2064",
        "Kinston JCH",
        "bushel_smithfield_kinston_jch_sample.html",
        ["Corn", "Wheat", "Soybeans"],
        4.44,
    )


def test_smithfield_jones_county_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_jones_county",
        "https://smithfieldgrain.com/cashbidssingle-2065",
        "Jones County",
        "bushel_smithfield_jones_county_sample.html",
        ["Corn", "Wheat", "Soybeans"],
        4.50,
    )


def test_smithfield_deep_run_jch_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_deep_run_jch",
        "https://smithfieldgrain.com/cashbidssingle-2066",
        "Deep Run JCH",
        "bushel_smithfield_deep_run_jch_sample.html",
        ["Corn", "Wheat"],
        4.46,
    )
