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

Cycle 5 (2026-11-19) verified the remaining 9 registry sites live
(one polite GET each) — all 200, all with a ``.cbmod`` widget, all
parsed by this module after three small shape fixes:

  * 6-column widget (Chandler Feed, CGS): Delivery | Bid | Basis |
    Futures | Change | Futures Month (no Last Trade). Header-driven,
    so no new code was needed for the column count itself.
  * Fractional futures/change notation (Chandler, Forest River):
    CBOT-style eighths, e.g. "433-2" / "-2-2" / "+0-6". ``_money``
    converts these to decimal in the same unit as published
    (433-2 -> 433.25, -2-2 -> -2.25). See the units note below.
  * Classless location h2 (Chandler, Rugby): the widget's location
    heading sometimes carries no ``fcControls`` class; any classless
    h2 inside the widget is now read as the location label.
  * "Cash Price" header (Forest River's #1 Spring Wheat section):
    the Bid column is headed "Cash Price" and the Delivery header
    cell is blank; the parser maps "cash price" and treats a blank
    first header cell as the delivery column.

Cycle 7 (2026-11-19) verified the AGP iframe target
(``agp.o.bushelsites.com/cash-bids``, behind ``agp.com/grain/bids``)
live — one polite GET, 200, standard 7-column ``.cbmod`` widget,
parsed by the generic parser with no changes. The page carries a
single location/row (Chester, NE, Soybeans, Nov 2026, USD/bu).

Units — published numbers, NOT normalized: futures and change keep
the units each site publishes, and those vary. Decimal sites publish
futures in dollars (FAC 4.3325) and change in cents (FAC -2.25) or
in dollars (Cameron, Lake Norden: -0.0225). Fractional sites publish
both in cents (433-2 -> 433.25 futures, -2-2 -> -2.25 change).
Consumers must not assume one unit for these two fields. Bid and
basis are dollars per bushel (or per tonne for $/t commodities) on
every site checked.

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
AGP_URL = "https://agp.o.bushelsites.com/cash-bids"
SYNERGY_URL = "https://www.synergycoop.com"

# Raw widget commodity label -> canonical commodity name.
COMMODITY_MAP = {
    "corn": "Corn",
    "soybeans": "Soybeans",
    "soybean": "Soybeans",
    "soft red wheat": "Wheat — SRW",
    "hard red winter wheat (protein in)": "Wheat — HRW",
    "hard red winter wheat": "Wheat — HRW",
    "hard red spring wheat (protein in)": "Wheat — HRS",
    "hard red spring wheat": "Wheat — HRS",
    "soft white wheat": "Wheat — SWW",
    # "Wheat - HRS" style labels (Rugby) and grade-prefixed labels
    # ("#1 Spring Wheat", "#2 Yellow Corn" — Forest River).
    "wheat - hrs": "Wheat — HRS",
    "wheat - hrw": "Wheat — HRW",
    "wheat - srw": "Wheat — SRW",
    "wheat - sww": "Wheat — SWW",
    "#1 spring wheat": "Wheat — HRS",
    "#2 yellow corn": "Corn",
    "#2 yellow soybeans": "Soybeans",
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
# 5-column widget layouts and the real-<table> fallback. "cash price"
# is the Bid heading on Forest River's #1 Spring Wheat section.
HEADER_FIELDS = {
    "delivery": "delivery_month",
    "bid": "cash_price",
    "cash price": "cash_price",
    "basis": "basis",
    "futures": "futures_price",
    "change": "change",
    "futures month": "futures_month",
    "last trade": "last_trade",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
# CBOT-style fractional quote: whole cents + eighths, e.g. "433-2"
# (= 433 2/8), "-2-2", "+0-6". Used for futures/change on Chandler
# Feed and Forest River; decimal sites publish "4.3325" / "-2.25".
_FRAC_RE = re.compile(r"^([+-]?)(\d+)-([0-7])$")
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
    # Cycle 5 (2026-11-19): all remaining registry sites verified live,
    # one polite GET each — every one 200 with a .cbmod widget, parsed
    # by the generic parser (see the module docstring for the three
    # shape fixes this sweep required). All USD/bu unless noted.
    "chandler_feed": BushelSite(
        key="chandler_feed",
        company="Chandler Feed",
        url="https://chandlerfeed.o.bushelsites.com",
        currency="USD",
        default_location="Chandler",
        verified=True,
        notes="Verified live 2026-11-19: 200, homepage .cbmod widget, "
        "17 rows, 6-col layout (no Last Trade), corn/oats/soy, "
        "USD/bu. Futures/change in fractional cents notation "
        "('433-2' -> 433.25). Classless location h2 ('Chandler'). "
        "Footer lists Chandler, Edgerton and Woodstock, MN locations; "
        "the widget shows Chandler only. The 'dtn' string in the page "
        "is inside a base64 blob, not a DTN widget; the footer reads "
        "'Data provided by Bushel'.",
    ),
    "cameron_coop": BushelSite(
        key="cameron_coop",
        company="Cameron Coop",
        url="https://www.cameroncoop.com/",
        currency="USD",
        default_location="Cameron",
        verified=True,
        location_labels={"Cameron Coop": "Cameron"},
        notes="Verified live 2026-11-19: 200, homepage .cbmod widget, "
        "4 rows, 7-col layout, corn/soy, USD/bu. Change published in "
        "dollars (-0.0225), unlike FAC's cents. Footer address: "
        "Cameron, MO 64429.",
    ),
    "cgs": BushelSite(
        key="cgs",
        company="CGS",
        url="https://www.cgscoop.net/",
        currency="USD",
        default_location="Bazine",
        verified=True,
        location_labels={"CGS": "Bazine"},
        notes="Verified live 2026-11-19: 200, homepage .cbmod widget, "
        "4 rows, 6-col layout (no Last Trade), wheat/milo/corn, "
        "USD/bu. Footer address: Bazine, KS 67516.",
    ),
    "almota": BushelSite(
        key="almota",
        company="Almota Elevator",
        url="https://www.almotagrain.com/cash-bids",
        currency="USD",
        per_tonne_commodities=frozenset({"Barley"}),
        default_location="Colfax",
        verified=True,
        location_labels={"Almota Elevator Co.": "Colfax"},
        notes="Verified live 2026-11-19: 200, 7-col .cbmod widget, "
        "12 rows, soft white wheat / hard red winter wheat / barley, "
        "USD. DTN ambiguity resolved: the page's only 'dtn' string "
        "is inside a base64 blob; the bids render in the Bushel "
        "widget (footer: 'Data provided by Bushel'). Barley rows are "
        "Bid-only at per-tonne scale (165 vs ~6/bu wheat), so Barley "
        "is $/t by scale inference. Footer address: Colfax, WA 99111.",
    ),
    "williams_gin": BushelSite(
        key="williams_gin",
        company="Williams Gin & Grain",
        url="https://williamsginandgrain.com/cashbidssingle-",
        currency="USD",
        verified=True,
        notes="Verified live 2026-11-19: 200 at the URL as given — the "
        "trailing '-' is the real path, not truncation: the page "
        "loads, no redirect, and the site's own nav links to "
        "'/cashbidssingle-'. 7-col .cbmod widget, 2 rows, corn "
        "('As Harvested') + grain sorghum ('Harvest'), USD/bu. "
        "Location label is the company name; town unconfirmed from "
        "the page (catalogue says North Dakota).",
    ),
    "rugby": BushelSite(
        key="rugby",
        company="Rugby Farmers Elevator",
        url="https://www.rugbyfarmers.com/",
        currency="USD",
        default_location="Rugby",
        verified=True,
        location_labels={"Rugby & York Bids": "Rugby"},
        notes="Verified live 2026-11-19: 200, homepage .cbmod widget, "
        "12 rows, 5-col layout (no Futures Month / Last Trade), "
        "HRS wheat/soy/corn, USD/bu. Classless location h2 "
        "('Rugby & York Bids') — the page covers Rugby & York; rows "
        "are labelled Rugby (footer: 201 Dewey St SE, Rugby, ND "
        "58368). Willow City receiving hours are also on the page.",
    ),
    "lake_norden": BushelSite(
        key="lake_norden",
        company="Lake Norden Farmers Elevator",
        url="https://www.lakenordenfarmerselevator.net/cash-bids",
        currency="USD",
        default_location="Lake Norden",
        verified=True,
        notes="Verified live 2026-11-19: 200, 7-col .cbmod widget, "
        "2 rows, corn ('Nc 2026') + soy ('Cash'), USD/bu. Change "
        "published in dollars (-0.0225), unlike FAC's cents. Footer "
        "address: Lake Norden, SD 57248.",
    ),
    "united_coop": BushelSite(
        key="united_coop",
        company="United Cooperative",
        url="https://www.unitedcoop.com/cash-bids",
        currency="USD",
        default_location="Webster City",
        verified=True,
        location_labels={"United Coop Cash Bids": "Webster City"},
        notes="Verified live 2026-11-19: 200, 7-col .cbmod widget, "
        "12 rows, corn/soy, USD/bu. Footer contact is 1932 W 2nd St, "
        "Webster City, IA 50595 — NOT Beaver Dam, WI as the catalogue "
        "said; the catalogue town is contradicted by the live page. "
        "Same-org question vs Batch 4 unitedcooperative.com is "
        "UNRESOLVED: the Bushel portal slug is 'unitedcooperative' "
        "but the page never links that domain, and the IA address "
        "does not match the WI org — possibly two orgs sharing a "
        "name. Needs one check of unitedcooperative.com.",
    ),
    "forest_river": BushelSite(
        key="forest_river",
        company="Forest River Coop",
        url="https://www.forestrivercoop.com/",
        currency="USD",
        default_location="Forest River",
        verified=True,
        notes="Verified live 2026-11-19: 200, homepage .cbmod widget, "
        "3 rows, 7-col layout, USD/bu. Grade-prefixed commodity "
        "labels ('#1 Spring Wheat', '#2 Yellow Corn', '#2 Yellow "
        "Soybeans'). First section heads Bid as 'Cash Price' with a "
        "blank Delivery header; futures/change in fractional cents "
        "notation ('630-0' -> 630.25). Footer address: Forest River, "
        "ND 58233.",
    ),
    "ace_ethanol": BushelSite(
        key="ace_ethanol",
        company="Ace Ethanol",
        url="https://www.aceethanol.com/cash-bids",
        currency="USD",
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 6 DTN sweep): 200, "
        "Bushel .cbmod widget in static HTML, 11 rows Corn, 7-col.",
    ),
    "alliance_grain": BushelSite(
        key="alliance_grain",
        company="Alliance Grain",
        url="https://www.alliance-grain.com/cash-bids",
        currency="USD",
        default_location="Gibson City",
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 6 DTN sweep): 200, "
        "Bushel .cbmod widget in static HTML, 10 rows (Corn 5 + "
        "Soybeans 5), 7-col; location h2 'Gibson City - West'.",
    ),
    "agp": BushelSite(
        key="agp",
        company="AGP",
        url=AGP_URL,
        currency="USD",
        default_location="Chester",
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 7): 200, Bushel .cbmod "
        "widget in static HTML at the iframe target behind "
        "agp.com/grain/bids, parsed by the generic parser with no "
        "changes (status ok). Only 1 row on the page: Chester, NE, "
        "Soybeans, Nov 2026, 7-col layout, USD/bu; widget header "
        "dated Nov 18, 2026 11:40 PM. The iframe page shows a single "
        "location — other AGP locations are not on this page.",
    ),
    "synergy": BushelSite(
        key="synergy",
        company="Synergy Cooperative",
        url=SYNERGY_URL,
        currency="USD",
        default_location="Cameron",
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 10 sweep): 200, Bushel "
        ".cbmod widget in static HTML, 4 rows (Corn 2 + Soybeans 2, "
        "Cameron), 6-col layout, USD/bu; widget header dated Nov 19, "
        "2026. Generic parser returns status ok against saved HTML.",
    ),
}


