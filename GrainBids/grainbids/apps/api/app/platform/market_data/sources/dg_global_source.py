# dg_global_source.py
"""DG Global cash bid collector — own JSON API.

Diagnosis (2026-11-28, run 46103946452): the adapter scraped the
Vue-rendered ``<table>`` elements on https://dgglobal.ca/cash-bids
with Playwright and parsed 0 rows on all 3 attempts, even though the
page loads (HTTP 200). The cash-bids page is a Vue SPA (``<main
id="app">``, no tables in the static HTML) whose own frontend fetches:

  GET https://dgglobal.ca/api/markets/cash-bids
      (plain GET, no auth; application/json)

Verified live 2026-11-28: 200, ``available: true, stale: false``,
``updatedAt`` fresh, 45 bids — Corn / Soybeans / Wheat, SRW across
5 Ontario destinations (Becher, Princeton, Shetland, Staples,
Talbotville). The data is served from DG Global's own domain, no
third-party host anywhere in the chain.

Response shape:
  {"available": true, "stale": false,
   "updatedAt": "2026-11-28T05:07:32+00:00",
   "data": [{"id", "type": "Corn" | "Soybeans" | "Wheat, SRW",
             "destination", "delivery": "Dec 2026",
             "futureMonth": "Mar 2027", "symbol": "@C7H",
             "futures": "463'0", "change": "6'4",
             "direction": "up" | "down", "basis": "1.15",
             "cash": "5.78", "converted": "227.55",
             "delayed": true}, ...]}

Units — documented conversions, not guesses: ``cash``, ``basis``
and ``converted`` are already dollars (``converted`` is $/MT, the
rest $/bu). ``futures`` / ``change`` are CBOT fractional-cent ticks
with an apostrophe separator (the same eighths notation as the
Luckey collector's ``446'6``): ``463'0`` -> 463.0 cents -> $4.63.
The change sign is carried separately in ``direction``
(``up`` = +, ``down`` = -), so change dollars = sign x tick
magnitude. The sign convention is checked against the published
values: cash = futures + basis holds on the live rows (e.g. Becher
Corn Dec 2026: $4.63 + $1.15 = $5.78 published). NOTE: every bid in
the live 2026-11-28 snapshot had direction ``up``, so the ``down``
branch is inferred from the field's meaning, not observed live.
``delayed`` is true on every row — the API marks its prices delayed,
as published; that is carried in the notes, not per row.

``delivery_month`` is the delivery label as published (``"Dec 2026"``);
the upload path maps it to both delivery_end and delivery_label
(see app/services/upload_csv.py). No delivery window is published,
so delivery_start / delivery_end stay None on the row itself.

Rows never contain invented values: unparseable or absent cells
become None, with a ``note`` explaining what is missing.

Return shape (matches the other direct_dict collectors):
{"company", "location", "rows", "status", "notes"} where ``status``
is "ok" (rows found), "empty" (payload present but no parseable
rows) or "unsupported" (response is not the expected JSON shape).
``location`` is the first location seen in the payload.
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests

CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

API_URL = "https://dgglobal.ca/api/markets/cash-bids"
COMPANY = "DG Global"
CURRENCY = "CAD"  # Ontario destinations; dgglobal.ca prices are CAD.

# Raw API type (lowercased) -> canonical commodity name.
COMMODITY_MAP = {
    "corn": "Corn",
    "soybeans": "Soybeans",
    "soybean": "Soybeans",
    "wheat, srw": "Wheat — SRW",
    "wheat srw": "Wheat — SRW",
    "soft red wheat": "Wheat — SRW",
    "wheat": "Wheat",
    "oats": "Oats",
    "barley": "Barley",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
# CBOT fractional-cent tick with an apostrophe separator:
# "463'0" (= 463 0/8 cents), "6'4"; an optional leading sign allowed.
_TICK_RE = re.compile(r"^([+-]?)(\d+)'([0-7])$")


def _money(text: Any) -> float | None:
    """Parse a plain dollar number ('5.78' / '1.15') to float."""
    if text is None:
        return None
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text)
    cleaned = str(text).replace("$", "").replace(",", "").strip()
    if cleaned in ("", "-", "—", "--"):
        return None
    match = _NUM_RE.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _tick_dollars(text: Any) -> float | None:
    """Convert a CBOT fractional-cent tick quote to dollars.

    "463'0" -> 463.0 cents -> $4.63; "6'4" -> 6.5 cents -> $0.065.
    A plain number in this field is likewise cents (the field's
    documented unit), so it is also divided by 100.
    """
    if text is None:
        return None
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text) / 100.0
    cleaned = str(text).replace("$", "").replace(",", "").strip()
    if cleaned in ("", "-", "—", "--"):
        return None
    tick = _TICK_RE.match(cleaned)
    if tick:
        sign, whole, eighths = tick.groups()
        cents = float(whole) + int(eighths) / 8
        return -cents / 100.0 if sign == "-" else cents / 100.0
    num = _money(cleaned)
    return None if num is None else num / 100.0


def _canonical_commodity(raw: Any) -> str:
    if not raw:
        return "Unknown"
    label = str(raw).strip().lower()
    if not label:
        return "Unknown"
    return COMMODITY_MAP.get(label, str(raw).strip().title())


def _make_row(
    *,
    company: str,
    location: str | None,
    commodity: str,
    bid: dict[str, Any],
    currency: str,
) -> dict[str, Any] | None:
    """Build one normalized row; None if it carries no usable money value."""
    cash_price = _money(bid.get("cash"))
    cash_price_mt = _money(bid.get("converted"))
    basis = _money(bid.get("basis"))
    futures_price = _tick_dollars(bid.get("futures"))
    change_tick = _tick_dollars(bid.get("change"))
    direction = str(bid.get("direction") or "").strip().lower()
    if change_tick is None:
        change = None
    elif direction == "down":
        change = -abs(change_tick)
    elif direction == "up":
        change = abs(change_tick)
    else:
        # No direction published: carry the tick magnitude as-is.
        change = change_tick
    if all(
        value is None for value in (cash_price, basis, futures_price, change)
    ):
        return None
    missing = [
        label
        for label, value in (
            ("basis", basis),
            ("futures", futures_price),
            ("change", change),
        )
        if value is None
    ]
    note = ""
    if missing:
        if cash_price is not None and len(missing) == 3:
            note = "Bid only — no basis / futures / change published for this row"
        else:
            note = "Missing: " + ", ".join(missing)
    return {
        "company": company,
        "location": location,
        "commodity": commodity,
        # Delivery label as published ("Dec 2026"); the upload path
        # maps delivery_month to delivery_end + delivery_label.
        # No delivery window is published.
        "delivery_month": bid.get("delivery") or None,
        "delivery_start": None,
        "delivery_end": None,
        "cash_price": cash_price,
        "cash_price_mt": cash_price_mt,
        "basis": basis,
        "futures_price": futures_price,
        "futures_month": bid.get("futureMonth") or None,
        "futures_symbol": bid.get("symbol") or None,
        # The API publishes a single futures-change figure; it is
        # carried in both fields (see the module docstring).
        "futures_change": change,
        "change": change,
        "currency": currency,
        "unit": "$/bu",
        "note": note,
    }


def _result(
    *,
    company: str,
    location: str | None,
    rows: list[dict[str, Any]],
    status: str,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "company": company,
        "location": location,
        "rows": rows,
        "status": status,
        "notes": notes,
    }


def parse_dg_global_json(
    text: str,
    *,
    company: str = COMPANY,
    currency: str = CURRENCY,
) -> dict[str, Any]:
    """Parse a DG Global cash-bids API JSON response into normalized rows.

    ``text`` is the raw response body of GET ``API_URL`` (a JSON
    string), so tests can use a recorded fixture without network.
    Returns {"company", "location", "rows", "status", "notes"}; see
    the module docstring.
    """
    notes: list[str] = []
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return _result(
            company=company,
            location=None,
            rows=[],
            status="unsupported",
            notes=notes
            + ["response is not valid JSON (expected the DG Global cash-bids API payload)"],
        )
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return _result(
            company=company,
            location=None,
            rows=[],
            status="unsupported",
            notes=notes
            + ["response has no top-level 'data' list (expected the DG Global cash-bids API payload)"],
        )
    updated_at = payload.get("updatedAt")
    if updated_at:
        notes.append(f"API updatedAt {updated_at}")
    if payload.get("delayed") is True or any(
        isinstance(b, dict) and b.get("delayed") for b in payload["data"]
    ):
        notes.append("API marks rows delayed=true (prices delayed as published)")

    rows: list[dict[str, Any]] = []
    locations: list[str] = []
    for bid in payload["data"]:
        if not isinstance(bid, dict):
            continue
        location = bid.get("destination") or None
        if location and location not in locations:
            locations.append(location)
        row = _make_row(
            company=company,
            location=location,
            commodity=_canonical_commodity(bid.get("type")),
            bid=bid,
            currency=currency,
        )
        if row is not None:
            rows.append(row)
    notes.append(f"{len(locations)} location(s) in payload")

    location = rows[0]["location"] if rows else None
    if not rows:
        return _result(
            company=company,
            location=location,
            rows=[],
            status="empty",
            notes=notes + ["payload present but no bid rows parsed"],
        )
    return _result(
        company=company, location=location, rows=rows, status="ok", notes=notes
    )


def fetch_dg_global_html(url: str = API_URL, timeout: int = 30) -> str:
    """One polite GET of the DG Global cash-bids API with the contact User-Agent."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_dg_global(_playwright=None) -> dict[str, Any]:
    """Fetch and parse DG Global cash bids from its own JSON API.

    Verified live 2026-11-28: 200, 5 Ontario destinations, 45 bids
    (Corn / Soybeans / Wheat, SRW; CAD/bu, $/MT converted).

    ``_playwright`` is accepted and ignored: the legacy GrainBidder
    orchestrator still calls fetchers with a Playwright instance, but
    this collector needs no browser — the API is plain JSON.
    """
    return parse_dg_global_json(fetch_dg_global_html())
