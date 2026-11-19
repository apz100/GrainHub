"""Generic AgriCharts ``cashbids.php`` embed collector.

Covers the AgriCharts cash-bids widget that co-ops embed with a
``<script src="...agricharts.com/inc/cashbids/cashbids.php?...">`` tag
(verified 2026-11-19, Cycle 7). The embed is a two-step JS chain, but
neither step needs a browser:

  1. ``cashbids.php`` returns a small JS loader (``text/javascript``,
     ~11.5 KB). It does NOT contain bid rows — it builds a second URL
     and XHRs it (``getACBids`` / ``acRunXHR`` in the loader source).
  2. ``cashbids-js.php`` (same host, same query params plus
     ``noscript=1`` / ``acCnt=1``) returns ``text/html`` containing a
     ``<script id="cb-functions">`` block with ``var bids = [...]`` —
     a JSON array of location groups, each with a ``cashbids`` array
     of bid objects — plus a ``table.cashbid_table``. The JSON is the
     parse target: it is present and complete on every site checked,
     while the rendered table is NOT reliable (Agtegra's table body
     is empty ``<tr class="odd/even">`` rows filled client-side from
     the JSON; the other eight sites server-render it).

Bid object fields used (all present on every row of all twelve sites
checked): ``name`` (commodity), ``symbol`` (e.g. ``ZCZ26``),
``delivery_start`` / ``delivery_end`` (``MM/DD/YYYY``), ``basismonth``
(``Dec 2026``), ``basis`` (integer cents, e.g. -90), ``futures`` /
``futureschange`` (CBOT fractional cents, e.g. ``433-2``),
``price`` / ``cashprice`` (``$``-prefixed dollars per bushel),
``cashpricetonne`` (``$``-prefixed dollars per tonne), ``change``
(``$``-prefixed dollars) / ``rawchange`` (float dollars),
``location_name`` (delivery point as published), ``require_login``,
``active``.

Units — documented conversions, not guesses: ``basis`` is integer
cents in the JSON, so basis dollars = cents / 100 (checked against
the published cash price: futures − basis ≈ cash). ``futures`` /
``futureschange`` are fractional cents, so futures dollars =
(cents) / 100 (``433-2`` → 433.25¢ → $4.3325). ``change`` /
``rawchange`` are already dollars. ``cash_price_mt`` is the published
``cashpricetonne`` (same number, not a conversion).

Location: each cashbid carries ``location_name`` — that is the row
location. Two sites group by commodity instead of location
(``groupby=ccommodity``: Ag State, Superior Ag), so the location
*group* name there is a commodity (``Corn`` / ``Soybeans``) and must
never be used as the location; ``location_name`` is authoritative.
Midway's embed publishes the location label ``All Locations`` (one
aggregated view); Ag State's only location label is ``A.C.`` — both
are recorded exactly as published, not expanded.

Rows never contain invented values: unparseable or absent cells
become None. Login-gated (``require_login``) or inactive rows are
skipped and counted in the notes, never silently dropped.

Return shape (matches the other direct_dict collectors):
{"company", "location", "rows", "status", "notes"} where ``status``
is "ok" (rows found), "empty" (payload present but no parseable
rows) or "unsupported" (no ``var bids`` JSON payload in the page).
``location`` is the first row's location.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

# The loader appends "&acCnt=<n>" to a widgetURL that already ends in
# "&", so a real browser request carries "&&acCnt=1". The registry
# URLs below reproduce exactly the URLs fetched and verified live
# 2026-11-19 (one polite GET each) — double ampersand included.
#
# Per-site embed hosts + location IDs (from the company pages, Cycle 6):
#   Agtegra        sdwg.agricharts.com            / 3135
#   Heritage Coop  heritagecoop.agricharts.com    / 21608
#   Linn Coop      linncoop.agricharts.com        / filter=all
#   Midway Coop    midwaycoop.agricharts.com      / 82270
#   Ag State       agstate.agricharts.com         / 84205
#   Superior Ag    superiorag-cb-jsi.agricharts.com / 82244
#   ALCIVIA        alciviacoop.agricharts.com     / filter=all
#   TGM            totalgrain.agricharts.com      / filter=all
#   PRO Coop       procooperative.agricharts.com  / 21297 (Ayrshire, IA)
#   PRO Coop 21302 procooperative.agricharts.com  / 21302 (Manson, IA)
#   Hull Coop      hullcoopresp.agricharts.com     / filter=all
#   StateLine Coop statelinecoop.agricharts.com    / filter=all

# Raw commodity label (lowercased, grade prefix stripped) -> canonical.
COMMODITY_MAP = {
    "corn": "Corn",
    "soybeans": "Soybeans",
    "soybean": "Soybeans",
    # TGM publishes soybeans under the label "Beans" (ZS symbols on
    # all 120 rows, verified live 2026-11-19, Cycle 9).
    "beans": "Soybeans",
    "wheat": "Wheat",
    "wheat srw": "Wheat — SRW",
    "wheat hrw": "Wheat — HRW",
    "wheat hrs": "Wheat — HRS",
    "wheat sww": "Wheat — SWW",
    "soft red wheat": "Wheat — SRW",
    "hard red winter wheat": "Wheat — HRW",
    "hard red spring wheat": "Wheat — HRS",
    "soft white wheat": "Wheat — SWW",
    "spring wheat": "Wheat — HRS",
    "winter wheat": "Wheat",
    "milo": "Milo",
    "grain sorghum": "Grain Sorghum",
    "sorghum": "Grain Sorghum",
    "oats": "Oats",
    "barley": "Barley",
    "canola": "Canola",
    "flax": "Flax",
    "millet": "Millet",
    "durum": "Durum",
    "rye": "Rye",
    "sunflowers": "Sunflowers",
    "sunflower": "Sunflowers",
    "nusuns": "Sunflowers",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
# CBOT-style fractional quote in cents: whole cents + eighths,
# e.g. "433-2" (= 433 2/8¢), "-2-2", "+0-6". Same notation as the
# Bushel collector's fractional futures/change.
_FRAC_RE = re.compile(r"^([+-]?)(\d+)-([0-7])$")
# Grade prefix on commodity labels, e.g. "#2 YELLOW CORN".
_GRADE_RE = re.compile(r"^#\d+\s+(?:yellow\s+)?", re.IGNORECASE)
# The JSON payload: <script id="cb-functions">var bids = [...];</script>
# The lookahead requires the opening bracket to be followed by "{" or
# "]" (array of objects or empty) so prose/comments mentioning the
# payload name cannot match.
_BIDS_RE = re.compile(r"var\s+bids\s*=\s*(?=\[\s*(?:\{|\]))(\[.*?\]);", re.S)
_BIDS_GREEDY_RE = re.compile(r"var\s+bids\s*=\s*(?=\[\s*(?:\{|\]))(\[.*\]);", re.S)


@dataclass(frozen=True)
class CashbidsEmbedSite:
    """Per-site config — no per-site code."""

    key: str
    company: str
    # The cashbids-js.php URL exactly as fetched and verified live
    # (loader widgetURL + "&acCnt=1"). Do not hand-edit the query
    # string: re-derive it from the site's cashbids.php loader.
    js_url: str
    currency: str = "USD"
    default_location: str | None = None
    # True only once the live cashbids-js.php response has been fetched
    # and the var-bids payload confirmed. Unverified sites stay out of
    # the registry; fetch_cashbids_embed_site() refuses unverified
    # entries the same way the Bushel collector does.
    verified: bool = False
    notes: str = ""


CASHBIDS_EMBED_SITES: dict[str, CashbidsEmbedSite] = {
    "agtegra": CashbidsEmbedSite(
        key="agtegra",
        company="Agtegra",
        js_url=(
            "https://sdwg.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=all&location=3135&commodity=&groupby=location&width="
            "&format=table&fields=%0Aname%2C%0Anotes%2C%0Abasismonth%2C%0A"
            "futures%2C%0Afutureschange%2C%0Abasis%2C%0Aprice%0A"
            "&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d"
            "%2F%25Y&months=8&noscript=1&enableScrollIntoView=1&&acCnt=1"
        ),
        default_location="Hecla",
        verified=True,
        notes="Verified live 2026-11-19: 200, var-bids JSON, 1 location "
        "(Hecla, SD), 8 Corn rows. NOTE: this site's rendered "
        "cashbid_fulltable body is empty client-filled rows — the JSON "
        "payload is the only static route. Embed at "
        "agtegra.com/cash-bids.",
    ),
    "heritage_coop": CashbidsEmbedSite(
        key="heritage_coop",
        company="Heritage Cooperative",
        js_url=(
            "https://heritagecoop.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=location&location=21608&commodity=&groupby=location"
            "&width=&showtimestamp=1&showchart=1&asp=1&enableScrollIntoView=1"
            "&format=table&fields=name%2Cdelivery_start%2Cdelivery_end"
            "%2Cbasismonth%2Cfutures%2Cfutureschange%2Cbasis%2Cprice%2Cnotes"
            "&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d"
            "%2F%25Y&months=8&locations=&commodities=&&acCnt=1"
        ),
        default_location="Ada",
        verified=True,
        notes="Verified live 2026-11-19: 200, var-bids JSON, 1 location "
        "(Ada, OH), 15 rows (Corn 7, Soybeans 7, Wheat SRW 1). Embed at "
        "heritagecooperative.com/grain/cash-bids.",
    ),
    "linn_coop": CashbidsEmbedSite(
        key="linn_coop",
        company="Linn Coop",
        js_url=(
            "https://linncoop.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=all&location=&commodity=&groupby=location&width="
            "&format=table&fields=name%2Cdelivery_start%2Cdelivery_end"
            "%2Cbasismonth%2Cfutures%2Cfutureschange%2Cbasis%2Cprice%2Cnotes"
            "&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d"
            "%2F%25Y&months=8&&acCnt=1"
        ),
        verified=True,
        notes="Verified live 2026-11-19: 200, var-bids JSON, 5 locations "
        "(ADM, Alburnett & Springville Elevator, Cargill (Beans), "
        "Cargill (Starch), Ingredion — all Cedar Rapids / Alburnett, "
        "IA), 51 rows (#2 Yellow Corn 39, Soybeans 12). filter=all, no "
        "single default location. Embed at linncoop.com/grain/cash-bids.",
    ),
    "midway_coop": CashbidsEmbedSite(
        key="midway_coop",
        company="Midway Coop",
        js_url=(
            "https://midwaycoop.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=location&location=82270&commodity=&groupby=location"
            "&width=&showtimestamp=1&hidenav=1&format=table&fields=name"
            "%2Cnotes%2Cprice%2Cbasis%2Cfutures%2Cfutureschange"
            "&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d"
            "%2F%25Y&months=8&locations=&commodities=&&acCnt=1"
        ),
        default_location="All Locations",
        verified=True,
        notes="Verified live 2026-11-19: 200, var-bids JSON, location "
        "label published as 'All Locations' (one aggregated view; "
        "company base Osborne, KS), 8 rows (Corn / Milo / Soybeans / "
        "Wheat, 2 each). Embed at midwaycoop.com/grain/cash-bids.",
    ),
    "ag_state": CashbidsEmbedSite(
        key="ag_state",
        company="Ag State",
        js_url=(
            "https://agstate.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=location&location=84205&commodity=&groupby=ccommodity"
            "&width=&format=table&fields=delivery_end%2Cbasismonth%2Cprice"
            "%2Cfutures%2Cfutureschange%2Cbasis&groupheading=table"
            "&bidsort=commodity&dateformat=%25m%2F%25d%2F%25Y&months=8"
            "&locations=84205&commodities=&enableScrollIntoView=1"
            "&excludeInlineStyle=1&&acCnt=1"
        ),
        default_location="A.C.",
        verified=True,
        notes="Verified live 2026-11-19: 200, var-bids JSON, 11 rows "
        "(Corn 6, Soybeans 5). groupby=ccommodity: groups are named "
        "Corn / Soybeans, so the row location comes from "
        "location_name, published as 'A.C.' (the site's location nav "
        "lists it among ~30 Iowa points). Embed at agstate.org/grain.",
    ),
    "superior_ag": CashbidsEmbedSite(
        key="superior_ag",
        company="Superior Ag",
        js_url=(
            "https://superiorag-cb-jsi.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=location&location=82244&commodity=&groupby=ccommodity"
            "&width=&showtimestamp=1&showchart=1&asp=1&enableScrollIntoView=1"
            "&format=table&fields=name%2Cdelivery_start%2Cdelivery_end"
            "%2Cbasismonth%2Cfutures%2Cfutureschange%2Cbasis%2Cprice"
            "&groupheading=table&bidsort=commodity&dateformat=%25b%20%25Y"
            "&months=8&locations=&commodities=&&acCnt=1"
        ),
        default_location="Princeton Central",
        verified=True,
        notes="Verified live 2026-11-19: 200, var-bids JSON, 12 rows "
        "(CORN 8, SOYBEANS 4). groupby=ccommodity: groups are named "
        "CORN / SOYBEANS, so the row location comes from "
        "location_name ('Princeton Central'). Embed at "
        "superiorag.com.",
    ),
    "alcivia": CashbidsEmbedSite(
        key="alcivia",
        company="ALCIVIA",
        js_url=(
            "https://alciviacoop.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=all&location=&commodity=&groupby=location&width=100%"
            "&showtimestamp=1&showchart=1&format=table&fields=%0Aname%2C"
            "%0Anotes%2C%0Abasismonth%2C%0Afutures%2C%0Aprice%2C%0Abasis"
            "%2C%0Aprice%2C%0Afutureschange%0A&groupheading=table"
            "&bidsort=commodity&dateformat=%25m%2F%25d%2F%25Y&months=11"
            "&&acCnt=1"
        ),
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 9): 200, var-bids JSON, "
        "15 locations (Baldwin, Belleville, Burlington, Cottage Grove, "
        "Durand, Elmwood, Evansville, Fall Creek, Fall River, Four "
        "Corners (New Richmond), Hager City, Kings Valley (Osseo), "
        "Menomonie Feed Mill, Mondovi, Whitewater — all Wisconsin), "
        "181 rows (Corn 90, Soybeans 75, Wheat 16). filter=all, "
        "groupby=location, no single default location. Embed at "
        "alcivia.com/cash-bids (redirects to "
        "/wisconsin-grain-services/cash-bids-grain-wisconsin-grain/).",
    ),
    "tgm": CashbidsEmbedSite(
        key="tgm",
        company="TGM",
        js_url=(
            "https://totalgrain.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=all&location=&commodity=&groupby=ccommodity&width="
            "&showtimestamp=1&format=table&fields=name%2Cprice"
            "%2Cfutureschange%2Cbasismonth%2Cdelivery_start%2Cdelivery_end"
            "%2Cbasis%2Cfutures&groupheading=table&bidsort=location"
            "&dateformat=%25m%2F%25d%2F%25Y&months=10&locations="
            "&commodities=&&acCnt=1"
        ),
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 9): 200, var-bids JSON, "
        "24 locations (Arcola, Ashmore, Cadwell, Casey, Champaign, "
        "Fairgrange, Greenup, Greenville, Hillsboro (IN), Ingraham, "
        "Kansas, Lis, Louisville, Lovington, Middlesworth, Mulberry "
        "Grove, Neoga, Rose Hill, Sandoval, Shelbyville, Stewardson, "
        "Watson, Willow Hill, Windsor — Illinois / Indiana), 362 rows "
        "(Corn 120, Beans 120, Wheat 120, White Corn 2). "
        "groupby=ccommodity: groups are named Corn / Beans / Wheat / "
        "White Corn, so the row location comes from location_name. "
        "The feed labels soybeans 'Beans' (ZS symbols on all 120 "
        "rows) — mapped to Soybeans in COMMODITY_MAP. Embed at "
        "totalgrainmarketing.com/Cash-Bids.",
    ),
    "pro_coop": CashbidsEmbedSite(
        key="pro_coop",
        company="PRO Coop",
        js_url=(
            "https://procooperative.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=location&location=21297&commodity=&groupby=location"
            "&width=100%&showtimestamp=1&showchart=1"
            "&enableScrollIntoView=1&format=table&fields=%0Aname%2C"
            "%0Adelivery_start%2C%0Adelivery_end%2C%0Aprice%2C%0Abasis"
            "%2C%0Abasismonth%2C%0Afutures%2C%0Afutureschange%0A"
            "&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d"
            "%2F%25Y&months=11&noscript=1&&acCnt=1"
        ),
        default_location="AYRSHIRE.IA",
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 11): 200, var-bids JSON, "
        "1 location (AYRSHIRE.IA), 6 rows (Corn 6). The js_url was "
        "derived from the homepage cashbids.php loader src "
        "(filename swap to cashbids-js.php, newlines %0A-encoded, "
        "+ noscript=1 & acCnt=1 per this module's documented method); "
        "the loader JS itself was not fetched (GET budget), so the "
        "URL is the derived form that served the payload, not the "
        "loader's own widgetURL verbatim. The homepage carries two "
        "more embeds for location 21302 (groupby=ccommodity): the "
        "first (fields delivery_start / delivery_end / price / basis / "
        "futureschange) was verified live 2026-11-19 (Cycle 12) as "
        "the separate 'pro_coop_21302' entry (MANSON.IA, 12 rows); "
        "the second 21302 embed (fields without delivery_end) was "
        "NOT checked. Embed at procooperative.com.",
    ),
    "pro_coop_21302": CashbidsEmbedSite(
        key="pro_coop_21302",
        company="PRO Coop",
        js_url=(
            "https://procooperative.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=location&location=21302&commodity=&groupby=ccommodity"
            "&width=100%&showtimestamp=1&showchart=1"
            "&enableScrollIntoView=1&format=table&fields=%0Adelivery_start"
            "%2C%0Adelivery_end%2C%0Aprice%2C%0Abasis%2C%0Afutureschange"
            "%0A&groupheading=table&bidsort=commodity&dateformat=%25m%2F"
            "%25d%2F%25Y&months=11&noscript=1&&acCnt=1"
        ),
        default_location="MANSON.IA",
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 12): 200, var-bids JSON, "
        "1 location (MANSON.IA), 12 rows (CORN 6, SOYBEANS 6). "
        "groupby=ccommodity: groups are named CORN / SOYBEANS, so the "
        "row location comes from location_name. The js_url was derived "
        "from the saved Cycle 11 homepage cashbids.php loader src "
        "(filename swap to cashbids-js.php, newlines %0A-encoded, "
        "+ noscript=1 & acCnt=1 per this module's documented method); "
        "the loader's src carries literal newline characters in the "
        "fields value, which requests percent-encodes to %0A on the "
        "wire — the registry URL is that wire form, matching the "
        "21297 entry. This is the FIRST of the homepage's two "
        "location-21302 embeds; the second (fields without "
        "delivery_end) was NOT checked. Embed at procooperative.com.",
    ),
    "hull_coop": CashbidsEmbedSite(
        key="hull_coop",
        company="Hull Coop",
        js_url=(
            "https://hullcoopresp.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=all&location=&commodity=&groupby=ccommodity&width="
            "&showtimestamp=1&hidenav=1&&showchart=1&format=table&fields="
            "delivery_start%2Cbasismonth%2Cfutureschange%2Cbasis%2Cprice"
            "&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d"
            "%2F%25Y&months=8&locations=&commodities=&noscript=1&&acCnt=1"
        ),
        default_location="Hull",
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 12): 200, var-bids JSON, "
        "1 location (Hull, IA), 12 rows (Corn 6, Soybeans 6). "
        "groupby=ccommodity: groups are named Corn / Soybeans, so the "
        "row location comes from location_name. The loader src carries "
        "'hidenav=1&&showchart=1' (double ampersand mid-query), kept "
        "verbatim in the js_url. Embed at hullcoop.com/cashbids.",
    ),
    "stateline_coop": CashbidsEmbedSite(
        key="stateline_coop",
        company="StateLine Coop",
        js_url=(
            "https://statelinecoop.agricharts.com/inc/cashbids/cashbids-js.php"
            "?filter=all&location=&commodity=&groupby=location&width=90%"
            "&enableScrollIntoView=1&format=table&fields=name%2Cdelivery_"
            "start%2Cfutureschange%2Cbasis%2Cbasismonth%2Cfutures%2Cprice"
            "%2Cnotes&groupheading=row&bidsort=commodity&dateformat=%25b"
            "+%25d%2C+%25Y&months=8&locations=&commodities=&noscript=1"
            "&&acCnt=1"
        ),
        verified=True,
        notes="Verified live 2026-11-19 (Cycle 12): 200, var-bids JSON, "
        "11 locations (Armstrong, Blue Earth, Cylinder, Emmetsburg-AGP, "
        "Fenton, Lakota, Ledyard, Marna, North Burt, Ringsted, Swea City "
        "— Iowa / Minnesota), 126 rows (Corn 60, Soybeans 66; "
        "Emmetsburg-AGP is Soybeans-only, 6 rows). filter=all, "
        "groupby=location, no single default location. Embed at "
        "statelinecoop.com/cash-bids.",
    ),
}


def _money(text: Any) -> float | None:
    """Parse a $-prefixed or plain number ('$3.43' / '$-0.02') to float."""
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


def _futures_dollars(text: Any) -> float | None:
    """Convert a futures/futures-change quote to dollars.

    The feed quotes futures in cents: fractional CBOT notation
    ('433-2' = 433 2/8¢ → $4.3325, '-2-2' → -$0.0225). A plain
    number in this field is likewise cents (the field's documented
    unit), so it is also divided by 100.
    """
    if text is None:
        return None
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text) / 100.0
    cleaned = str(text).replace("$", "").replace(",", "").strip()
    if cleaned in ("", "-", "—", "--"):
        return None
    frac = _FRAC_RE.match(cleaned)
    if frac:
        sign, whole, eighths = frac.groups()
        cents = float(whole) + int(eighths) / 8
        return -cents / 100.0 if sign == "-" else cents / 100.0
    num = _money(cleaned)
    return None if num is None else num / 100.0


def _basis_dollars(value: Any) -> float | None:
    """Convert the JSON ``basis`` to dollars per bushel.

    The feed publishes basis as integer cents (e.g. -90 → -$0.90).
    A string with a decimal point is already dollars; an integer
    string is cents.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) / 100.0
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if cleaned in ("", "-", "—", "--"):
        return None
    try:
        num = float(cleaned)
    except ValueError:
        return None
    return num if "." in cleaned else num / 100.0


