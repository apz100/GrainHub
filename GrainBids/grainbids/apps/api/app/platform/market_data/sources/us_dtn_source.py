# us_dtn_source.py
"""
Generic scraper for US grain elevators using the DTN CashBidTable widget.

These sites embed a widget configured like:
    const tableOptions = {
        targetID: "target",
        companyID: 22641,
        ...
    };
    CashBidTable(tableOptions);

The widget renders asynchronously via JavaScript, so Playwright is required.
After rendering, the widget produces an HTML table inside #target (or similar)
which we extract with BeautifulSoup.

Usage (called by GrainBidder.py via the [[us.elevators]] config):
    fetch_us_dtn(url, company_name, playwright) -> pd.DataFrame
"""

from __future__ import annotations

import re
import time
from io import StringIO
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PWTimeout

_BU_PER_MT = {
    "corn":      39.3683,
    "soybeans":  36.7437,
    "soybean":   36.7437,
    "wheat":     36.7437,
    "milo":      39.3683,
    "sorghum":   39.3683,
    "ethanol":   39.3683,  # ethanol plants use corn
}

_HEADERS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

# Column name normalisation: maps common DTN table header variants → internal names
_COL_MAP = {
    "commodity":      "Name",
    "name":           "Name",
    "grain":          "Name",
    "location":       "Sub-Location",
    "elevator":       "Sub-Location",
    "site":           "Sub-Location",
    "delivery":       "Delivery",
    "delivery start": "Delivery",
    "delivery end":   "Delivery End",
    "futures":        "Futures Price",
    "futures price":  "Futures Price",
    "futures month":  "Futures Month",
    "month":          "Futures Month",
    "contract":       "Futures Month",
    "change":         "Change",
    "basis":          "Basis",
    "cash":           "Bushel Cash Price",
    "cash price":     "Bushel Cash Price",
    "cash bid":       "Bushel Cash Price",
    "price":          "Bushel Cash Price",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to internal standard names using _COL_MAP."""
    rename = {}
    for col in df.columns:
        key = col.strip().lower().rstrip("*").strip()
        if key in _COL_MAP:
            rename[col] = _COL_MAP[key]
    return df.rename(columns=rename)


def _parse_cash_table(html: str, company_name: str) -> pd.DataFrame:
    """Extract all bid tables from rendered HTML and return a normalised DataFrame."""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        return pd.DataFrame()

    all_rows: list[pd.DataFrame] = []
    for tbl in tables:
        try:
            df = pd.read_html(StringIO(str(tbl)), flavor="lxml")[0]
        except Exception:
            continue
        if df.empty or len(df.columns) < 3:
            continue
        df = df.dropna(how="all").reset_index(drop=True)
        df = _normalize_columns(df)
        all_rows.append(df)

    if not all_rows:
        return pd.DataFrame()

    combined = pd.concat(all_rows, ignore_index=True)

    # Ensure required columns exist
    for col in ["Name", "Delivery", "Delivery End", "Futures Month",
                "Futures Price", "Change", "Basis", "Bushel Cash Price"]:
        if col not in combined.columns:
            combined[col] = ""

    combined["Location"] = company_name

    # Attempt MT cash price from Bushel Cash Price if not present
    if "MT Cash Price" not in combined.columns:
        def _to_mt(row: pd.Series) -> str:
            try:
                price_str = str(row.get("Bushel Cash Price", "")).replace("$", "").strip()
                price_bu  = float(price_str)
                commodity = str(row.get("Name", "")).lower()
                bpu = _BU_PER_MT.get(commodity, 39.3683)
                return str(round(price_bu * bpu, 2))
            except Exception:
                return ""
        combined["MT Cash Price"] = combined.apply(_to_mt, axis=1)

    # Reorder to standard column set
    keep = [c for c in [
        "Location", "Name", "Delivery", "Delivery End",
        "Futures Month", "Futures Price", "Change", "Basis",
        "Bushel Cash Price", "MT Cash Price",
    ] if c in combined.columns]
    return combined[keep]


def fetch_us_dtn(url: str, company_name: str, playwright) -> pd.DataFrame:
    """
    Scrape a US elevator page powered by the DTN CashBidTable widget.

    Args:
        url:          Cash bids page URL
        company_name: Display name for Location column
        playwright:   Playwright instance from sync_playwright context

    Returns:
        Normalised DataFrame.
    """
    if playwright is None:
        # Cycle 20: registry adapters call with no browser (the registry
        # calls fetch_fn() with no arguments and this module must not
        # launch Playwright). The DTN CashBidTable widget renders via
        # JavaScript, so without a render there is nothing to parse.
        # Return empty honestly — never a fake row. A Playwright render
        # check is a later cycle's work.
        print(
            f"[US-DTN WARN] {company_name}: no browser render available — "
            "DTN widget is JS-rendered, returning no rows"
        )
        return pd.DataFrame()

    try:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent=_HEADERS_UA)
        page    = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=60_000)
        except PWTimeout:
            # networkidle can time out on heavy pages; proceed anyway
            pass

        # Wait for the DTN widget to render — it injects into a #target div
        # or any div containing a table with bid data
        rendered = False
        for selector in ["#target table", ".cash-bid-table table", "table"]:
            try:
                page.wait_for_selector(selector, timeout=15_000)
                rendered = True
                break
            except PWTimeout:
                continue

        if not rendered:
            print(f"[US-DTN WARN] {company_name}: table did not appear after waiting")

        # Give any pending JS renders a moment to settle
        page.wait_for_timeout(3_000)
        html = page.content()

        context.close()
        browser.close()

        df = _parse_cash_table(html, company_name)
        if df.empty:
            print(f"[US-DTN WARN] {company_name}: no bid table found in rendered page")
            return pd.DataFrame()

        print(f"[US-DTN OK] {company_name}: {len(df)} rows")
        return df

    except Exception as e:
        print(f"[US-DTN ERR] {company_name}: {e}")
        return pd.DataFrame()


# ─── URL-bound registry adapters (Cycle 20) ────────────────────────────────
# Zero-argument wrappers over fetch_us_dtn() for the enabled `dtn`
# entries in us_elevators_urls.toml. The platform registry
# (app/services/source_registry.py) calls fetch_fn() with no arguments,
# so each entry gets its own bound wrapper; the coordinator wires them
# as SourceAdapter rows (mode "direct" — these return a DataFrame).
#
# All 13 entries are JS-only: the DTN widget (classic CashBidTable,
# modern content-services widget, or aghost loader) renders in the
# browser and no static bid rows exist in the page HTML (Cycle 6
# sweep; Sunrise confirmed classic DTN in Cycle 10). The registry
# adapter path has no Playwright render, so every wrapper below calls
# the generic with playwright=None and the generic returns an empty
# DataFrame honestly — never a fake row, and no Playwright is ever
# launched from this module's adapter path. The [sources] toggles for
# these keys are therefore false until a Playwright render check in a
# later cycle proves a page collectable. Live verification of the
# wrappers is a later cycle's GET-probe work; nothing here fetches
# a page.
#
# One exception to the family label: Frontier Coop's widget is
# StoneX, not DTN (Cycle 6/8/9) — the DTN generic path returns empty
# for it too, and a StoneX collector is a separate later-cycle item.

US_DTN_SITES: dict[str, tuple[str, str]] = {
    # key: (company_name, url) — mirrors the enabled `dtn` entries
    # in us_elevators_urls.toml.
    "ag_partners": ("Ag Partners", "https://agpartners.net/cash-bids"),
    "al_corn": ("Al-Corn", "https://www.al-corn.com/cash-bids"),
    "allied_cooperative": ("Allied Cooperative", "https://www.allied.coop/grain/cash-bids"),
    "aurora_coop": ("Aurora Coop", "https://auroracoop.com/markets"),
    "cfs": ("CFS", "https://www.cfscoop.com/products-services/grain"),
    "elite_octane": ("Elite Octane", "https://www.eliteoctane.net/cash-bids"),
    "frontier_coop": ("Frontier Coop", "https://www.frontiercooperative.com/grain/cash-bids"),
    "green_plains": ("Green Plains", "https://gpreinc.com/corn-bids/"),
    "kanza_coop": ("Kanza Coop", "https://www.kanzacoop.com/services/grain"),
    "sunrise": ("Sunrise", "https://www.sunriseco-op.com"),
    "brubaker_grain": ("Brubaker Grain", "https://dtn.brubakergrain.com/"),
    "hoffman_ag": ("Hoffman Ag", "https://dtn.hoffmanag.com/"),
    "wilton_farmers_union_elevator": ("Wilton Farmers Union Elevator", "https://www.wiltonfarmerselevator.com/index.cfm?show=11&mid=5&theLocation=1&cmid=all&layout=19"),
}


def fetch_ag_partners() -> pd.DataFrame:
    """Fetch Ag Partners via the generic DTN collector.

    JS-only: modern DTN widget (content-services), no static bid
    rows (Cycles 6/8). No browser render on the adapter path, so
    the generic returns an empty DataFrame honestly.
    """
    name, url = US_DTN_SITES["ag_partners"]
    return fetch_us_dtn(url, name, None)


def fetch_al_corn() -> pd.DataFrame:
    """Fetch Al-Corn via the generic DTN collector.

    JS-only: classic DTN — <div id="target"> + CashBidTable,
    companyID 239483 (Cycle 6). Exact fit for the generic once
    rendered; no browser render on the adapter path, so the generic
    returns an empty DataFrame honestly.
    """
    name, url = US_DTN_SITES["al_corn"]
    return fetch_us_dtn(url, name, None)


def fetch_allied_cooperative() -> pd.DataFrame:
    """Fetch Allied Cooperative via the generic DTN collector.

    JS-only: modern DTN widget (content-services), no static bid
    rows (Cycle 6). No browser render on the adapter path, so the
    generic returns an empty DataFrame honestly.
    """
    name, url = US_DTN_SITES["allied_cooperative"]
    return fetch_us_dtn(url, name, None)


def fetch_aurora_coop() -> pd.DataFrame:
    """Fetch Aurora Coop via the generic DTN collector.

    JS-only: modern DTN widget (content-services), no static bid
    rows (Cycle 6). No browser render on the adapter path, so the
    generic returns an empty DataFrame honestly.
    """
    name, url = US_DTN_SITES["aurora_coop"]
    return fetch_us_dtn(url, name, None)


def fetch_cfs() -> pd.DataFrame:
    """Fetch CFS via the generic DTN collector.

    JS-only: aghost DTN widget (DtnCashbidDetailsScript.js) with a
    location-cookie flow; the only static table is a futures quotes
    table, not bids (Cycle 6). No browser render on the adapter
    path, so the generic returns an empty DataFrame honestly.
    """
    name, url = US_DTN_SITES["cfs"]
    return fetch_us_dtn(url, name, None)


def fetch_elite_octane() -> pd.DataFrame:
    """Fetch Elite Octane via the generic DTN collector.

    JS-only: <div id="target"> + CIHedging CashBidWidget.js loader,
    no inline tableOptions (Cycle 6). No browser render on the
    adapter path, so the generic returns an empty DataFrame honestly.
    """
    name, url = US_DTN_SITES["elite_octane"]
    return fetch_us_dtn(url, name, None)


def fetch_frontier_coop() -> pd.DataFrame:
    """Fetch Frontier Coop via the generic DTN collector.

    NOT a DTN widget: the page carries a StoneX widget
    (StonexCashbidScript.js) plus an empty inline JSON model
    (Cycles 6/8/9) — the DTN generic path returns empty for it, as
    it does for every entry here. A StoneX collector is a separate
    later-cycle item, not this adapter.
    """
    name, url = US_DTN_SITES["frontier_coop"]
    return fetch_us_dtn(url, name, None)


def fetch_green_plains() -> pd.DataFrame:
    """Fetch Green Plains via the generic DTN collector.

    JS-only: modern DTN widget (content-services), no static bid
    rows (Cycle 6). No browser render on the adapter path, so the
    generic returns an empty DataFrame honestly.
    """
    name, url = US_DTN_SITES["green_plains"]
    return fetch_us_dtn(url, name, None)


def fetch_kanza_coop() -> pd.DataFrame:
    """Fetch Kanza Coop via the generic DTN collector.

    JS-only: ATLAS DTN shell (/dtncashbidwidget/bindlocation),
    no static bid rows (Cycle 6). No browser render on the adapter
    path, so the generic returns an empty DataFrame honestly.
    """
    name, url = US_DTN_SITES["kanza_coop"]
    return fetch_us_dtn(url, name, None)


def fetch_sunrise() -> pd.DataFrame:
    """Fetch Sunrise via the generic DTN collector.

    JS-only: classic DTN — <div id="target"> + CashBidTable,
    companyID 23043, CIHedging CashBidWidget.js, ATLAS DTN shell
    (Cycle 10). Exact fit for the generic once rendered; no browser
    render on the adapter path, so the generic returns an empty
    DataFrame honestly.
    """
    name, url = US_DTN_SITES["sunrise"]
    return fetch_us_dtn(url, name, None)


def fetch_brubaker_grain() -> pd.DataFrame:
    """Fetch Brubaker Grain via the generic DTN collector.

    JS-only: DTN-subdomain host, widget reference confirmed in HTML
    with live bid rows visible only in the search index (Cycle 1);
    rows still to be confirmed in Playwright. No browser render on
    the adapter path, so the generic returns an empty DataFrame
    honestly.
    """
    name, url = US_DTN_SITES["brubaker_grain"]
    return fetch_us_dtn(url, name, None)


def fetch_hoffman_ag() -> pd.DataFrame:
    """Fetch Hoffman Ag via the generic DTN collector.

    JS-only: DTN-subdomain host, widget reference confirmed in HTML
    with live bid rows visible only in the search index (Cycle 1);
    rows still to be confirmed in Playwright. No browser render on
    the adapter path, so the generic returns an empty DataFrame
    honestly.
    """
    name, url = US_DTN_SITES["hoffman_ag"]
    return fetch_us_dtn(url, name, None)


def fetch_wilton_farmers_union_elevator() -> pd.DataFrame:
    """Fetch Wilton Farmers Union Elevator via the generic DTN collector.

    JS-only: DTN index.cfm page, widget reference confirmed in HTML
    with live bid rows visible only in the search index (Cycle 1);
    rows still to be confirmed in Playwright. No browser render on
    the adapter path, so the generic returns an empty DataFrame
    honestly.
    """
    name, url = US_DTN_SITES["wilton_farmers_union_elevator"]
    return fetch_us_dtn(url, name, None)
