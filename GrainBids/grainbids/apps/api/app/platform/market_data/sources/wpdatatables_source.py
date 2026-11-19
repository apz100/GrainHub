"""Generic wpDataTables cash-bid collector.

Covers sites that publish cash bids in a server-rendered wpDataTables
table (``<table class="... wpDataTable ...">``) — a NEW pattern found
in Cycle 8 (2026-11-19). One parser, per-site config for URL /
company / currency; no per-site code.

Verified site — Five Star Coop (New Hampton, IA):

  https://www.fivestarcoop.com/cash-bids
      -> 301 https://www.fivestarcoop.com/grain-elevators-and-services/
         five-star-cash-bids/
  Verified live 2026-11-19 (one polite GET): 200, table_1 present in
  static HTML, 299 bid rows (Corn 197 + Soybeans 102) across 21
  locations, USD/bu. Saved Cycle 8 copy: /tmp/cycle8/five-star.html.

Page shape (table_1, id="table_1", class wpDataTable):

  Header (12 columns):
    Location | Commodity | Delivery Periods | Bids | Basis | Change
    | LocationID | deliveryPeriodID | TradeDateTime | id
    | createdAt | updatedAt
  The last six columns are hidden bookkeeping IDs / timestamps and
  are ignored — except TradeDateTime, which is the row's as-of date
  (e.g. "Nov 18, 2026, 1:15 PM CST"; identical on every row).

  One data row per location x commodity x delivery period. The table
  repeats its header row once at the end of <tbody> (a wpDataTables
  grouping artifact); that repeat is skipped, as is any row with no
  usable money value at all.

  Locations are kept VERBATIM: the table mixes Five Star elevators
  (Ionia, New Hampton, Nashua, ...) with third-party delivery points
  (AGP Mason City, Valero Charles City, Shell Rock Soy Processing,
  GGE Mason City, Reicks View Milling, Christensen Farms FC). No
  location is cleaned, expanded, or dropped.

  Tables 2-4 on the same page are DTN futures tables (WHEAT / LIVE
  CATTLE / RBOB GASOLINE, headers description / marketName / symbol /
  ... / Last / Change) — NOT cash bids. The parser selects ONLY the
  table whose header contains both "Location" and "Bids" (preferring
  id="table_1"); the futures tables never qualify, so they are never
  read as bids.

Delivery labels are inconsistent on the page and are normalised to
"%b %Y" (e.g. "Nov 2026"). Observed mapping (all labels seen live
2026-11-19):

  "Nov 26"    -> "Nov 2026"     "Nov26"     -> "Nov 2026"
  "Dec26"     -> "Dec 2026"     "Dec27"     -> "Dec 2027"
  "Jan27"     -> "Jan 2027"     "Jan 27"    -> "Jan 2027"
  "Feb 27"    -> "Feb 2027"     "Mar 27"    -> "Mar 2027"
  "Apr 27"    -> "Apr 2027"     "April 27"  -> "Apr 2027"
  "May 27"    -> "May 2027"     "June 27"   -> "Jun 2027"
  "July 27"   -> "Jul 2027"     "Oct 27."   -> "Oct 2027"
  "Dec 27"    -> "Dec 2027"
  The raw label is kept in ``delivery_raw``. A label that matches no
  known pattern is kept verbatim in ``delivery_month`` and flagged in
  the notes, never dropped or guessed.

Units — published numbers, NOT normalized: Bids and Basis are dollars
per bushel (Bids 3.89-4.36 corn, 11.13-11.67 soybeans; Basis -0.35 to
-0.88). Change is published in CENTS (-7.75 to -13.00 — a dollars
reading would be absurd for a daily move, and matches the cents
convention on the Bushel decimal sites); it is kept as published so
consumers see the page's own numbers. ``futures_price`` /
``futures_month`` / ``last_trade`` are None: this page publishes no
futures alongside the bids (the DTN futures live in the separate
tables 2-4, which are not parsed).

Numbers are decimal on the verified page (no fractional quotes were
present); CBOT-style fractional notation ("433-2" = 433 2/8) is still
handled by ``_money`` for robustness, in the same unit as published.

Rows never contain invented values: unparseable or absent cells become
None, with a ``note`` explaining what is missing. Every row carries
``source`` ("five_star_coop") and ``date`` (ISO date parsed from the
row's TradeDateTime, e.g. "2026-11-18"; the raw text is kept in
``trade_datetime``).

Return shape (matches the other direct_dict collectors):
{"company", "location", "rows", "status", "notes"} where ``status``
is "ok" (rows found), "empty" (bid table present but no parseable
rows) or "unsupported" (no Location/Bids table found).
``location`` is the first row's location.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

FIVE_STAR_URL = (
    "https://www.fivestarcoop.com/grain-elevators-and-services/"
    "five-star-cash-bids/"
)
# The /cash-bids URL 301-redirects to the URL above (Cycle 8).
FIVE_STAR_ENTRY_URL = "https://www.fivestarcoop.com/cash-bids"

# Raw commodity label (lowercased) -> canonical commodity name.
COMMODITY_MAP = {
    "corn": "Corn",
    "soybeans": "Soybeans",
    "soybean": "Soybeans",
    "wheat": "Wheat",
    "wheat srw": "Wheat — SRW",
    "wheat hrw": "Wheat — HRW",
    "wheat hrs": "Wheat — HRS",
    "wheat sww": "Wheat — SWW",
    "oats": "Oats",
    "barley": "Barley",
    "milo": "Milo",
    "grain sorghum": "Grain Sorghum",
    "sorghum": "Grain Sorghum",
    "canola": "Canola",
    "flax": "Flax",
    "rye": "Rye",
    "sunflowers": "Sunflowers",
    "sunflower": "Sunflowers",
}

# Header label (lowercased) -> row field. The six hidden bookkeeping
# columns (LocationID, deliveryPeriodID, id, createdAt, updatedAt)
# map to nothing and are ignored; TradeDateTime is the row date.
HEADER_FIELDS = {
    "location": "location",
    "commodity": "commodity",
    "delivery periods": "delivery_month",
    "delivery period": "delivery_month",
    "bids": "cash_price",
    "bid": "cash_price",
    "basis": "basis",
    "change": "change",
    "tradedatetime": "trade_datetime",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
# CBOT-style fractional quote: whole + eighths, e.g. "433-2"
# (= 433 2/8), "-2-2", "+0-6". Not present on the verified Five Star
# page (all values decimal) but handled like the Bushel collector.
_FRAC_RE = re.compile(r"^([+-]?)(\d+)-([0-7])$")
# Delivery label: month name (full or abbreviated, optional trailing
# period) + optional space + 2-digit year, e.g. "Dec26", "Dec 26",
# "April 27", "Oct 27.". Captures (month, year).
_DELIVERY_RE = re.compile(r"^([A-Za-z]+)\.?\s?(\d{2})$")
# TradeDateTime, e.g. "Nov 18, 2026, 1:15 PM CST" — the trailing
# timezone abbreviation is stripped before parsing.
_TRADE_DATE_RE = re.compile(
    r"^([A-Za-z]{3} \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M)"
)
_MONEY_FIELDS = {"cash_price", "basis", "change"}

# Full month name / abbreviation (lowercased) -> "%b" abbreviation.
_MONTH_ABBR = {
    "jan": "Jan", "january": "Jan",
    "feb": "Feb", "february": "Feb",
    "mar": "Mar", "march": "Mar",
    "apr": "Apr", "april": "Apr",
    "may": "May",
    "jun": "Jun", "june": "Jun",
    "jul": "Jul", "july": "Jul",
    "aug": "Aug", "august": "Aug",
    "sep": "Sep", "sept": "Sep", "september": "Sep",
    "oct": "Oct", "october": "Oct",
    "nov": "Nov", "november": "Nov",
    "dec": "Dec", "december": "Dec",
}


@dataclass(frozen=True)
class WpDataTablesSite:
    """Per-site config — no per-site code."""

    key: str
    company: str
    url: str
    currency: str = "USD"
    default_location: str | None = None
    # True only once the live page has been fetched and the
    # Location/Bids table shape confirmed. Unverified sites stay in
    # the registry as documentation; fetch_wpdatatables_site()
    # refuses them.
    verified: bool = False
    notes: str = ""


WPDATATABLES_SITES: dict[str, WpDataTablesSite] = {
    "five_star_coop": WpDataTablesSite(
        key="five_star_coop",
        company="Five Star Coop",
        url=FIVE_STAR_URL,
        currency="USD",
        default_location="New Hampton",
        verified=True,
        notes="Verified live 2026-11-19: 200, wpDataTables table_1 in "
        "static HTML, 299 rows (Corn 197 + Soybeans 102), 21 locations "
        "(Five Star elevators + third-party delivery points kept "
        "verbatim), USD/bu. Tables 2-4 are DTN futures, not bids. "
        "Delivery labels inconsistent (Dec26 vs Dec 27, Apr 27 vs "
        "April 27) — normalised, see module docstring.",
    ),
}


def _money(text: str | None) -> float | None:
    """Parse a plain number like '11.28' / '-0.88' / '4' to float.

    Also handles CBOT-style fractional quotes '433-2' (433 2/8) and
    '-2-2' / '+0-6', converting to decimal in the same unit as
    published. Empty / dash cells become None.
    """
    if not text:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    if cleaned in ("", "-", "—", "--"):
        return None
    frac = _FRAC_RE.match(cleaned)
    if frac:
        sign, whole, eighths = frac.groups()
        value = float(whole) + int(eighths) / 8
        return -value if sign == "-" else value
    match = _NUM_RE.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _canonical_commodity(raw: str | None) -> str:
    if not raw:
        return "Unknown"
    label = raw.strip()
    return COMMODITY_MAP.get(label.lower(), label.title())


def normalize_delivery_label(raw: str | None) -> str | None:
    """Normalise an inconsistent delivery label to "%b %Y".

    "Dec26" / "Dec 26" -> "Dec 2026"; "April 27" -> "Apr 2027";
    "Oct 27." -> "Oct 2027". A label matching no known pattern is
    returned verbatim (stripped) so nothing is dropped or guessed.
    """
    if not raw:
        return None
    label = raw.strip().rstrip(".").strip()
    if not label:
        return None
    match = _DELIVERY_RE.match(label)
    if not match:
        return label
    month_raw, year2 = match.groups()
    abbr = _MONTH_ABBR.get(month_raw.lower())
    if abbr is None:
        return label
    return f"{abbr} 20{year2}"


def _trade_date(raw: str | None) -> str | None:
    """'Nov 18, 2026, 1:15 PM CST' -> '2026-11-18' (ISO date)."""
    if not raw:
        return None
    text = raw.strip()
    match = _TRADE_DATE_RE.match(text)
    candidate = match.group(1) if match else text
    for fmt in ("%b %d, %Y, %I:%M %p", "%b %d, %Y"):
        try:
            return datetime.strptime(candidate, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _find_bid_table(soup: Any) -> Any | None:
    """Return the cash-bids wpDataTables table, or None.

    The bid table is the one whose header row contains both
    "Location" and "Bids". The page's DTN futures tables (2-4) have
    headers like description / marketName / symbol / ... / Last /
    Change — no "Bids" column — so they never qualify. id="table_1"
    is preferred when present, but the header check is authoritative.
    """
    candidates: list[Any] = []
    for table in soup.find_all("table"):
        header_texts = [
            c.get_text(" ", strip=True).lower()
            for tr in table.find_all("tr")
            for c in tr.find_all(["th", "td"])
        ]
        if "location" in header_texts and "bids" in header_texts:
            candidates.append(table)
    if not candidates:
        return None
    for table in candidates:
        if table.get("id") == "table_1":
            return table
    return candidates[0]


def _make_row(
    *,
    company: str,
    source_key: str,
    location: str | None,
    commodity: str,
    fields: dict[str, Any],
    currency: str,
) -> dict[str, Any] | None:
    """Build one normalized row; None if it carries no usable money value."""
    cash_price = fields.get("cash_price")
    basis = fields.get("basis")
    change = fields.get("change")
    if all(value is None for value in (cash_price, basis, change)):
        return None
    missing = [
        label
        for label, value in (
            ("basis", basis),
            ("change", change),
        )
        if value is None
    ]
    note = ""
    if missing:
        if cash_price is not None and len(missing) == 2:
            note = "Bid only — no basis / change published for this row"
        else:
            note = "Missing: " + ", ".join(missing)
    delivery_raw = fields.get("delivery_raw")
    trade_datetime = fields.get("trade_datetime")
    return {
        "company": company,
        "source": source_key,
        "location": location,
        "commodity": commodity,
        "delivery_month": normalize_delivery_label(delivery_raw),
        "delivery_raw": delivery_raw,
        "cash_price": cash_price,
        # No per-tonne price is published; None (not a conversion).
        "cash_price_mt": None,
        "basis": basis,
        # No futures published alongside the bids on this page (the
        # DTN futures live in the separate tables 2-4, not parsed).
        "futures_price": None,
        "futures_month": None,
        "last_trade": None,
        "change": change,
        "currency": currency,
        "unit": "$/bu",
        # As-of date from the row's TradeDateTime column.
        "date": _trade_date(trade_datetime),
        "trade_datetime": trade_datetime,
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


def parse_wpdatatables_html(
    html: str,
    *,
    company: str | None = None,
    currency: str = "USD",
    site: WpDataTablesSite | None = None,
    default_location: str | None = None,
) -> dict[str, Any]:
    """Parse a wpDataTables cash-bids page into normalized bid rows.

    ``site`` (a WPDATATABLES_SITES entry) supplies company / currency
    / default location; the keyword arguments override it for ad-hoc
    pages. Returns {"company", "location", "rows", "status",
    "notes"}; see the module docstring.
    """
    if site is not None:
        company = company or site.company
        currency = site.currency
        default_location = default_location or site.default_location
    company = company or "Unknown wpDataTables site"
    source_key = site.key if site is not None else "wpdatatables"
    notes: list[str] = []
    if site is not None and site.notes:
        notes.append(f"site config: {site.notes}")

    soup = BeautifulSoup(html, "lxml")
    table = _find_bid_table(soup)
    if table is None:
        return _result(
            company=company,
            location=default_location,
            rows=[],
            status="unsupported",
            notes=notes
            + [
                "no cash-bids table found (expected a wpDataTables "
                "table whose header contains Location + Bids)"
            ],
        )

    column_map: list[str | None] | None = None
    rows: list[dict[str, Any]] = []
    unparsed_deliveries: set[str] = set()
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        texts = [c.get_text(" ", strip=True) for c in cells]
        lowered = [t.lower() for t in texts]
        if column_map is None and "location" in lowered and "bids" in lowered:
            column_map = [HEADER_FIELDS.get(t.lower()) for t in texts]
            continue
        if column_map is None:
            continue
        # The table repeats its header row at the end of <tbody>;
        # skip it (and any other header-labelled row) explicitly.
        if texts and texts[0].lower() == "location":
            continue
        fields: dict[str, Any] = {}
        for idx, text in enumerate(texts):
            if idx >= len(column_map):
                break
            field_name = column_map[idx]
            if field_name is None:
                continue
            if field_name in _MONEY_FIELDS:
                fields[field_name] = _money(text)
            elif field_name == "delivery_month":
                fields["delivery_raw"] = text or None
            elif field_name == "location":
                fields["location"] = text or None
            elif field_name == "commodity":
                fields["commodity"] = text or None
            else:
                fields[field_name] = text or None
        delivery_raw = fields.get("delivery_raw")
        if delivery_raw and normalize_delivery_label(
            delivery_raw
        ) == delivery_raw.strip().rstrip(".").strip():
            # Normalisation left the label unchanged and it does not
            # already look like "%b %Y" — flag it, keep it verbatim.
            if not re.match(r"^[A-Z][a-z]{2} \d{4}$", delivery_raw.strip()):
                unparsed_deliveries.add(delivery_raw)
        row = _make_row(
            company=company,
            source_key=source_key,
            location=fields.get("location") or default_location,
            commodity=_canonical_commodity(fields.get("commodity")),
            fields=fields,
            currency=currency,
        )
        if row is not None:
            rows.append(row)

    if unparsed_deliveries:
        notes.append(
            "delivery label(s) kept verbatim (no normalisation rule): "
            + ", ".join(sorted(unparsed_deliveries))
        )
    location = rows[0]["location"] if rows else default_location
    if not rows:
        return _result(
            company=company,
            location=location,
            rows=[],
            status="empty",
            notes=notes + ["bid table found but no bid rows parsed"],
        )
    as_of = rows[0].get("date")
    if as_of:
        notes.append(f"trade date: {as_of}")
    return _result(
        company=company, location=location, rows=rows, status="ok", notes=notes
    )


def fetch_wpdatatables_html(url: str, timeout: int = 30) -> str:
    """One polite GET with the contact User-Agent."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_wpdatatables(
    url: str,
    *,
    company: str | None = None,
    currency: str = "USD",
    site: WpDataTablesSite | None = None,
    default_location: str | None = None,
) -> dict[str, Any]:
    """Fetch and parse wpDataTables cash bids from ``url`` in one call."""
    return parse_wpdatatables_html(
        fetch_wpdatatables_html(url),
        company=company,
        currency=currency,
        site=site,
        default_location=default_location,
    )