def _canonical_commodity(raw: Any) -> str:
    if not raw:
        return "Unknown"
    label = _GRADE_RE.sub("", str(raw).strip()).strip().lower()
    if not label:
        return "Unknown"
    return COMMODITY_MAP.get(label, str(raw).strip().title())


def _delivery_month(delivery_start: Any) -> str | None:
    """'11/01/2026' -> 'Nov 2026' (delivery label for the row)."""
    if not delivery_start:
        return None
    text = str(delivery_start).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%b %Y")
        except ValueError:
            continue
    return text or None


def _extract_bids_payload(html: str) -> list[dict[str, Any]] | None:
    """Return the ``var bids`` JSON array, or None if it is absent/unparseable."""
    for pattern in (_BIDS_RE, _BIDS_GREEDY_RE):
        match = pattern.search(html)
        if not match:
            continue
        try:
            payload = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(payload, list):
            return payload
    return None


def _make_row(
    *,
    company: str,
    location: str | None,
    cashbid: dict[str, Any],
    currency: str,
) -> dict[str, Any] | None:
    """Build one normalized row; None if it carries no usable money value."""
    commodity = _canonical_commodity(cashbid.get("name"))
    cash_price = _money(cashbid.get("cashprice", cashbid.get("price")))
    cash_price_mt = _money(cashbid.get("cashpricetonne"))
    basis = _basis_dollars(cashbid.get("basis"))
    futures_price = _futures_dollars(cashbid.get("futures"))
    futures_change = _futures_dollars(cashbid.get("futureschange"))
    raw_change = cashbid.get("rawchange")
    change = (
        float(raw_change)
        if isinstance(raw_change, (int, float)) and not isinstance(raw_change, bool)
        else _money(cashbid.get("change"))
    )
    delivery_start = cashbid.get("delivery_start") or None
    delivery_end = cashbid.get("delivery_end") or None
    futures_month = cashbid.get("basismonth") or None
    symbol = cashbid.get("symbol") or None
    if all(
        value is None
        for value in (cash_price, cash_price_mt, basis, futures_price, change)
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
        "delivery_month": _delivery_month(delivery_start),
        "delivery_start": delivery_start,
        "delivery_end": delivery_end,
        "cash_price": cash_price,
        # Published per-tonne bid (same number, not a conversion);
        # None when the feed does not publish one.
        "cash_price_mt": cash_price_mt,
        "basis": basis,
        "futures_price": futures_price,
        "futures_month": futures_month,
        "futures_symbol": symbol,
        "futures_change": futures_change,
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


def parse_cashbids_embed_html(
    html: str,
    *,
    company: str | None = None,
    currency: str = "USD",
    site: CashbidsEmbedSite | None = None,
    default_location: str | None = None,
) -> dict[str, Any]:
    """Parse a cashbids-js.php response into normalized bid rows.

    ``site`` (a CASHBIDS_EMBED_SITES entry) supplies company /
    currency / default location; the keyword arguments override it
    for ad-hoc pages. Returns {"company", "location", "rows",
    "status", "notes"}; see the module docstring.
    """
    if site is not None:
        company = company or site.company
        currency = site.currency
        default_location = default_location or site.default_location
    company = company or "Unknown cashbids-embed site"
    notes: list[str] = []
    if site is not None and site.notes:
        notes.append(f"site config: {site.notes}")

    payload = _extract_bids_payload(html)
    if payload is None:
        return _result(
            company=company,
            location=default_location,
            rows=[],
            status="unsupported",
            notes=notes
            + [
                "no `var bids` JSON payload found in the cashbids-js.php "
                "response (expected <script id=\"cb-functions\">var bids = "
                "[...]</script>)"
            ],
        )

    rows: list[dict[str, Any]] = []
    skipped_login = 0
    skipped_inactive = 0
    for group in payload:
        if not isinstance(group, dict):
            continue
        # groupby=ccommodity sites name their groups after the commodity;
        # the per-row location_name is authoritative in all cases.
        group_name = group.get("name") or None
        for cashbid in group.get("cashbids") or []:
            if not isinstance(cashbid, dict):
                continue
            if cashbid.get("require_login"):
                skipped_login += 1
                continue
            if cashbid.get("active") is False:
                skipped_inactive += 1
                continue
            location = (
                cashbid.get("location_name")
                or group_name
                or default_location
            )
            row = _make_row(
                company=company,
                location=location,
                cashbid=cashbid,
                currency=currency,
            )
            if row is not None:
                rows.append(row)
    if skipped_login:
        notes.append(f"skipped {skipped_login} login-gated bid row(s)")
    if skipped_inactive:
        notes.append(f"skipped {skipped_inactive} inactive bid row(s)")

    location = rows[0]["location"] if rows else default_location
    if not rows:
        return _result(
            company=company,
            location=location,
            rows=[],
            status="empty",
            notes=notes + ["var-bids payload present but no bid rows parsed"],
        )
    return _result(
        company=company, location=location, rows=rows, status="ok", notes=notes
    )


def fetch_cashbids_embed_html(url: str, timeout: int = 30) -> str:
    """One polite GET with the contact User-Agent."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_cashbids_embed(
    url: str,
    *,
    company: str | None = None,
    currency: str = "USD",
    site: CashbidsEmbedSite | None = None,
    default_location: str | None = None,
) -> dict[str, Any]:
    """Fetch and parse cashbids-js.php bids from ``url`` in one call."""
    return parse_cashbids_embed_html(
        fetch_cashbids_embed_html(url),
        company=company,
        currency=currency,
        site=site,
        default_location=default_location,
    )


def get_cashbids_embed_site(key: str) -> CashbidsEmbedSite:
    normalized = key.strip().lower()
    if normalized not in CASHBIDS_EMBED_SITES:
        raise KeyError(f"Unknown cashbids-embed site '{key}'")
    return CASHBIDS_EMBED_SITES[normalized]


def fetch_cashbids_embed_site(key: str) -> dict[str, Any]:
    """Fetch a configured cashbids-embed site. Only verified sites may
    run — unverified entries need one live check of the
    cashbids-js.php response first, so a typo or a premature enable
    cannot silently scrape an unconfirmed page shape."""
    site = get_cashbids_embed_site(key)
    if not site.verified:
        return _result(
            company=site.company,
            location=site.default_location,
            rows=[],
            status="unsupported",
            notes=[
                f"site '{key}' is not verified yet: {site.notes or 'live cashbids-js.php shape unconfirmed'}",
                "Fetch the cashbids-js.php URL once by hand and confirm "
                "the var-bids payload, locations and currency before "
                "marking it verified.",
            ],
        )
    return fetch_cashbids_embed(site.js_url, site=site)


def fetch_agtegra() -> dict[str, Any]:
    """Fetch Agtegra (Hecla, SD). Verified live 2026-11-19."""
    return fetch_cashbids_embed_site("agtegra")


def fetch_heritage_coop() -> dict[str, Any]:
    """Fetch Heritage Cooperative (Ada, OH). Verified live 2026-11-19."""
    return fetch_cashbids_embed_site("heritage_coop")


def fetch_linn_coop() -> dict[str, Any]:
    """Fetch Linn Coop (Cedar Rapids / Alburnett, IA). Verified live 2026-11-19."""
    return fetch_cashbids_embed_site("linn_coop")


def fetch_midway_coop() -> dict[str, Any]:
    """Fetch Midway Coop (Osborne, KS). Verified live 2026-11-19."""
    return fetch_cashbids_embed_site("midway_coop")


def fetch_ag_state() -> dict[str, Any]:
    """Fetch Ag State (Iowa). Verified live 2026-11-19."""
    return fetch_cashbids_embed_site("ag_state")


def fetch_superior_ag() -> dict[str, Any]:
    """Fetch Superior Ag. Verified live 2026-11-19."""
    return fetch_cashbids_embed_site("superior_ag")


def fetch_alcivia() -> dict[str, Any]:
    """Fetch ALCIVIA (Wisconsin). Verified live 2026-11-19 (Cycle 9)."""
    return fetch_cashbids_embed_site("alcivia")


def fetch_tgm() -> dict[str, Any]:
    """Fetch TGM / Total Grain Marketing (Illinois / Indiana).
    Verified live 2026-11-19 (Cycle 9)."""
    return fetch_cashbids_embed_site("tgm")


def fetch_pro_coop() -> dict[str, Any]:
    """Fetch PRO Coop (Ayrshire, IA — location 21297 view).
    Verified live 2026-11-19 (Cycle 11)."""
    return fetch_cashbids_embed_site("pro_coop")


def fetch_pro_coop_21302() -> dict[str, Any]:
    """Fetch PRO Coop (Manson, IA — location 21302 view, first embed).
    Verified live 2026-11-19 (Cycle 12)."""
    return fetch_cashbids_embed_site("pro_coop_21302")


def fetch_hull_coop() -> dict[str, Any]:
    """Fetch Hull Coop (Hull, IA). Verified live 2026-11-19 (Cycle 12)."""
    return fetch_cashbids_embed_site("hull_coop")


def fetch_stateline_coop() -> dict[str, Any]:
    """Fetch StateLine Coop (Iowa / Minnesota, 11 locations).
    Verified live 2026-11-19 (Cycle 12)."""
    return fetch_cashbids_embed_site("stateline_coop")
