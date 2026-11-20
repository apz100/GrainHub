"""North Gower Grains (North Gower, Ontario) cash-bid collector.

Ordinary price source among many — no special treatment, no pilot,
no showcase, no branding or affiliation anywhere in this module.

Source: the daily blog post on https://northgowergrains.com/
(e.g. https://northgowergrains.com/wednesday-november-18-2026-820-am/).
The homepage itself only carries a "#cash-bids" call-to-action with
no prices; the dated bid table lives in the daily post. Plain HTML —
no browser needed.

Post structure (verified 2026-11-19, one polite GET):
  One <table> with headers:
    Name | Notes | Basis Month | Futures Price | Fut. Chg. |
    Basis | Cash Price | Cash Price (tonne)
  Rows: CORN / SOYBEANS / WHEAT, SRW / WHEAT, HRW (INCLUDES PROTEIN) /
  WHEAT, HRS (INCLUDES PROTEIN), each with Notes Spot / Harvest 2026 /
  Harvest 2027 and a Basis Month like "Sep 2026".

``delivery_month`` is the Notes value (Spot / Harvest 2026 /
Harvest 2027); ``futures_price`` and basis come from their columns;
``cash_price`` is the Cash Price column ($/bu) and ``cash_price_mt``
the Cash Price (tonne) column.

Currency: CAD — North Gower Grains is an Ontario elevator and the
table is headed in dollars; the page does not state a currency
explicitly, so this is recorded as an inference, not a page fact.

``find_latest_post_url`` reads the homepage HTML and returns the
most recent daily-post link (``/<weekday>-<month>-<day>-<year>-<time>/``)
so the fetch step can target today's post without guessing a URL.
"""

from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup

NORTH_GOWER_HOMEPAGE = "https://northgowergrains.com/"
NORTH_GOWER_COMPANY = "North Gower Grains"
NORTH_GOWER_LOCATION = "North Gower"
CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

# Daily-post slugs look like /wednesday-november-18-2026-820-am/
_POST_RE = re.compile(
    r"^https://northgowergrains\.com/"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)-"
    r"(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)-\d{1,2}-\d{4}-\d{1,4}-(am|pm)/$",
    re.IGNORECASE,
)

COMMODITY_MAP = {
    "corn": "Corn",
    "soybeans": "Soybeans",
    "wheat, srw": "Wheat — SRW",
    "wheat, hrw (includes protein)": "Wheat — HRW",
    "wheat, hrs (includes protein)": "Wheat — HRS",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _money(text: str | None) -> float | None:
    """Parse '$6.70' / '4.6475' / '+2.75' to float or None."""
    if not text:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    if cleaned in ("", "-", "—", "--"):
        return None
    match = _NUM_RE.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def find_latest_post_url(homepage_html: str) -> str | None:
    """Return the first daily-post URL found on the homepage HTML.

    The homepage lists recent posts newest-first, so the first match
    is the latest post. Returns None when no post link is present.
    """
    soup = BeautifulSoup(homepage_html, "lxml")
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if _POST_RE.match(href):
            return href
    return None


def parse_north_gower_html(html: str) -> dict[str, Any]:
    """Parse a North Gower daily-post page into normalized bid rows.

    Returns {"company", "location", "rows", "status", "notes"} where
    ``status`` is "ok" (rows found), "empty" (table present but no
    rows parsed) or "unsupported" (no bid table found — e.g. the
    page is not a daily post).
    """
    soup = BeautifulSoup(html, "lxml")
    table = None
    for candidate in soup.find_all("table"):
        headers = [
            th.get_text(" ", strip=True).lower()
            for th in candidate.find_all("th")
        ]
        if "cash price" in headers and "basis" in headers and "name" in headers:
            table = candidate
            break
    if table is None:
        return {
            "company": NORTH_GOWER_COMPANY,
            "location": NORTH_GOWER_LOCATION,
            "rows": [],
            "status": "unsupported",
            "notes": ["no bid table (Name/Basis/Cash Price headers) found"],
        }

    headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
    idx = {name: i for i, name in enumerate(headers)}
    rows: list[dict[str, Any]] = []
    body = table.find("tbody") or table
    for tr in body.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cells) < len(headers):
            continue
        raw_name = cells[idx["name"]] if "name" in idx else ""
        if not raw_name or raw_name.lower() == "name":
            continue
        commodity = COMMODITY_MAP.get(raw_name.lower(), raw_name)
        delivery = cells[idx["notes"]] if "notes" in idx else ""
        basis_month = (
            cells[idx["basis month"]] if "basis month" in idx else ""
        )
        futures = (
            _money(cells[idx["futures price"]])
            if "futures price" in idx
            else None
        )
        basis = _money(cells[idx["basis"]]) if "basis" in idx else None
        cash = (
            _money(cells[idx["cash price"]])
            if "cash price" in idx
            else None
        )
        cash_mt = (
            _money(cells[idx["cash price (tonne)"]])
            if "cash price (tonne)" in idx
            else None
        )
        if cash is None and basis is None and futures is None:
            continue
        rows.append(
            {
                "company": NORTH_GOWER_COMPANY,
                "location": NORTH_GOWER_LOCATION,
                "commodity": commodity,
                "delivery_month": delivery,
                "basis_month": basis_month,
                "cash_price": cash,
                "cash_price_mt": cash_mt,
                "basis": basis,
                "futures_price": futures,
                "currency": "CAD",
                "unit": "$/bu",
                "note": "",
            }
        )

    if not rows:
        return {
            "company": NORTH_GOWER_COMPANY,
            "location": NORTH_GOWER_LOCATION,
            "rows": [],
            "status": "empty",
            "notes": ["bid table found but no rows parsed"],
        }
    return {
        "company": NORTH_GOWER_COMPANY,
        "location": NORTH_GOWER_LOCATION,
        "rows": rows,
        "status": "ok",
        "notes": [],
    }


def fetch_html(url: str, timeout: int = 30) -> str:
    """One polite GET. Contact User-Agent."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_north_gower_post(post_url: str) -> dict[str, Any]:
    """Fetch one daily-post URL and parse its bid table."""
    return parse_north_gower_html(fetch_html(post_url))


def fetch_north_gower_latest() -> dict[str, Any]:
    """Fetch the homepage, find the latest daily post, fetch and parse it."""
    homepage = fetch_html(NORTH_GOWER_HOMEPAGE)
    post_url = find_latest_post_url(homepage)
    if post_url is None:
        return {
            "company": NORTH_GOWER_COMPANY,
            "location": NORTH_GOWER_LOCATION,
            "rows": [],
            "status": "unsupported",
            "notes": ["no daily-post link found on homepage"],
        }
    result = fetch_north_gower_post(post_url)
    result["notes"] = [f"post: {post_url}"] + result["notes"]
    return result
