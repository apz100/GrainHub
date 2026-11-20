"""Homeland Grain tests (night queue, 2026-11-20).

Homeland Grain (Norwich, ON) was a catalogue lead with no adapter.
One polite GET of https://www.homelandgrain.com/cash-bids
(GrainHub-Research/1.0) returned 200 with a standard 7-column
``.cbmod`` Bushel widget — 13 live rows: corn 3, soybeans 3,
soybeans delivered Hamilton 1, soft red winter wheat 3, soft red
wheat on-farm pick-up 3 — and the generic ``bushel_source`` parser
handled it with no changes, so Homeland is now a verified
``BUSHEL_SITES`` entry with a ``fetch_homeland()`` wrapper, a
``homeland`` registry adapter and a ``[sources]`` toggle.

The fixture is synthetic: same widget shape as the live page,
invented prices. No live fetching inside pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import bushel_source  # noqa: E402
from app.services.source_registry import get_adapter  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_homeland_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("homeland")
    assert site.company == "Homeland Grain"
    assert site.url == "https://www.homelandgrain.com/cash-bids"
    assert site.currency == "CAD"
    assert site.default_location == "Norwich"
    assert site.location_labels == {"Homeland Grain": "Norwich"}
    assert site.verified is True


def test_homeland_adapter_registered() -> None:
    adapter = get_adapter("homeland")
    assert adapter.module == "bushel_source"
    assert adapter.function == "fetch_homeland"
    assert adapter.mode == "direct_dict"


def test_homeland_fixture_parses_all_sections() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_homeland_sample.html"),
        site=bushel_source.get_bushel_site("homeland"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Homeland Grain"
    assert result["location"] == "Norwich"
    assert any(
        "Cash bids for Friday, November 20, 2026" in note
        for note in result["notes"]
    )
    rows = result["rows"]
    assert len(rows) == 7
    by_key = {(r["commodity"], r["delivery_month"]): r for r in rows}

    corn = by_key[("Corn", "2026 Harvest Corn")]
    assert corn["cash_price"] == 5.11
    assert corn["basis"] == 1.11
    assert corn["futures_price"] == 4.00
    assert corn["change"] == 1.00
    assert corn["futures_month"] == "Dec 26 Corn"
    assert corn["last_trade"] == "10:01 AM"
    assert corn["location"] == "Norwich"
    assert corn["currency"] == "CAD"
    assert corn["unit"] == "$/bu"
    assert corn["cash_price_mt"] is None
    assert corn["note"] == ""

    # A futures value with the trailing settlement marker "s" still
    # parses to its number (the live page publishes e.g. "11.4500s").
    soy28 = by_key[("Soybeans", "2028 Harvest Soybeans")]
    assert soy28["futures_price"] == 11.00
    assert soy28["cash_price"] == 13.99

    # Delivery-variant sections keep their qualifier in the commodity
    # label; the widget location stays the elevator town.
    delivered = by_key[("Soybeans - Delivered Hamilton", "2027 Harvest Hamilton")]
    assert delivered["cash_price"] == 15.55
    assert delivered["basis"] == 3.55
    assert delivered["location"] == "Norwich"

    pickup = by_key[("Soft Red Wheat - On Farm Pick-up", "Jan/Feb/Mar 2027")]
    assert pickup["cash_price"] == 6.22
    assert pickup["futures_month"] == "Mar 27 Wheat"


def test_homeland_page_without_widget_is_unsupported() -> None:
    result = bushel_source.parse_bushel_html(
        "<html><body><p>No bids here.</p></body></html>",
        site=bushel_source.get_bushel_site("homeland"),
    )
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_fetch_homeland_uses_registered_site() -> None:
    with patch.object(
        bushel_source,
        "fetch_bushel_html",
        return_value=_read("bushel_homeland_sample.html"),
    ) as fetch:
        result = bushel_source.fetch_homeland()
    fetch.assert_called_once_with("https://www.homelandgrain.com/cash-bids")
    assert result["status"] == "ok"
    assert len(result["rows"]) == 7
