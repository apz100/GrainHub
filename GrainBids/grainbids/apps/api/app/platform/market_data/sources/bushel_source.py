"""Generic Bushel-pattern cash-bid collector.

Covers the Bushel Sites platform (``o.bushelsites.com`` hosting, branded
domains fronting it): one parser, per-site config for URL / currency /
units / location. Verified live 2026-11-19 (one polite GET each):

  FAC (Farmers Cooperative Elevator Co.), Arcadia, IA
      https://www.faccooperative.com/cash-bids — 200
  Collwest Grain, Ltd., Collingwood, ON
      https://www.collwestgrain.com/ — 200

Correction to docs/plans/bushel-collector-research.md: on BOTH sites the
cash bids live in the ``.cbmod`` div widget — NOT in a ``<table>``. FAC's
single ``table.standardTable`` is a 4-row "Data provided by Bushel"
footer, and Collwest's ``table.market_table`` is the futures market
table (headers Contract / Last / Chg / ...). The widget shape is what
varies and what this parser handles:

  FAC       .cbCommodity > ul.sevenColumnsBigFirst (7 cols):
            Delivery | Bid | Basis | Futures | Change | Futures Month | Last Trade
            Delivery labels are months: "November '26" ... "Oct. / Nov. '27".
            Three locations on one page (.cashBidLocation h2 each):
            Arcadia, Schleswig, AGP Manning. USD per bushel.
  Collwest  .cbCommodity > ul.fiveColumnsBigFirst (5 cols):
            Delivery | Bid | Basis | Futures | Change
            Delivery labels are crop years: "2026 Crop", "2027 Crop".
            One location ("Collwest"). CAD; corn/soy/wheat per bushel,
            canola / barley / oats per tonne. Barley and oats rows are
            thin: Bid only, Basis / Futures / Change cells empty.

Fallback: if no ``.cbmod`` widget is present, a real ``<table>`` is
parsed only when its header row contains both "Delivery" and "Bid"
(class ``standardTable`` / ``market_table`` or any other). That guard
keeps Collwest's futures market table from ever being read as bids.

Rows never contain invented values: unparseable or absent cells become
None, with a ``note`` explaining what is missing (thin rows, missing
basis/futures). ``cash_price_mt`` is the published per-tonne bid for
``$/t`` commodities (same number, not a conversion); it is None for
``$/bu`` commodities because no per-tonne price is published.

Return shape (matches the other direct_dict collectors):
{"company", "location", "rows", "status", "notes"} where ``status`` is
"ok" (rows found), "empty" (widget/table present but no parseable rows)
or "unsupported" (no recognizable bid structure). ``location`` is the
first location seen on the page (FAC pages carry several; every row
carries its own location).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import requests
from bs4 import BeautifulSoup

CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

FAC_URL = "https://www.faccooperative.com/cash-bids"
COLLWEST_URL = "https://www.collwestgrain.com/"

# Raw widget commodity label -> canonical commodity name.
COMMODITY_MAP = {
    "corn": "Corn",
    "soybeans": "Soybeans",
    "soybean": "Soybeans",
    "soft red wheat": "Wheat — SRW",
    "hard red winter wheat (protein in)": "Wheat — HRW",
    "hard red spring wheat (protein in)": "Wheat — HRS",
    "soft white wheat": "Wheat — SWW",
    "wheat": "Wheat",
    "canola": "Canola",
    "barley": "Barley",
    "oats": "Oats",
    "milo": "Milo",
    "grain sorghum": "Grain Sorghum",
    "sorghum": "Grain Sorghum",
    "durum": "Durum",
    "sunflowers": "Sunflowers",
    "sunflower": "Sunflowers",
    "flax": "Flax",
    "rye": "Rye",
    "peas": "Peas",
    "lentils": "Lentils",
}

# Header label (lowercased) -> row field. Covers both the 7-column and
# 5-column widget layouts and the real-<table> fallback.
HEADER_FIELDS = {
    "delivery": "delivery_month",
    "bid": "cash_price",
    "basis": "basis",
    "futures": "futures_price",
    "change": "change",
    "futures month": "futures_month",
    "last trade": "last_trade",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_MONEY_FIELDS = {"cash_price", "basis", "futures_price", "change"}


@dataclass(frozen=True)
class BushelSite:
    """Per-site config — no per-site code."""

    key: str
    company: str
    url: str
    currency: str
    # Canonical commodity -> unit. Anything not listed is "$/bu".
    per_tonne_commodities: frozenset[str] = frozenset()
    default_location: str | None = None
    # True only once the live page has been fetched and the widget shape
    # confirmed. Unverified sites stay in the registry as documentation
    # of the catalogue entries, but fetch_bushel_site() refuses them.
    verified: bool = False
    # Widget h2 -> canonical location. The widget's location label is
    # usually a town (FAC: "Arcadia"), but Collwest's h2 is the company
    # short name ("Collwest") while the town is Collingwood.
    location_labels: dict[str, str] = field(default_factory=dict)
    notes: str = ""


BUSHEL_SITES: dict[str, BushelSite] = {
    "fac": BushelSite(
        key="fac",
        company="FAC",
        url=FAC_URL,
        currency="USD",
        default_location="Arcadia",
        verified=True,
        notes="Verified live 2026-11-19: 7-col widget, month delivery "
        "labels, 3 locations on one page (Arcadia, Schleswig, "
        "AGP Manning), corn + soybeans, USD/bu.",
    ),
    "collwest": BushelSite(
        key="collwest",
        company="Collwest Grain",
        url=COLLWEST_URL,
        currency="CAD",
        per_tonne_commodities=frozenset({"Canola", "Barley", "Oats"}),
        default_location="Collingwood",
        verified=True,
        location_labels={"Collwest": "Collingwood"},
        notes="Verified live 2026-11-19: 5-col widget, crop-year "
        "delivery labels, thin Bid-only barley/oats rows, CAD; "
        "canola/barley/oats per tonne, corn/soy/wheat per bushel. "
        "Canadian — Ontario panel, not US. (Also covered by the "
        "older collwest_source.py widget parser.)",
    ),
    # Catalogue entries whose live page has NOT been fetched yet. The
    # generic parser should cover them (same Bushel Sites platform),
    # but each needs one polite GET to confirm widget vs table shape,
    # locations, and currency before it is marked verified.
    "chandler_feed": BushelSite(
        key="chandler_feed",
        company="Chandler Feed",
        url="https://chandlerfeed.o.bushelsites.com",
        currency="USD",
        notes="Unverified — homepage-only URL, table location unknown.",
    ),
    "cameron_coop": BushelSite(
        key="cameron_coop",
        company="Cameron Coop",
        url="https://www.cameroncoop.com/",
        currency="USD",
        notes="Unverified — homepage-only URL, table location unknown.",
    ),
    "cgs": BushelSite(
        key="cgs",
        company="CGS",
        url="https://www.cgscoop.net/",
        currency="USD",
        notes="Unverified — homepage-only URL, table location unknown.",
    ),
    "almota": BushelSite(
        key="almota",
        company="Almota Elevator",
        url="https://www.almotagrain.com/cash-bids",
        currency="USD",
        notes="Unverified — HTML also carries a DTN reference; confirm "
        "which widget actually renders the bids.",
    ),
    "williams_gin": BushelSite(
        key="williams_gin",
        company="Williams Gin & Grain",
        url="https://williamsginandgrain.com/cashbidssingle-",
        currency="USD",
        notes="Unverified — URL path looks truncated; confirm the "
        "canonical cash-bids URL before enabling.",
    ),
    "rugby": BushelSite(
        key="rugby",
        company="Rugby Farmers Elevator",
        url="https://www.rugbyfarmers.com/",
        currency="USD",
        notes="Unverified — homepage-only URL, table location unknown.",
    ),
    "lake_norden": BushelSite(
        key="lake_norden",
        company="Lake Norden Farmers Elevator",
        url="https://www.lakenordenfarmerselevator.net/cash-bids",
        currency="USD",
    ),
    "united_coop": BushelSite(
        key="united_coop",
        company="United Cooperative",
        url="https://www.unitedcoop.com/cash-bids",
        currency="USD",
        notes="Unverified — confirm same org as Batch 4 "
        "unitedcooperative.com.",
    ),
    "forest_river": BushelSite(
        key="forest_river",
        company="Forest River Coop",
        url="https://www.forestrivercoop.com/",
        currency="USD",
        notes="Unverified — homepage-only URL, table location unknown.",
    ),
}


def _money(text: str | None) -> float | None:
    """Parse a plain number like '5.58' / '-0.35' / '4.3325' to float."""
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


def _unit_for(commodity: str, site: BushelSite | None) -> str:
    if site is not None and commodity in site.per_tonne_commodities:
        return "$/t"
    return "$/bu"


def _canonical_commodity(raw: str) -> str:
    return COMMODITY_MAP.get(raw.strip().lower(), raw.strip() or "Unknown")


def _make_row(
    *,
    company: str,
    location: str | None,
    commodity: str,
    fields: dict[str, Any],
    currency: str,
    site: BushelSite | None,
) -> dict[str, Any]:
    """Build one normalized row; missing values stay None with a reason."""
    unit = _unit_for(commodity, site)
    cash_price = fields.get("cash_price")
    missing = [
        label
        for label, value in (
            ("basis", fields.get("basis")),
            ("futures", fields.get("futures_price")),
            ("change", fields.get("change")),
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
        "delivery_month": fields.get("delivery_month"),
        "cash_price": cash_price,
        # Published per-tonne bid for $/t commodities (same number, not
        # a conversion); None for $/bu commodities — no per-tonne price
        # is published.
        "cash_price_mt": cash_price if unit == "$/t" else None,
        "basis": fields.get("basis"),
        "futures_price": fields.get("futures_price"),
        "futures_month": fields.get("futures_month"),
        "last_trade": fields.get("last_trade"),
        "change": fields.get("change"),
        "currency": currency,
        "unit": unit,
        "note": note,
    }


def _parse_widget(
    widget: Any,
    *,
    company: str,
    currency: str,
    site: BushelSite | None,
    notes: list[str],
) -> list[dict[str, Any]]:
    """Parse the .cbmod div widget (verified shape on FAC + Collwest)."""
    rows: list[dict[str, Any]] = []
    location = site.default_location if site else None

    # Walk the widget in document order so each commodity section picks
    # up the .cashBidLocation h2 that precedes it (FAC has 3 locations
    # on one page; Collwest has 1).
    for element in widget.descendants:
        if not getattr(element, "name", None):
            continue
        classes = element.get("class") or []
        if element.name == "h2" and "fcControls" in classes:
            text = element.get_text(" ", strip=True)
            if text:
                location = (
                    site.location_labels.get(text, text) if site else text
                )
        if element.name == "div" and "cbCommodity" in classes:
            rows.extend(
                _parse_commodity_section(
                    element,
                    company=company,
                    location=location,
                    currency=currency,
                    site=site,
                )
            )

    header = widget.find("p", class_="fcControlsSectionHeader")
    if header:
        as_of = header.get_text(" ", strip=True)
        if as_of:
            notes.append(f"widget header: {as_of}")
    return rows


def _parse_commodity_section(
    section: Any,
    *,
    company: str,
    location: str | None,
    currency: str,
    site: BushelSite | None,
) -> list[dict[str, Any]]:
    heading = section.find("h3")
    raw_name = heading.get_text(" ", strip=True) if heading else ""
    commodity = _canonical_commodity(raw_name)
    rows: list[dict[str, Any]] = []
    column_map: list[str | None] | None = None

    for row_ul in section.find_all("ul"):
        classes = " ".join(row_ul.get("class") or [])
        cells = row_ul.find_all("li")
        if "fcControlsSubHdr" in classes:
            # Header row: map column positions from the labels, so 5-col
            # and 7-col layouts (and any reordering) are handled.
            column_map = [
                HEADER_FIELDS.get(cell.get_text(" ", strip=True).lower())
                for cell in cells
            ]
            continue
        if "fcControls1" not in classes and "fcControls2" not in classes:
            continue
        if column_map is None:
            # No header seen (defensive): fall back to the ul class.
            if "sevenColumnsBigFirst" in classes:
                column_map = [
                    "delivery_month",
                    "cash_price",
                    "basis",
                    "futures_price",
                    "change",
                    "futures_month",
                    "last_trade",
                ]
            else:  # fiveColumnsBigFirst and anything else
                column_map = [
                    "delivery_month",
                    "cash_price",
                    "basis",
                    "futures_price",
                    "change",
                ]
        fields: dict[str, Any] = {}
        for idx, cell in enumerate(cells):
            if idx >= len(column_map):
                break
            field_name = column_map[idx]
            if field_name is None:
                continue
            if field_name == "delivery_month":
                span = cell.find("span", class_="cashBidsColumnOne")
                fields[field_name] = (
                    span.get_text(" ", strip=True)
                    if span
                    else cell.get_text(" ", strip=True)
                )
            elif field_name in _MONEY_FIELDS:
                fields[field_name] = _money(cell.get_text(" ", strip=True))
            else:
                fields[field_name] = cell.get_text(" ", strip=True) or None
        # Skip rows with no usable values at all (all-dash placeholder).
        if not fields.get("delivery_month") and all(
            fields.get(f) is None for f in _MONEY_FIELDS
        ):
            continue
        if all(fields.get(f) is None for f in _MONEY_FIELDS):
            continue
        rows.append(
            _make_row(
                company=company,
                location=location,
                commodity=commodity,
                fields=fields,
                currency=currency,
                site=site,
            )
        )
    return rows


def _parse_bid_table(
    table: Any,
    *,
    company: str,
    location: str | None,
    currency: str,
    site: BushelSite | None,
) -> list[dict[str, Any]]:
    """Parse a real <table> whose header has Delivery + Bid columns."""
    rows: list[dict[str, Any]] = []
    column_map: list[str | None] | None = None
    commodity = "Unknown"
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        texts = [c.get_text(" ", strip=True) for c in cells]
        lowered = [t.lower() for t in texts]
        if column_map is None and "delivery" in lowered and "bid" in lowered:
            column_map = [HEADER_FIELDS.get(t.lower()) for t in texts]
            continue
        if column_map is None:
            # A lone non-empty first cell before the header is a
            # commodity section heading.
            if len(texts) == 1 and texts[0]:
                commodity = _canonical_commodity(texts[0])
            continue
        if len(texts) == 1 and texts[0]:
            commodity = _canonical_commodity(texts[0])
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
                fields[field_name] = text or None
            else:
                fields[field_name] = text or None
        if all(fields.get(f) is None for f in _MONEY_FIELDS):
            continue
        rows.append(
            _make_row(
                company=company,
                location=location,
                commodity=commodity,
                fields=fields,
                currency=currency,
                site=site,
            )
        )
    return rows


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


def parse_bushel_html(
    html: str,
    *,
    company: str | None = None,
    currency: str = "USD",
    site: BushelSite | None = None,
    default_location: str | None = None,
) -> dict[str, Any]:
    """Parse Bushel cash-bid HTML into normalized bid rows.

    ``site`` (a BUSHEL_SITES entry) supplies company / currency /
    per-tonne commodities / default location; the keyword arguments
    override it for ad-hoc pages. Returns {"company", "location",
    "rows", "status", "notes"}; see the module docstring.
    """
    if site is not None:
        company = company or site.company
        currency = site.currency
        default_location = default_location or site.default_location
    company = company or "Unknown Bushel site"
    notes: list[str] = []
    if site is not None and site.notes:
        notes.append(f"site config: {site.notes}")

    soup = BeautifulSoup(html, "lxml")

    widget = soup.find("div", class_="cbmod")
    if widget is not None:
        rows = _parse_widget(
            widget, company=company, currency=currency, site=site, notes=notes
        )
        location = rows[0]["location"] if rows else default_location
        if not rows:
            return _result(
                company=company,
                location=location,
                rows=[],
                status="empty",
                notes=notes + ["cash-bid widget found but no bid rows parsed"],
            )
        return _result(
            company=company, location=location, rows=rows, status="ok", notes=notes
        )

    # No widget: fall back to a real <table> only if its header row
    # carries Delivery + Bid (a genuine cash-bids table). A futures
    # market table (Contract / Last / Chg) never qualifies.
    for table in soup.find_all("table"):
        header_texts = [
            c.get_text(" ", strip=True).lower()
            for tr in table.find_all("tr")
            for c in tr.find_all(["th", "td"])
        ]
        if "delivery" not in header_texts or "bid" not in header_texts:
            continue
        rows = _parse_bid_table(
            table,
            company=company,
            location=default_location,
            currency=currency,
            site=site,
        )
        if rows:
            return _result(
                company=company,
                location=default_location,
                rows=rows,
                status="ok",
                notes=notes + ["parsed cash-bids <table> (no .cbmod widget found)"],
            )
        return _result(
            company=company,
            location=default_location,
            rows=[],
            status="empty",
            notes=notes + ["cash-bids table found but no bid rows parsed"],
        )

    return _result(
        company=company,
        location=default_location,
        rows=[],
        status="unsupported",
        notes=notes
        + ["no cash-bid widget (.cbmod) or Delivery/Bid table found in page HTML"],
    )


def fetch_bushel_html(url: str, timeout: int = 30) -> str:
    """One polite GET with the contact User-Agent."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_bushel(
    url: str,
    *,
    company: str | None = None,
    currency: str = "USD",
    site: BushelSite | None = None,
    default_location: str | None = None,
) -> dict[str, Any]:
    """Fetch and parse Bushel cash bids from ``url`` in one call."""
    return parse_bushel_html(
        fetch_bushel_html(url),
        company=company,
        currency=currency,
        site=site,
        default_location=default_location,
    )


