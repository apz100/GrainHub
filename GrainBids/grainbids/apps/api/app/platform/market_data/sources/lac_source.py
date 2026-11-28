"""
London Agricultural Commodities (LAC) cash bid scraper.

Uses Playwright to let DTN's JavaScript render the page, then reads the
finished <table name="cashbids-data-table"> as text via pandas.read_html.

That way we get the *displayed* numbers:
  Basis, Cash Price, Price / (Tonnes), Basis / (Tonnes)
instead of the internal displayNumber(...) values.
"""

from __future__ import annotations

import re
from typing import Dict

import io
import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Playwright
from urllib.parse import urlencode

LAC_BASE_URL = "https://www.londonag-dtn.com/index.cfm"
# NOTE (Cycle 3, 2026-11-19): old base https://dtn.londonag.com is dead.
# New domain verified live (HTTP 200, "Cash Bid" content, Location
# dropdown present) via one polite GET of
# https://www.londonag-dtn.com/index.cfm?show=11&mid=3&layout=19&cmid=all
# The Location options and bid tables are JS-rendered, so the Playwright
# fetch path is unchanged — only the domain moved.
DEFAULT_PARAMS = {"show": "11", "mid": "3", "layout": "19", "cmid": "all"}

NUM_RE = re.compile(r"[-+]?\d*\.\d+|[-+]?\d+")


def extract_visible_number(val: object) -> str:
    """
    Given a cell like:
      '<!-- displayNumber(-57.3956,4); //-->  14.5425'
    return the LAST numeric literal: '14.5425'.

    If no numbers, return ''.
    """
    if val is None:
        return ""
    text = str(val)
    nums = NUM_RE.findall(text)
    if not nums:
        return ""
    return nums[-1]  # last = what user sees in the table


# ---------------------------------------------------------------------------
# Location dropdown (via requests)
# ---------------------------------------------------------------------------

