"""Tests for the LAC source (Cycle 3: base URL moved to the live domain).

Parsing tests run against a saved synthetic fixture in tests/fixtures/
— no live fetching inside pytest. The fixture values are invented
test data, not live prices.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import lac_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_lac_base_url_is_live_domain() -> None:
    assert lac_source.LAC_BASE_URL == "https://www.londonag-dtn.com/index.cfm"
    assert "dtn.londonag.com" not in lac_source.LAC_BASE_URL


def test_lac_default_params_unchanged() -> None:
    assert lac_source.DEFAULT_PARAMS == {
        "show": "11",
        "mid": "3",
        "layout": "19",
        "cmid": "all",
    }


def test_lac_parse_rendered_table() -> None:
    html = (FIXTURES / "lac_sample.html").read_text(encoding="utf-8")
    df = lac_source.parse_lac_html(html, "LAC - Testville")
    assert not df.empty
    assert len(df) == 3
    assert set(df["Location"]) == {"LAC - Testville"}
    assert set(df["Name"]) == {"SOYBEANS", "CORN"}
    soy = df[df["Name"] == "SOYBEANS"].iloc[0]
    assert float(soy["Bushel Cash Price"]) == 15.01
    assert float(soy["Basis"]) == 3.50
    assert float(soy["MT Cash Price"]) == 551.11
    assert soy["Delivery"] == "Nov 2026"


def test_lac_parse_empty_html_returns_empty_frame() -> None:
    df = lac_source.parse_lac_html("<html><body>no tables</body></html>", "LAC - Nowhere")
    assert df.empty