def _money(text: str | None) -> float | None:
    """Parse a plain number like '5.58' / '-0.35' / '4.3325' to float.

    Also handles CBOT-style fractional quotes '433-2' (433 2/8) and
    '-2-2' / '+0-6', converting to decimal in the same unit as
    published (cents for those sites — see the module docstring).
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
    # on one page; Collwest has 1). The location h2 usually carries
    # class fcControls, but Chandler Feed and Rugby render it classless,
    # so a classless h2 counts too (a "Cash Bids" title h2 never does).
    for element in widget.descendants:
        if not getattr(element, "name", None):
            continue
        classes = element.get("class") or []
        if element.name == "h2" and ("fcControls" in classes or not classes):
            text = element.get_text(" ", strip=True)
            if text and "cash bid" not in text.lower():
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
            # A blank first header cell is still the delivery column
            # (Forest River's #1 Spring Wheat section leaves it blank
            # and heads the Bid column "Cash Price").
            column_map = [
                HEADER_FIELDS.get(cell.get_text(" ", strip=True).lower())
                or ("delivery_month" if idx == 0 else None)
                for idx, cell in enumerate(cells)
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


def fetch_chandler_feed() -> dict[str, Any]:
    """Fetch Chandler Feed (Chandler, MN). Verified live 2026-11-19."""
    return fetch_bushel_site("chandler_feed")


def fetch_cameron_coop() -> dict[str, Any]:
    """Fetch Cameron Coop (Cameron, MO). Verified live 2026-11-19."""
    return fetch_bushel_site("cameron_coop")


def fetch_cgs() -> dict[str, Any]:
    """Fetch CGS (Bazine, KS). Verified live 2026-11-19."""
    return fetch_bushel_site("cgs")


def fetch_almota() -> dict[str, Any]:
    """Fetch Almota Elevator (Colfax, WA). Verified live 2026-11-19."""
    return fetch_bushel_site("almota")


def fetch_williams_gin() -> dict[str, Any]:
    """Fetch Williams Gin & Grain. Verified live 2026-11-19."""
    return fetch_bushel_site("williams_gin")


def fetch_rugby() -> dict[str, Any]:
    """Fetch Rugby Farmers Elevator (Rugby, ND). Verified live 2026-11-19."""
    return fetch_bushel_site("rugby")


def fetch_lake_norden() -> dict[str, Any]:
    """Fetch Lake Norden Farmers Elevator (Lake Norden, SD). Verified live 2026-11-19."""
    return fetch_bushel_site("lake_norden")


def fetch_united_coop() -> dict[str, Any]:
    """Fetch United Cooperative (Webster City, IA). Verified live 2026-11-19."""
    return fetch_bushel_site("united_coop")


def fetch_forest_river() -> dict[str, Any]:
    """Fetch Forest River Coop (Forest River, ND). Verified live 2026-11-19."""
    return fetch_bushel_site("forest_river")


def fetch_ace_ethanol() -> dict[str, Any]:
    """Fetch Ace Ethanol. Verified live 2026-11-19 (Cycle 6 DTN sweep)."""
    return fetch_bushel_site("ace_ethanol")


def fetch_alliance_grain() -> dict[str, Any]:
    """Fetch Alliance Grain (Gibson City). Verified live 2026-11-19 (Cycle 6 DTN sweep)."""
    return fetch_bushel_site("alliance_grain")


def fetch_agp() -> dict[str, Any]:
    """Fetch AGP (Chester, NE) via the iframe target behind agp.com.

    Verified live 2026-11-19 (Cycle 7): 200, Bushel .cbmod widget in
    static HTML, 1 row (Soybeans, Nov 2026), USD/bu.
    """
    return fetch_bushel_site("agp")


def fetch_synergy() -> dict[str, Any]:
    """Fetch Synergy Cooperative (Cameron, WI). Verified live 2026-11-19
    (Cycle 10 sweep): 200, Bushel .cbmod widget in static HTML, 4 rows
    (Corn 2 + Soybeans 2), 6-col layout, USD/bu.
    """
    return fetch_bushel_site("synergy")
