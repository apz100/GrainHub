"""Per-location Bushel probes (Cycle 14).

Skyland 2763 / 2766 / 2770 / 2771 / 2778 / 3370 / 3621 — the last
seven picker IDs, completing the 14-location sweep (2730 in Cycle
12; 2731 / 2734 / 2740 / 2742 / 2754 / 2761 in Cycle 13): each
serves a standard wrapped 7-column Bushel .cbmod widget — the FAC
shape, not Wheaton Grain's tabbed variant — parsed by the existing
generic parser with no changes. Verified live 2026-11-19, one
polite GET each.

Skyland: every page carries Corn 2 + Red Wheat 2; Milo is 1 except
on 3370 (2 — the first Skyland page with two Milo rows); White
Wheat appears on 2763 / 2771 / 2778. 3370's location h2 carries
", KS" and is mapped to the town name, as with Smithfield's
", NC" entries (Cycle 13). 3370 and 3621 carry widget headers
dated Nov 18, 2026 — a day older than the other Cycle 14 pages
(Nov 19), like Chadbourn in Cycle 13.

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

# ---------------------------------------------------------------------------
# Skyland — Satanta - Ryus (2763)
# ---------------------------------------------------------------------------


def test_skyland_2763_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2763")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2763"
    assert site.currency == "USD"
    assert site.default_location == "Satanta - Ryus"
    assert site.verified is True


def test_skyland_2763_fixture_parses_six_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2763_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2763"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Satanta - Ryus"
    rows = result["rows"]
    assert len(rows) == 6
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
        "White Wheat",
    ]
    assert rows[0]["cash_price"] == 4.31
    assert rows[2]["cash_price"] == 3.95
    assert rows[5]["cash_price"] == 6.02
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2763_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2763_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2763()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2763"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 6
    assert result["rows"][0]["location"] == "Satanta - Ryus"

# ---------------------------------------------------------------------------
# Skyland — Spearman - Gruver - Texline (2766)
# ---------------------------------------------------------------------------


def test_skyland_2766_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2766")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2766"
    assert site.currency == "USD"
    assert site.default_location == "Spearman - Gruver - Texline"
    assert site.verified is True


def test_skyland_2766_fixture_parses_five_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2766_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2766"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Spearman - Gruver - Texline"
    rows = result["rows"]
    assert len(rows) == 5
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
    ]
    assert rows[0]["cash_price"] == 4.27
    assert rows[2]["cash_price"] == 3.91
    assert rows[4]["cash_price"] == 5.87
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2766_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2766_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2766()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2766"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 5
    assert result["rows"][0]["location"] == "Spearman - Gruver - Texline"

# ---------------------------------------------------------------------------
# Skyland — Sunray Area (2770)
# ---------------------------------------------------------------------------


def test_skyland_2770_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2770")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2770"
    assert site.currency == "USD"
    assert site.default_location == "Sunray Area"
    assert site.verified is True


def test_skyland_2770_fixture_parses_five_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2770_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2770"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Sunray Area"
    rows = result["rows"]
    assert len(rows) == 5
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
    ]
    assert rows[0]["cash_price"] == 4.29
    assert rows[2]["cash_price"] == 3.93
    assert rows[4]["cash_price"] == 5.89
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2770_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2770_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2770()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2770"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 5
    assert result["rows"][0]["location"] == "Sunray Area"

# ---------------------------------------------------------------------------
# Skyland — Kendall - Midway - Lydia (2771)
# ---------------------------------------------------------------------------


def test_skyland_2771_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2771")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2771"
    assert site.currency == "USD"
    assert site.default_location == "Kendall - Midway - Lydia"
    assert site.verified is True


def test_skyland_2771_fixture_parses_six_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2771_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2771"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Kendall - Midway - Lydia"
    rows = result["rows"]
    assert len(rows) == 6
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
        "White Wheat",
    ]
    assert rows[0]["cash_price"] == 4.33
    assert rows[2]["cash_price"] == 3.97
    assert rows[5]["cash_price"] == 6.04
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2771_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2771_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2771()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2771"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 6
    assert result["rows"][0]["location"] == "Kendall - Midway - Lydia"

# ---------------------------------------------------------------------------
# Skyland — Buckeye - Syracuse (2778)
# ---------------------------------------------------------------------------


def test_skyland_2778_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_2778")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-2778"
    assert site.currency == "USD"
    assert site.default_location == "Buckeye - Syracuse"
    assert site.verified is True


def test_skyland_2778_fixture_parses_six_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_2778_sample.html"),
        site=bushel_source.get_bushel_site("skyland_2778"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Buckeye - Syracuse"
    rows = result["rows"]
    assert len(rows) == 6
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
        "White Wheat",
    ]
    assert rows[0]["cash_price"] == 4.35
    assert rows[2]["cash_price"] == 3.99
    assert rows[5]["cash_price"] == 6.06
    assert all(r["currency"] == "USD" for r in rows)
    assert any("Cash bids for" in n for n in result["notes"])


def test_fetch_skyland_2778_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_2778_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_2778()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-2778"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 6
    assert result["rows"][0]["location"] == "Buckeye - Syracuse"

# ---------------------------------------------------------------------------
# Skyland — Hugoton (3370)
# ---------------------------------------------------------------------------


def test_skyland_3370_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_3370")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-3370"
    assert site.currency == "USD"
    assert site.default_location == "Hugoton"
    assert site.verified is True


def test_skyland_3370_fixture_parses_six_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_3370_sample.html"),
        site=bushel_source.get_bushel_site("skyland_3370"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Hugoton"
    rows = result["rows"]
    assert len(rows) == 6
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Milo",
        "Red Wheat",
        "Red Wheat",
    ]
    assert rows[0]["cash_price"] == 4.37
    assert rows[2]["cash_price"] == 4.01
    assert rows[5]["cash_price"] == 5.97
    assert all(r["currency"] == "USD" for r in rows)
    # The live page's location h2 is "Hugoton, KS"; the registry
    # entry maps it to the town name.
    assert rows[0]["location"] == "Hugoton"
    # 3370 is the first Skyland page with two Milo rows.
    assert rows[3]["commodity"] == "Milo"
    assert rows[3]["cash_price"] == 4.11
    # The live widget header is dated Nov 18, 2026 — a day older
    # than the other Cycle 14 pages (Nov 19).
    assert any("November 18, 2026" in n for n in result["notes"])


def test_fetch_skyland_3370_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_3370_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_3370()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-3370"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 6
    assert result["rows"][0]["location"] == "Hugoton"

# ---------------------------------------------------------------------------
# Skyland — Vilas - Walsh (3621)
# ---------------------------------------------------------------------------


def test_skyland_3621_registry_entry_is_verified() -> None:
    site = bushel_source.get_bushel_site("skyland_3621")
    assert site.company == "Skyland Grain"
    assert site.url == "https://www.skylandgrain.com/cashbidssingle-3621"
    assert site.currency == "USD"
    assert site.default_location == "Vilas - Walsh"
    assert site.verified is True


def test_skyland_3621_fixture_parses_five_rows() -> None:
    result = bushel_source.parse_bushel_html(
        _read("bushel_skyland_3621_sample.html"),
        site=bushel_source.get_bushel_site("skyland_3621"),
    )
    assert result["status"] == "ok"
    assert result["company"] == "Skyland Grain"
    assert result["location"] == "Vilas - Walsh"
    rows = result["rows"]
    assert len(rows) == 5
    assert [r["commodity"] for r in rows] == [
        "Corn",
        "Corn",
        "Milo",
        "Red Wheat",
        "Red Wheat",
    ]
    assert rows[0]["cash_price"] == 4.39
    assert rows[2]["cash_price"] == 4.03
    assert rows[4]["cash_price"] == 5.99
    assert all(r["currency"] == "USD" for r in rows)
    # The live widget header is dated Nov 18, 2026 — a day older
    # than the other Cycle 14 pages (Nov 19).
    assert any("November 18, 2026" in n for n in result["notes"])


def test_fetch_skyland_3621_uses_verified_registry_entry() -> None:
    fixture = _read("bushel_skyland_3621_sample.html")
    with patch.object(
        bushel_source, "fetch_bushel_html", return_value=fixture
    ) as fetch_html:
        result = bushel_source.fetch_skyland_3621()
    fetch_html.assert_called_once_with(
        "https://www.skylandgrain.com/cashbidssingle-3621"
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 5
    assert result["rows"][0]["location"] == "Vilas - Walsh"

