"""Tests for the Hensall collector's DTN-widget wait + table parsing.

The fixture (tests/fixtures/hensall_sample.html) is SYNTHETIC —
invented test data shaped like the live <dtn-table> widget, not a
live capture (the live page only renders in a browser; this sandbox
has no browser egress). No live fetching inside pytest.

Regression: run 46103946452 failed Hensall with "no dtn-table
elements found" because the adapter waited a blind 5 s after
domcontentloaded. The DTN widget JS (920 KB) plus its api.dtn.com
data fetch can take ~20 s on a cold gateway, so the adapter now
waits for the <dtn-table> element itself (60 s).
"""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import hensall_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _fixture_table_html() -> str:
    html = (FIXTURES / "hensall_sample.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    tbl = soup.find("table")
    assert tbl is not None
    return str(tbl)


def test_table_parses_to_rows():
    df = hensall_source._html_table_to_df(_fixture_table_html())  # noqa: SLF001
    assert not df.empty
    assert len(df) == 2  # the all-empty row is skipped
    assert list(df.columns[:3]) == ["LOCATION", "DELIVERY LABEL", "CASH PRICE"]


def test_normalize_maps_documented_columns():
    df_raw = hensall_source._html_table_to_df(_fixture_table_html())  # noqa: SLF001
    df = hensall_source._normalize_hensall_df(df_raw, "Corn")  # noqa: SLF001
    assert len(df) == 2
    assert set(df["Location"]) == {"Hensall"}
    assert set(df["Name"]) == {"Corn"}
    assert list(df["Delivery"]) == ["Dec 2026", "Nov 2027"]
    assert list(df["Bushel Cash Price"]) == ["10.00", "11.00"]
    assert list(df["Basis"]) == ["1.00", "1.50"]
    assert list(df["Futures Month"]) == ["@C26Z", "@C27Z"]
    assert list(df["MT Cash Price"]) == ["393.70", "433.07"]


def test_collect_finds_rendered_dtn_table():
    """_collect_dtn_tables waits for the element and extracts the
    widget name + inner table HTML. Exercised with a fixture page —
    no network."""
    from playwright.sync_api import sync_playwright

    html = (FIXTURES / "hensall_sample.html").read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html)
        items = hensall_source._collect_dtn_tables(page)  # noqa: SLF001
        browser.close()
    assert len(items) == 1
    assert items[0]["name"] == "Corn"
    assert "<table>" in items[0]["html"]
    assert "Dec 2026" in items[0]["html"]


def test_collect_times_out_when_widget_never_renders():
    """A page with no <dtn-table> must raise PWTimeout — proves the
    wait is what gates the collect, not a blind sleep. Short timeout
    so the test stays fast; production uses the 60 s default."""
    import pytest
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import TimeoutError as PWTimeout

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content("<html><body><p>no widget here</p></body></html>")
        with pytest.raises(PWTimeout):
            hensall_source._collect_dtn_tables(page, timeout_ms=1000)  # noqa: SLF001
        browser.close()
