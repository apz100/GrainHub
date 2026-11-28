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


def test_extract_location_options_from_rendered_page() -> None:
    """Regression: the static-HTML dropdown fetch finds zero options
    (the DTN page populates the <select> client-side), which failed
    LAC in the first scheduled poll ("Parsed zero LAC locations from
    dropdown"). The rendered-page path reads the same options from
    the live DOM. Exercised here with a fixture page — no network.
    """
    from playwright.sync_api import sync_playwright

    html = """<html><body><form><select name="Location">
    <option value="">Select a Location</option>
    <option value="12">London</option>
    <option value="34">St. Thomas</option>
    </select></form></body></html>"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        options = lac_source._extract_location_options(page)  # noqa: SLF001
        browser.close()
    assert options == {"12": "London", "34": "St. Thomas"}


def test_extract_location_options_no_locations_listed() -> None:
    """Regression (run 46103946452): the DTN backend answered the
    locations AJAX with a single placeholder option — "No Locations
    Listed", value "0" — verified live 2026-11-28, twice, with a
    session, and theLocation pages render no bid tables either. The
    old code would have treated "0" as a real location and fetched
    nothing for it; it now fails loudly with the actual cause.
    Exercised here with a fixture page — no network.
    """
    import pytest
    from playwright.sync_api import sync_playwright

    html = """<html><body><form><select name="Location">
    <option value="0">No Locations Listed</option>
    </select></form></body></html>"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        with pytest.raises(RuntimeError, match="lists no locations"):
            lac_source._extract_location_options(page)  # noqa: SLF001
        browser.close()
