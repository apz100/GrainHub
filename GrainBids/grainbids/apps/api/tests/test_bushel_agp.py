"""AGP iframe-target tests (Cycle 7).

The AGP cash-bids page (agp.com/grain/bids) embeds a Bushel widget via
``<iframe src="https://agp.o.bushelsites.com/cash-bids">``. One polite
GET of that iframe target (2026-11-19, GrainHub-Research/1.0) returned
200 with a standard 7-column ``.cbmod`` widget — a single location/row
(Chester, NE, Soybeans, Nov 2026) — and the generic
``bushel_source`` parser handled it with no changes, so AGP is now a
verified ``BUSHEL_SITES`` entry with a ``fetch_agp()`` wrapper.

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


def test_agp_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("agp")
    assert site.company == "AGP"
    assert site.url == "https://agp.o.bushelsites.com/cash-bids"
    assert site.currency == "USD"
    assert site.default_location == "Chester"
    assert site.verified is True


def test_agp_fixture_parses_single_soybean_row() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_agp_sample.html"), site=bushel_source.get_bushel_site("agp")
    )
    assert result["status"] == "ok"
    assert result["company"] == "AGP"
    assert result["location"] == "Chester, NE"
    rows = result["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["commodity"] == "Soybeans"
    assert row["delivery_month"] == "Nov 2026"
    assert row["cash_price"] == 10.50
    assert row["basis"] == -0.60
    assert row["futures_price"] == 11.10
    assert row["change"] == -0.02
    assert row["futures_month"] == "Jan 27 Soybeans"
    assert row["last_trade"] == "9:00 AM"
    assert row["currency"] == "USD"
    assert row["unit"] == "$/bu"
    assert row["cash_price_mt"] is None
    assert row["note"] == ""
    assert any("Cash bids as of" in n for n in result["notes"])


def test_fetch_agp_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_agp_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_agp()
    fetch_html.assert_called_once_with("https://agp.o.bushelsites.com/cash-bids")
    assert result["status"] == "ok"
    assert len(result["rows"]) == 1
    assert result["rows"][0]["location"] == "Chester, NE"
