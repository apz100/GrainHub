"""Per-location Bushel probes (Cycle 16, loose ends).

Smithfield 1675 (Raeford), 2067 (Lapaz), 2179 (Hamer): one polite
GET each, 2026-11-19. The location names come from the saved
Cycle 11 list page (/tmp/cycle11/smithfield_fccp.html), so no GET
was spent re-fetching it.

Raeford re-probed STILL EMPTY: HTTP 200 but the page is the
generic site shell with an empty .cbmod widget — no location h2,
no header date, 0 rows parsed (status "empty"), exactly as in
Cycle 15 batch A. It is NOT registered, and no further re-probe
is planned unless the widget shape changes; the test below pins
that (unknown site key + an empty-widget shape parses to
status "empty").

Lapaz and Hamer both parsed cleanly: standard wrapped 7-column
Bushel .cbmod widgets, generic parser, no changes. Lapaz carries
2 Corn rows with a fresh header (Thursday, November 19, 2026);
Hamer is a thin 1-row page (Soybeans) whose header is dated
Wednesday, November 18, 2026 — a day stale, like Chadbourn
(Cycle 13). Location h2s carry the state (", IN", ", SC") and
are mapped to the town name, as with Bentonville (Cycle 12).
With these two, every Smithfield ID on the Cycle 11 list page is
now verified except Raeford (1675).

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

# Minimal synthetic shape of the Raeford page: the generic site
# shell with an empty .cbmod widget — no location h2, no header
# date, no .cbCommodity blocks.
RAEFORD_EMPTY_WIDGET = """<html><body>
<div class="cbmod"></div>
<h2 class="fcControls">Contact Us</h2>
</body></html>"""


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


def test_smithfield_lapaz_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_lapaz",
        "https://smithfieldgrain.com/cashbidssingle-2067",
        "Lapaz",
        "bushel_smithfield_lapaz_sample.html",
        ["Corn", "Corn"],
        4.71,
    )


def test_smithfield_hamer_parses_and_registry_entry_exists() -> None:
    _check_site(
        "smithfield_hamer",
        "https://smithfieldgrain.com/cashbidssingle-2179",
        "Hamer",
        "bushel_smithfield_hamer_sample.html",
        ["Soybeans"],
        11.64,
    )


def test_smithfield_raeford_still_empty_and_not_registered() -> None:
    with pytest.raises(KeyError, match="smithfield_raeford"):
        bushel_source.get_bushel_site("smithfield_raeford")
    result = bushel_source.parse_bushel_html(RAEFORD_EMPTY_WIDGET)
    assert result["status"] == "empty"
    assert result["rows"] == []
    assert result["location"] is None