def get_bushel_site(key: str) -> BushelSite:
    normalized = key.strip().lower()
    if normalized not in BUSHEL_SITES:
        raise KeyError(f"Unknown Bushel site '{key}'")
    return BUSHEL_SITES[normalized]


def fetch_bushel_site(key: str) -> dict[str, Any]:
    """Fetch a configured Bushel site. Only verified sites may run —
    unverified catalogue entries need one live check first (see the
    registry notes), so a typo or a premature enable cannot silently
    scrape an unconfirmed page shape."""
    site = get_bushel_site(key)
    if not site.verified:
        return _result(
            company=site.company,
            location=site.default_location,
            rows=[],
            status="unsupported",
            notes=[
                f"site '{key}' is not verified yet: {site.notes or 'live page shape unconfirmed'}",
                "Fetch the page once by hand and confirm widget/table shape, "
                "locations and currency before marking it verified.",
            ],
        )
    return fetch_bushel(site.url, site=site)


def fetch_fac() -> dict[str, Any]:
    """Fetch FAC (Arcadia, IA) cash bids. Verified live 2026-11-19."""
    return fetch_bushel_site("fac")


def fetch_collwest_bushel() -> dict[str, Any]:
    """Fetch Collwest Grain (Collingwood, ON) via the generic collector.

    Same page the older collwest_source.py parses; kept as a second
    shape check for the generic parser (5-col widget, CAD, per-tonne
    canola/barley/oats).
    """
    return fetch_bushel_site("collwest")