def _fetch_location_options() -> Dict[str, str]:
    resp = requests.get(LAC_BASE_URL, params=DEFAULT_PARAMS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    select = soup.find("select", attrs={"name": re.compile("Location", re.I)})
    if not select:
        raise RuntimeError("Could not find Location dropdown on LAC DTN page")

    options: Dict[str, str] = {}
    for opt in select.find_all("option"):
        value = (opt.get("value") or "").strip()
        label = opt.get_text(" ", strip=True)
        if value.isdigit() and label:
            options[value] = label

    if not options:
        raise RuntimeError("Parsed zero LAC locations from dropdown")
    return options


def _fetch_location_options_from_page(page) -> Dict[str, str]:
    """Read the Location dropdown from the JS-rendered page.

    Fallback for when the static-HTML path above finds nothing: the
    DTN page now populates the dropdown client-side, so the HTML
    returned by ``requests`` carries an empty <select> and
    ``_fetch_location_options`` raises "Parsed zero LAC locations"
    (verified live 2026-11-28 — the first scheduled poll failed LAC
    on exactly this). The Playwright page has the rendered DOM, so
    the same digit-valued options are readable there. ``page`` is the
    already-open page from ``fetch_lac_all``.
    """
    from urllib.parse import urlencode as _urlencode

    page.goto(f"{LAC_BASE_URL}?{_urlencode(DEFAULT_PARAMS)}", wait_until="domcontentloaded", timeout=30000)
    return _extract_location_options(page)


def _extract_location_options(page) -> Dict[str, str]:
    """Read the Location dropdown options from the current page DOM.

    Split out from ``_fetch_location_options_from_page`` so the
    extraction is testable with a fixture page (``set_content``)
    without a live navigation.
    """
    # The options arrive with the page's JavaScript; wait until at
    # least one digit-valued option exists before reading them.
    # state="attached": <option> elements are never "visible" in
    # Playwright's sense (they live inside a closed <select>), so
    # the default visible wait would time out even when the options
    # are present.
    # Timeout is 60 s (was 30 s): the DTN backend that populates the
    # dropdown took ~10 s on a direct probe 2026-11-28 and was slower
    # still during run 46103946452, where all three attempts timed
    # out at 30 s. Still inside the adapter's 90 s timeout.
    page.wait_for_selector(
        "select[name*='Location' i] option[value]",
        state="attached",
        timeout=60000,
    )
    pairs = page.eval_on_selector_all(
        "select[name*='Location' i] option",
        "els => els.map(e => [e.value.trim(), (e.textContent || '').trim()])",
    )
    options: Dict[str, str] = {}
    for value, label in pairs:
        if value.isdigit() and label:
            options[value] = label
    if not options:
        raise RuntimeError("Parsed zero LAC locations from dropdown (rendered page)")
    # The DTN backend can answer with a single placeholder option
    # ("No Locations Listed", value "0") instead of real locations —
    # verified live 2026-11-28, twice, with a session: the backend
    # currently lists no locations at all, and theLocation pages
    # render no bid tables either. Iterating location "0" would fetch
    # nothing; fail loudly with the actual cause instead.
    if set(options) == {"0"}:
        raise RuntimeError(
            "LAC backend lists no locations (DTN returned 'No Locations Listed')"
        )
    return options


# ---------------------------------------------------------------------------
# Parse a *rendered* LAC HTML page into our canonical DataFrame
# ---------------------------------------------------------------------------

def _parse_lac_dom(html: str, location_name: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table", attrs={"name": "cashbids-data-table"})
    if not tables:
        return pd.DataFrame()

    frames = []

    for tbl in tables:
        # Commodity label just above the table (SOYBEANS, CORN, WHEAT, SRW, etc.)
        label_node = tbl.find_previous(
            lambda tag: tag.name in ["h1", "h2", "h3", "h4", "b", "strong", "font", "span"]
            and tag.get_text(strip=True)
        )
        commodity = label_node.get_text(" ", strip=True).strip() if label_node else "LAC Cash Bid"

        try:
            df_raw = pd.read_html(io.StringIO(str(tbl)))[0]
        except ValueError:
            continue

        # Normalize column labels
        df_raw.columns = [str(c).strip() for c in df_raw.columns]

        # Map DTN headers -> our internal schema
        mapping = {}
        for col in df_raw.columns:
            lc = col.lower()
            if "delivery" in lc:
                mapping[col] = "Delivery"
            elif "month" in lc:
                mapping[col] = "Futures Month"
            elif "futures" in lc:
                mapping[col] = "Futures Price"
            elif "change" in lc:
                mapping[col] = "Change"
            elif "basis" in lc and "tonnes" not in lc:
                mapping[col] = "Basis"
            elif "cash" in lc:
                mapping[col] = "Bushel Cash Price"
            elif "price" in lc and "tonnes" in lc:
                mapping[col] = "MT Cash Price"
            elif "basis" in lc and "tonnes" in lc:
                mapping[col] = "Basis / (Tonnes)"

        df_tmp = df_raw.rename(columns=mapping)

        # Add our extra fields
        df_tmp["Location"] = location_name
        df_tmp["Name"] = commodity

        # Clean numeric columns: keep only the visible value
        for col in ["Basis", "Bushel Cash Price", "MT Cash Price", "Basis / (Tonnes)"]:
            if col in df_tmp.columns:
                df_tmp[col] = df_tmp[col].apply(extract_visible_number)

        # Ensure all expected columns exist
        expected_cols = [
            "Location",
            "Name",
            "Delivery",
            "Futures Month",
            "Futures Price",
            "Change",
            "Basis",
            "Bushel Cash Price",
            "MT Cash Price",
            "Basis / (Tonnes)",
        ]
        for c in expected_cols:
            if c not in df_tmp.columns:
                df_tmp[c] = ""

        df_clean = df_tmp[expected_cols]
        frames.append(df_clean)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    # Excel headers to match the LAC webpage
    df.attrs["web_headers"] = {
        "Location":          "Location",
        "Name":              "Commodity",
        "Delivery":          "Delivery",
        "Futures Month":     "Month",
        "Futures Price":     "Futures",
        "Change":            "Change",
        "Basis":             "Basis",
        "Bushel Cash Price": "Cash Price",
        "MT Cash Price":     "Price / (Tonnes)",
        "Basis / (Tonnes)":  "Basis / (Tonnes)",
    }

    return df


# ---------------------------------------------------------------------------
# Public fetch – via Playwright
# ---------------------------------------------------------------------------

def fetch_lac_all(p: Playwright) -> pd.DataFrame:
    """
    Fetch cash bids for all LAC locations by letting the DTN page render in
    Chromium (Playwright) and then scraping the visible table text.

    Reuses the Playwright instance passed in from grainBidder.py.
    """
    # Fast path first (worked until the DTN page went JS-only for the
    # dropdown): one requests GET. When it finds zero options, fall
    # back to reading the rendered dropdown via the Playwright page
    # instead of failing the whole source.
    locations: Dict[str, str] | None = None
    try:
        locations = _fetch_location_options()
    except RuntimeError as exc:
        if "Parsed zero" not in str(exc):
            raise
    all_rows = []

    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    if locations is None:
        locations = _fetch_location_options_from_page(page)

    for loc_id, loc_name in locations.items():
        params = DEFAULT_PARAMS | {"theLocation": loc_id}
        url = f"{LAC_BASE_URL}?{urlencode(params)}"

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            df_loc = _parse_lac_dom(html, f"LAC - {loc_name}")
            if df_loc is not None and not df_loc.empty:
                all_rows.append(df_loc)
                print(f"[LAC OK] {loc_name}: {len(df_loc)} rows")
            else:
                print(f"[LAC WARN] {loc_name}: no rows parsed")
        except Exception as e:
            print(f"[LAC ERR] {loc_name}: {e}")

    browser.close()

    if not all_rows:
        return pd.DataFrame()

    return pd.concat(all_rows, ignore_index=True)


# Backwards-compatible wrapper expected by some tests
def parse_lac_html(html: str, location_name: str) -> pd.DataFrame:
    """Compatibility wrapper: parse rendered LAC HTML into DataFrame."""
    return _parse_lac_dom(html, location_name)