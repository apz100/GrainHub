"""Luckey Farmers (OH/MI) cash-bid collector — own JSON API.

The grain-bids page (luckeyfarmers.com/grain-bids/) loads a JS app
whose bundle calls the company's OWN API — no Bushel widget, no
AgriCharts embed, no Barchart/DTN host anywhere in the chain:

  GET https://widgets-admin.luckeyfarmers.com/api/v1/cashbids
      (plain GET, no auth; application/json)

Verified live 2026-11-28: 200, ~41 KB, 14 locations, 77 bids.

Response shape:
  {"data": {"locationId1": {"name": "Curtice",
             "cropId1": {"name": "Corn", "bids": [...],
                         "contractUids": [...]}, ...}, ...},
   "kind": ..., "batchUid": ..., "lastUpdatedAt": ...,
   "createdAt": ..., "futuresRecordId": ...}

Each bid:
  {"id", "kind": "normal",
   "name": "Cash" | "NC 27" (delivery label as published),
   "basis": "-0.18" (dollars, string), "basisF",
   "cropId", "symbol": "ZCZ26",
   "currentBid": "4.29", "currentBidF",
   "futuresMonth": "Dec 26",
   "futuresPriceTick": "446'6" (CBOT fractional cents),
   "futuresChangeTick": "7'0", "futuresChangeSign": 1,
   "priceUpdatedAt", "expiration", "locationId", "contractUid"}

Units — documented conversions, not guesses: ``currentBid`` and
``basis`` are already dollars per bushel. ``futuresPriceTick`` /
``futuresChangeTick`` are CBOT fractional cents with an apostrophe
separator (the same eighths notation as the Bushel collector's
``433-2``, written ``446'6`` here): ``446'6`` -> 446 6/8 cents ->
446.75 cents -> $4.4675. The change sign is carried separately in
``futuresChangeSign`` (1 = up, -1 = down, 0 = unchanged), so
change dollars = sign x tick magnitude in dollars. The sign
convention is checked against the published values: cash =
futures + basis holds on the live rows (e.g. Curtice Corn Cash:
$4.4675 - $0.18 = $4.2875 ~ $4.29 published). NOTE: every bid in
the live 2026-11-28 snapshot had futuresChangeSign 1 (futures up
across the board that day), so the -1 / 0 branches are inferred
from the field's meaning, not observed live.

``delivery_month`` is the bid ``name`` as published ("Cash" /
"NC 27") — the API publishes no delivery window, only an
``expiration`` timestamp per bid, which is carried on the row as
``expiration`` (not as delivery_start / delivery_end, which stay
None). The API publishes a single futures-change figure, carried
in both the ``change`` and ``futures_change`` row fields.

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

API_URL = "https://widgets-admin.luckeyfarmers.com/api/v1/cashbids"
COMPANY = "Luckey Farmers"
CURRENCY = "USD"

# Raw API crop name (lowercased) -> canonical commodity name.
# The API publishes "Soybean" (singular); everything else arrives
# already canonical ("Corn", "Wheat").
COMMODITY_MAP = {
    "corn": "Corn",
    "soybean": "Soybeans",
    "soybeans": "Soybeans",
    "wheat": "Wheat",
    "wheat srw": "Wheat — SRW",
    "wheat hrw": "Wheat — HRW",
    "wheat hrs": "Wheat — HRS",
    "wheat sww": "Wheat — SWW",
    "soft red wheat": "Wheat — SRW",
    "hard red winter wheat": "Wheat — HRW",
    "hard red spring wheat": "Wheat — HRS",
    "soft white wheat": "Wheat — SWW",
    "red wheat": "Red Wheat",
    "white wheat": "White Wheat",
    "oats": "Oats",
    "barley": "Barley",
    "milo": "Milo",
    "grain sorghum": "Grain Sorghum",
    "sorghum": "Grain Sorghum",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
# CBOT fractional-cent tick with an apostrophe separator:
# "446'6" (= 446 6/8 cents), "7'0", "-2-2" is NOT this notation
# (the API uses "'" only); an optional leading sign is allowed.
_TICK_RE = re.compile(r"^([+-]?)(\d+)'([0-7])$")


def _money(text: Any) -> float | None:
    """Parse a plain dollar number ('4.29' / '-0.18') to float."""
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

    "446'6" -> 446.75 cents -> $4.4675; "7'0" -> 7.0 cents ->
    $0.07. A plain number in this field is likewise cents (the
    field's documented unit), so it is also divided by 100.
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
    cash_price = _money(bid.get("currentBid"))
    basis = _money(bid.get("basis"))
    futures_price = _tick_dollars(bid.get("futuresPriceTick"))
    change_tick = _tick_dollars(bid.get("futuresChangeTick"))
    sign = bid.get("futuresChangeSign")
    if change_tick is None:
        change = None
    elif isinstance(sign, (int, float)) and not isinstance(sign, bool):
        change = 0.0 if sign == 0 else abs(change_tick) * (1 if sign > 0 else -1)
    else:
        # No sign published: carry the tick magnitude as-is.
        change = change_tick
    if all(value is None for value in (cash_price, basis, futures_price, change)):
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
        # Delivery label as published ("Cash" / "NC 27"); the API
        # publishes no delivery window.
        "delivery_month": bid.get("name") or None,
        "delivery_start": None,
        "delivery_end": None,
        "cash_price": cash_price,
        "cash_price_mt": None,
        "basis": basis,
        "futures_price": futures_price,
        "futures_month": bid.get("futuresMonth") or None,
        "futures_symbol": bid.get("symbol") or None,
        # The API publishes a single futures-change figure; it is
        # carried in both fields (see the module docstring).
        "futures_change": change,
        "change": change,
        "currency": currency,
        "unit": "$/bu",
        # Per-bid expiration timestamp as published; not a delivery
        # window, so it is not mapped to delivery_start / delivery_end.
        "expiration": bid.get("expiration") or None,
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


def parse_luckey_json(
    text: str,
    *,
    company: str = COMPANY,
    currency: str = CURRENCY,
) -> dict[str, Any]:
    """Parse a Luckey cashbids API JSON response into normalized rows.

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
            + ["response is not valid JSON (expected the Luckey cashbids API payload)"],
        )
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return _result(
            company=company,
            location=None,
            rows=[],
            status="unsupported",
            notes=notes
            + ["response has no top-level 'data' object (expected the Luckey cashbids API payload)"],
        )
    last_updated = payload.get("lastUpdatedAt")
    if last_updated:
        notes.append(f"API lastUpdatedAt {last_updated}")

    rows: list[dict[str, Any]] = []
    location_count = 0
    for location_block in payload["data"].values():
        if not isinstance(location_block, dict):
            continue
        location = location_block.get("name") or None
        location_count += 1
        for crop_block in location_block.values():
            if not isinstance(crop_block, dict) or "bids" not in crop_block:
                continue
            commodity = _canonical_commodity(crop_block.get("name"))
            for bid in crop_block.get("bids") or []:
                if not isinstance(bid, dict):
                    continue
                row = _make_row(
                    company=company,
                    location=location,
                    commodity=commodity,
                    bid=bid,
                    currency=currency,
                )
                if row is not None:
                    rows.append(row)
    notes.append(f"{location_count} location(s) in payload")

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


def fetch_luckey_html(url: str = API_URL, timeout: int = 30) -> str:
    """One polite GET of the Luckey cashbids API with the contact User-Agent.

    Named ``*_html`` to mirror the other collectors' raw-fetch
    helpers; the endpoint returns JSON text, not HTML.
    """
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_luckey_json(url: str = API_URL, timeout: int = 30) -> str:
    """Alias for fetch_luckey_html — the raw API response text (JSON)."""
    return fetch_luckey_html(url, timeout=timeout)


def fetch_luckey() -> dict[str, Any]:
    """Fetch and parse Luckey Farmers cash bids from its own JSON API.

    Verified live 2026-11-28: 200, 14 locations, 77 bids
    (Corn / Soybeans / Wheat, USD/bu).
    """
    return parse_luckey_json(fetch_luckey_html())
