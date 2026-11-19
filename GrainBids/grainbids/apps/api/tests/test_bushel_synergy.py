"""Synergy Cooperative tests (Cycle 10 sweep).

One polite GET of https://www.synergycoop.com (2026-11-19,
GrainHub-Research/1.0) returned 200 with a standard 6-column Bushel
``.cbmod`` widget in static HTML — 4 rows (Corn 2 + Soybeans 2,
Cameron) — and the generic ``bushel_source`` parser handled it with
no changes, so Synergy is now a verified ``BUSHEL_SITES`` entry with
a ``fetch_synergy()`` wrapper.

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


def test_synergy_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("synergy")
    assert site.company == "Synergy Cooperative"
    assert site.url == "https://www.synergycoop.com"
    assert site.currency == "USD"
    assert site.default_location == "Cameron"
    assert site.verified is True


def test_synergy_fixture_parses_four_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_synergy_sample.html"),
        site=bushel_source.get_bushel_site("synergy"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Synergy Cooperative"
    assert result["location"] == "Cameron"
    rows = result["rows"]
    assert len(rows) == 4
    corn = rows[0]
    assert corn["commodity"] == "Corn"
    assert corn["delivery_month"] == "New Crop '26"
    assert corn["cash_price"] == 3.60
    assert corn["basis"] == -0.75
    assert corn["futures_price"] == 4.35
    assert corn["change"] == -0.02
    assert corn["futures_month"] == "Dec 26 Corn"
    assert corn["last_trade"] is None
    assert corn["currency"] == "USD"
    assert corn["unit"] == "$/bu"
    assert rows[2]["commodity"] == "Soybeans"
    assert rows[2]["cash_price"] == 10.80
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_synergy_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_synergy_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_synergy()
    fetch_html.assert_called_once_with("https://www.synergycoop.com")
    assert result["status"] == "ok"
    assert len(result["rows"]) == 4
    assert result["rows"][0]["location"] == "Cameron"
