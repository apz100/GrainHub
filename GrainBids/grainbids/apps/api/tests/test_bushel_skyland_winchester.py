"""Skyland Grain + Winchester Ag tests (Cycle 11).

Skyland: the canonical /cashbidssingle- URL (trailing dash, empty ID)
serves a static 7-column Bushel .cbmod widget for the default location
("Cunningham Area") alongside a 14-location picker — 6 rows (Corn 2,
Milo 1, Red Wheat 2, Soybeans 1). Verified live 2026-11-19 by the
coordinator's own re-check (the Cycle 11 sweep worker had reported no
widget; that was wrong — the saved HTML and a fresh GET both parse ok).

Winchester: the Wheaton Grain embed target /cashbidssingle-3439?embed=y
serves a standard wrapped 7-column .cbmod widget — 10 rows (Corn 5 +
Soybeans 5, Winchester). Verified live 2026-11-19 (Cycle 11 sweep).

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


def test_skyland_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-"
    assert site.currency == "USD"
    assert site.default_location == "Cunningham Area"
    assert site.verified is True


def test_skyland_fixture_parses_six_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_sample.html"),
        site=bushel_source.get_bushel_site("skyland"),
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


def test_fetch_skyland_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 6
    assert result["rows"][0]["location"] == "Cunningham Area"


def test_winchester_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("winchester")
    assert site.company == "Winchester Ag"
    assert site.url == "https://www.wheatongrain.com/cashbidssingle-3439?embed=y"
    assert site.currency == "USD"
    assert site.default_location == "Winchester"
    assert site.verified is True


def test_winchester_fixture_parses_ten_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_winchester_sample.html"),
        site=bushel_source.get_bushel_site("winchester"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Winchester Ag"
    assert result["location"] == "Winchester"
    rows = result["rows"]
    assert len(rows) == 10
    assert len([r for r in rows if r["commodity"] == "Corn"]) == 5
    assert len([r for r in rows if r["commodity"] == "Soybeans"]) == 5
    assert rows[0]["cash_price"] == 4.10
    assert rows[5]["cash_price"] == 11.10
    assert all(r["currency"] == "USD" for r in rows)


def test_fetch_winchester_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_winchester_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_winchester()
    fetch_html.assert_called_once_with(
        "https://www.wheatongrain.com/cashbidssingle-3439?embed=y"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 10
    assert result["rows"][0]["location"] == "Winchester"