def get_wpdatatables_site(key: str) -> WpDataTablesSite:
    normalized = key.strip().lower()
    if normalized not in WPDATATABLES_SITES:
        raise KeyError(f"Unknown wpDataTables site '{key}'")
    return WPDATATABLES_SITES[normalized]


def fetch_wpdatatables_site(key: str) -> dict[str, Any]:
    """Fetch a configured wpDataTables site. Only verified sites may
    run — unverified entries need one live check of the page first,
    so a typo or a premature enable cannot silently scrape an
    unconfirmed page shape."""
    site = get_wpdatatables_site(key)
    if not site.verified:
        return _result(
            company=site.company,
            location=site.default_location,
            rows=[],
            status="unsupported",
            notes=[
                f"site '{key}' is not verified yet: {site.notes or 'live page shape unconfirmed'}",
                "Fetch the page once by hand and confirm the "
                "Location/Bids table, locations and currency before "
                "marking it verified.",
            ],
        )
    return fetch_wpdatatables(site.url, site=site)


def fetch_five_star_coop() -> dict[str, Any]:
    """Fetch Five Star Coop (New Hampton, IA) cash bids.

    Verified live 2026-11-19: 200, wpDataTables table_1 in static
    HTML, 299 rows (Corn 197 + Soybeans 102), 21 locations, USD/bu.
    """
    return fetch_wpdatatables_site("five_star_coop")
