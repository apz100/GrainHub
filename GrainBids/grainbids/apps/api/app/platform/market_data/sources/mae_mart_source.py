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
    ``/grain-proxy?symbols=...`` futures proxy.
  * Basis IS published statically (table cell and the inline
    ``ALL_BIDS`` JSON), so rows carry the site's basis.
  * Rye is the exception: it has no futures symbol and a static
    ``manualPrice`` in the inline ``ALL_BIDS`` JSON, which is exactly
    what the site displays as its cash price. Rye rows therefore
    carry ``cash_price`` from that value.

Futures proxy (verified live 2026-11-19, Cycle 19, one GET):
  ``GET /grain-proxy?symbols=ZCZ26=F`` returns HTTP 200,
  ``application/json``, shaped exactly as the page's inline JS
  documents: JSON keyed by symbol, each entry with a numeric
  ``price`` and a ``currency``. (Cycle 29: the ``.php`` URL now
  301s to this extensionless canonical URL; Cycle 30 stored the
  canonical form directly to save the redirect hop.)
  ``currency == "USX"`` means the
  price is in cents, so the client divides by 100 — this collector
  follows the page's own rule. ``fetch_mae_mart`` therefore fills
  ``futures_price`` on corn/soybean/wheat rows from the proxy as an
  optional second step that degrades gracefully (rows keep
  ``futures_price=None`` if the proxy fails). ``cash_price`` is
  NEVER computed from futures + basis here: using the site's relay
  of third-party futures data plus its static basis to compute cash
  is a decision for Adam/the coordinator, so corn/soybean/wheat
  rows still carry ``cash_price=None`` with a note.

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
MAE_MART_PROXY_URL = "http://www.mae-martfarms.com/grain-proxy"
MAE_MART_COMPANY = "Mae-Mart Farms"
MAE_MART_LOCATION = "Norfolk County"
CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

# Futures symbols the page itself uses (from its inline JS, verified
# 2026-11-19). Rye has no symbol — no proxy call for it.
FUTURES_SYMBOLS = {
    "Corn": "ZCZ26=F",
    "Soybeans": "ZSF27=F",
    "Wheat": "ZWN27=F",
}

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


def parse_mae_mart_proxy_json(data: dict[str, Any]) -> dict[str, float]:
    """Parse the /grain-proxy response into {commodity: futures $/bu}.

    Contract (verified live 2026-11-19, Cycle 19): JSON keyed by
    Yahoo-style symbol, each entry with a numeric ``price`` and a
    ``currency``. ``currency == "USX"`` means the price is in cents,
    so it is divided by 100 — the page's own rule. Any other
    currency is taken as dollars as-is. Malformed or unknown-symbol
    entries are ignored, never guessed.
    """
    symbol_to_commodity = {sym: crop for crop, sym in FUTURES_SYMBOLS.items()}
    out: dict[str, float] = {}
    if not isinstance(data, dict):
        return out
    for symbol, entry in data.items():
        crop = symbol_to_commodity.get(symbol)
        if crop is None or not isinstance(entry, dict):
            continue
        price = entry.get("price")
        if not isinstance(price, (int, float)):
            continue
        if entry.get("currency") == "USX":
            out[crop] = float(price) / 100.0
        else:
            out[crop] = float(price)
    return out


def fetch_mae_mart_futures(
    symbols: dict[str, str] | None = None, timeout: int = 30
) -> dict[str, float]:
    """Fetch futures quotes from the site's own proxy, one GET per symbol.

    Mirrors the page's client-side behaviour (one symbol per request).
    A failed symbol is skipped, not fatal; returns {} when nothing
    usable comes back. Callers treat an empty result as "no futures
    data" and keep the static-only rows.
    """
    symbols = symbols or FUTURES_SYMBOLS
    out: dict[str, float] = {}
    for crop, symbol in symbols.items():
        try:
            response = requests.get(
                MAE_MART_PROXY_URL,
                params={"symbols": symbol},
                headers={"User-Agent": CONTACT_USER_AGENT},
                timeout=timeout,
            )
            response.raise_for_status()
            out.update(parse_mae_mart_proxy_json(response.json()))
        except (requests.RequestException, ValueError):
            continue
    return out


def fetch_mae_mart(
    url: str = MAE_MART_URL, include_futures: bool = True
) -> dict[str, Any]:
    """Fetch and parse Mae-Mart bids in one call.

    The proxy call is an optional second step: when
    ``include_futures`` is true it fills ``futures_price`` on the
    corn/soybean/wheat rows from the site's futures proxy. Any proxy
    failure degrades gracefully to the static-only rows (basis only,
    ``futures_price=None``). ``cash_price`` is never computed from
    futures + basis — that decision is left to Adam/the coordinator.
    """
    result = parse_mae_mart_html(fetch_mae_mart_html(url))
    if not include_futures or result["status"] != "ok":
        return result
    try:
        futures = fetch_mae_mart_futures()
    except Exception:
        futures = {}
    if not futures:
        result["notes"].append(
            "futures proxy unavailable: rows carry basis only, "
            "futures_price left empty"
        )
        return result
    for row in result["rows"]:
        price = futures.get(row["commodity"])
        if price is not None:
            row["futures_price"] = price
    result["notes"].append(
        "futures_price from the site's /grain-proxy relay "
        "(USX cents converted to dollars per the page's own rule); "
        "cash_price is NOT computed from futures + basis"
    )
    return result
