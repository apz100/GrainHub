"""Mae-Mart Farms (Norfolk County, Ontario) cash-bid collector.

Source: http://www.mae-martfarms.com/grain-pricing (the homepage
carries only "—" placeholder cards; the bids live on /grain-pricing).
Plain HTML — no browser needed for what is published statically.

Page structure (verified 2026-11-19, one polite GET):
  One <table class="gp-table" id="gp-table-{corn,soybeans,wheat,rye}">
  per crop. Columns:
    Contract / Delivery | CBOT <crop> | Basis (CAD/bu) |
    Cash Price (CAD/bu) | Cash Price (CAD/tonne) | (Lock a Bid)
  The delivery cell reads e.g. "Best Bid HARVEST 2026 - Free Storage
  Program Full - ..." — the delivery label is the leading
  HARVEST <year> / Current Bid token.

Static-HTML limits (recorded, not worked around):
  * The CBOT futures and Cash Price cells are "—" in static HTML.
    The page fills them client-side from its own
    ``/grain-proxy.php?symbols=...`` futures proxy. This collector
    does NOT call that proxy (it is the site's own market-data relay,
    not a plain bid page), so corn/soybean/wheat rows carry
    ``cash_price=None`` with a note.
  * Basis IS published statically (table cell and the inline
    ``ALL_BIDS`` JSON), so rows carry the site's basis.
  * Rye is the exception: it has no futures symbol and a static
    ``manualPrice`` in the inline ``ALL_BIDS`` JSON, which is exactly
    what the site displays as its cash price. Rye rows therefore
    carry ``cash_price`` from that value.

Currency/unit: the page states prices are "CAD/bu and CAD/tonne"
and labels the cash column CAD/bu, so rows are currency CAD,
unit $/bu (``cash_price_mt`` in $/t where published).
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

MAE_MART_URL = "http://www.mae-martfarms.com/grain-pricing"
MAE_MART_COMPANY = "Mae-Mart Farms"
MAE_MART_LOCATION = "Norfolk County"
CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

CROP_TABLE_IDS = {
    "gp-table-corn": "Corn",
    "gp-table-soybeans": "Soybeans",
    "gp-table-wheat": "Wheat",
    "gp-table-rye": "Rye",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_DELIVERY_RE = re.compile(r"(HARVEST\s+\d{4}|CURRENT\s+BID)", re.IGNORECASE)


def _money(text: str | None) -> float | None:
    """Parse '$6.35' / '+1.3000' / '—' to float or None."""
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


def _delivery_label(cell_text: str) -> str:
    """'Best Bid HARVEST 2026 - Free Storage ...' -> 'Harvest 2026'."""
    match = _DELIVERY_RE.search(cell_text)
    if not match:
        return cell_text.strip()
    label = match.group(1)
    return " ".join(word.capitalize() for word in label.split())


def _manual_prices(html: str) -> dict[str, float]:
    """Extract static manualPrice cash values from the inline ALL_BIDS JSON.

    Only crops with a manualPrice (rye) have a statically published
    cash price; the rest rely on the live futures proxy. Returns
    {crop: manual_price}; empty when the JSON is absent/unparseable.
    """
    match = re.search(r"var\s+ALL_BIDS\s*=\s*(\{.*?\});", html, re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return {}
    out: dict[str, float] = {}
    for crop, bids in data.items():
        if not isinstance(bids, list):
            continue
        for bid in bids:
            manual = bid.get("manualPrice") if isinstance(bid, dict) else None
            if isinstance(manual, (int, float)):
                out[crop] = float(manual)
    return out


def parse_mae_mart_html(html: str) -> dict[str, Any]:
    """Parse Mae-Mart /grain-pricing HTML into normalized bid rows.

    Returns {"company", "location", "rows", "status", "notes"}.
    Rows with no statically published cash price carry
    ``cash_price=None`` and a note explaining why — never a computed
    or guessed value.
    """
    soup = BeautifulSoup(html, "lxml")
    manual = _manual_prices(html)
    rows: list[dict[str, Any]] = []
    notes: list[str] = []
    tables_found = 0

    for table_id, commodity in CROP_TABLE_IDS.items():
        table = soup.find("table", id=table_id)
        if table is None:
            continue
        tables_found += 1
        body = table.find("tbody") or table
        for tr in body.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) < 5:
                continue
            delivery = _delivery_label(cells[0])
            basis = _money(cells[2])
            cash = _money(cells[3])
            cash_mt = _money(cells[4])
            note = ""
            if cash is None:
                crop_key = commodity.lower()
                if crop_key in manual:
                    cash = manual[crop_key]
                    note = (
                        "cash price from site's static manualPrice "
                        "(no futures symbol for this crop)"
                    )
                else:
                    note = (
                        "cash price not in static HTML: site fills it "
                        "client-side from its futures proxy; basis only"
                    )
            rows.append(
                {
                    "company": MAE_MART_COMPANY,
                    "location": MAE_MART_LOCATION,
                    "commodity": commodity,
                    "delivery_month": delivery,
                    "cash_price": cash,
                    "cash_price_mt": cash_mt,
                    "basis": basis,
                    "futures_price": None,
                    "currency": "CAD",
                    "unit": "$/bu",
                    "note": note,
                }
            )

    if tables_found == 0:
        return {
            "company": MAE_MART_COMPANY,
            "location": MAE_MART_LOCATION,
            "rows": [],
            "status": "unsupported",
            "notes": ["no gp-table-* bid tables found in page HTML"],
        }
    if not rows:
        return {
            "company": MAE_MART_COMPANY,
            "location": MAE_MART_LOCATION,
            "rows": [],
            "status": "empty",
            "notes": ["bid tables found but no rows parsed"],
        }
    notes.append(
        "cash prices for corn/soybeans/wheat need the site's live "
        "futures proxy; only basis is static for those crops"
    )
    return {
        "company": MAE_MART_COMPANY,
        "location": MAE_MART_LOCATION,
        "rows": rows,
        "status": "ok",
        "notes": notes,
    }


def fetch_mae_mart_html(url: str = MAE_MART_URL, timeout: int = 30) -> str:
    """One polite GET of the Mae-Mart grain-pricing page."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_mae_mart(url: str = MAE_MART_URL) -> dict[str, Any]:
    """Fetch and parse Mae-Mart bids in one call."""
    return parse_mae_mart_html(fetch_mae_mart_html(url))
