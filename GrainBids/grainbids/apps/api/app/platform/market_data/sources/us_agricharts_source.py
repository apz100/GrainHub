# us_agricharts_source.py
"""
Generic scraper for US grain elevators using the Agricharts/Barchart writeBidRow() pattern.

Many US grain elevator sites (hosted by Agricharts, now part of Barchart) embed cash bid
data directly in HTML as writeBidRow() function calls:

    writeBidRow(name, basis_cents, manual, eod, incwt, rounding,
                start, end, location, group, notes, weight, rowclass,
                chartsym, quotes['SYMBOL'], settlement, displayOrigPrice,
                basisInActualCents, currConv, exchDisplayType);

Location names come from <h4> tags that precede each table/script block.
Futures prices are fetched from the Agricharts jsquote.php API (same as ganaraska_source).

Delivery windows: most sites emit full MM/DD/YYYY dates, but some
AgriCharts-hosted cash pages emit month-name labels instead — 'Dec 2026',
'January 2027' (West-Con), or the short form 'Nov 26', 'Jan 27' with a
2-digit year (Wheaton Dumont) — one label per month, with start == end.
Cycle 12 decision: month-only windows are kept VERBATIM in the
Delivery / Delivery End columns.  No day is invented (no first-of-month
synthesis), and no century is expanded for 2-digit years, because the
source never states either; the label itself is the delivery window.
MM/DD/YYYY rows are unaffected.

Cycle 22 (Heritage Grain Cooperative): forward-month rows carry the
delivery label in the notes argument with an escaped quote, e.g.
'DEC \'26' — the regex now allows an escaped quote in the group and
notes arguments, or those rows fail to match entirely (11 of 14
Heritage rows were skipped before this fix). The same page uses
<h4> tags for commodity headings, not locations ('CORN - DEC 2026'
precedes the row named 'CORN - DEC 2026'); an <h4> that is exactly
the row's commodity name, or that starts with a commodity word, is
treated as a commodity heading and the row falls back to the company
name as its location.

Cycle 24, option (a) (FMN precedent): when the page carries no
jsquote.php script tag, the collector no longer returns empty
before parsing. It parses the writeBidRow rows as basis-only
rows — Basis / Delivery / Location / Name / Symbol filled,
Futures Month decoded from the contract symbol, Futures Price /
Change / Bushel and MT Cash Price None with a Note saying the
values come from the missing feed, never invented. A page WITH
the tag behaves exactly as before.

Cycle 25 follow-up (design §9 scope note): when the tag IS
present but the jsquote feed returns no data (empty quotes,
e.g. `var quotes = null;`), the collector degrades the same
way as the no-tag path instead of returning an empty DataFrame.

Cycle 26: when the tag IS present but the jsquote feed fetch
itself RAISES (HTTP error, timeout, any exception from
_fetch_jsquote), the collector degrades the same way — the page
already fetched successfully, so the basis-only rows survive.
Only the feed call is wrapped: if the PAGE fetch itself fails
there is no HTML to parse, and the outer except still returns
an empty DataFrame.

Usage (called by GrainBidder.py via the [[us.elevators]] config):
    fetch_us_agricharts(url, company_name) -> pd.DataFrame

No Playwright needed — pure requests.
"""

from __future__ import annotations

import re
from typing import Optional

import pandas as pd
import requests

JSQUOTE_BASE = "https://www.agricharts.com/marketdata/jsquote.php"

_BU_PER_MT = {
    "corn":      39.3683,
    "soybeans":  36.7437,
    "soybean":   36.7437,
    "wheat":     36.7437,
    "hrw wheat": 36.7437,
    "srw wheat": 36.7437,
    "hard red winter": 36.7437,
    "soft red winter": 36.7437,
    "milo":      39.3683,
    "sorghum":   39.3683,
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}

# A delivery window is either a full date (MM/DD/YYYY) or a month-name
# label ('Dec 2026', 'January 2027', or the short 'Nov 26' / 'Jan 27'
# with a 2-digit year) — see module docstring, Cycle 12.
# Month names accept the abbreviated or full form, any case the page uses
# is matched case-sensitively as emitted by AgriCharts (title case).
_MONTH_LABEL = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?:\d{4}|\d{2})"
)
_DELIVERY = r"(?:\d{2}/\d{2}/\d{4}|" + _MONTH_LABEL + r")"

# Matches a writeBidRow() call and captures the parameters we care about.
# Signature (0-indexed):
#   0  name          commodity name
#   1  basis         cents/bu (signed integer)
#   2  manual        bool
#   3  eod           bool
#   4  incwt         bool
#   5  rounding      float
#   6  start         delivery start MM/DD/YYYY or month label ('Dec 2026')
#   7  end           delivery end   MM/DD/YYYY or month label ('Dec 2026')
#   8  location      often 'All' — we prefer the surrounding <h4> name
#   9  group         display group (often '&nbsp;')
#   10 notes         (often '&nbsp;')
#   11 weight        bu/unit (56 for corn, 60 for soy/wheat)
#   12 rowclass      'odd'/'even'
#   13 chartsym      'c=XXXX&l=YYYY&d=ZZZ'
#   14 quote         quotes['SYMBOL'] or quotevarXXXX['SYMBOL']
_WRITEBIDROW_RX = re.compile(
    r"writeBidRow\s*\("
    r"\s*'([^']+)'"                               # 0: name
    r"\s*,\s*([+-]?\d+(?:\.\d+)?)"               # 1: basis (cents/bu)
    r"\s*,\s*(?:true|false)"                      # 2: manual
    r"\s*,\s*(?:true|false)"                      # 3: eod
    r"\s*,\s*(?:true|false)"                      # 4: incwt
    r"\s*,\s*[+-]?[\d.]*"                         # 5: rounding
    r"\s*,\s*'(" + _DELIVERY + r")'"              # 6: delivery start
    r"\s*,\s*'(" + _DELIVERY + r")'"              # 7: delivery end
    r"\s*,\s*'([^']*)'"                           # 8: location param
    r"\s*,\s*'(?:[^'\\]|\\.)*'"                   # 9: group (may hold an escaped quote)
    r"\s*,\s*'(?:[^'\\]|\\.)*'"                   # 10: notes — Cycle 22: forward-month rows
    # carry the delivery label here with an escaped quote, e.g. 'DEC \'26'
    # (Heritage Grain Cooperative); the old '[^']*' stopped at the \'
    # and the whole row failed to match, so 11 of 14 rows were skipped.
    r"\s*,\s*\d+"                                 # 11: weight
    r"\s*,\s*'[^']*'"                             # 12: rowclass
    r"\s*,\s*'([^']*)'"                           # 13: chartsym
    r"\s*,\s*(?:quotes|quotevar\w+)\['([A-Z0-9]+)'\]"  # 14: futures symbol
)

_H4_RX = re.compile(r"<h4[^>]*>\s*([^<]+?)\s*</h4>", re.IGNORECASE)

# Cycle 22 (Heritage Grain Cooperative): some pages use <h4> for commodity
# headings, not locations — the h4 text is the row's commodity name
# ('CORN - DEC 2026') or starts with a commodity word ('BEANS - CASH').
# Such a heading is not a location; rows under it fall back to the
# company name, the same "Company - Company" fallback shape as West-Con
# (whose page has no <h4> headings at all).
_COMMODITY_WORDS = (
    "corn|soybeans?|beans|wheat|milo|sorghum|barley|oats|canola|rye|"
    "sunflowers?|flax|peas|lentils?|chickpeas|durum"
)
_COMMODITY_HEADING_RX = re.compile(
    r"^(?:" + _COMMODITY_WORDS + r")\b", re.IGNORECASE
)


def _is_commodity_heading(h4_text: str, row_name: str) -> bool:
    """True when an <h4> heading names a commodity, not a location.

    Either it is exactly the row's commodity name (Heritage: the h4
    'CORN - DEC 2026' precedes the row named 'CORN - DEC 2026'), or it
    starts with a commodity word ('BEANS - CASH'). A real place name
    cannot match the second form — the word boundary keeps 'Wheatland'
    and 'Cornwall' out — and the first form requires an exact match.
    """
    if h4_text.strip().lower() == row_name.strip().lower():
        return True
    return bool(_COMMODITY_HEADING_RX.match(h4_text.strip()))

_JSQUOTE_SCRIPT_RX = re.compile(
    r"jsquote\.php\?varname=(\w+)&(?:amp;)?symbols=([A-Z0-9,]+)",
)


# ─── Futures-month decoding (FMN precedent, fmn_source.py) ──────────────────
# A contract symbol decodes to its month without the quotes feed:
# 'ZCZ26' -> 'Dec 2026'. This decodes the symbol the page itself
# references — it is not a quote-feed reading. Unrecognised symbols
# return None. Used when the jsquote tag is missing (Cycle 24,
# option (a)): the month column survives even though the futures
# price does not.

_MONTH_CODES = {
    "F": "Jan", "G": "Feb", "H": "Mar", "J": "Apr", "K": "May",
    "M": "Jun", "N": "Jul", "Q": "Aug", "U": "Sep", "V": "Oct",
    "X": "Nov", "Z": "Dec",
}
_SYMBOL_RE = re.compile(r"^([A-Z]+)([FGHJKMNQUVXZ])(\d{2})$")

# Note attached to basis-only rows (FMN pattern: feed-dependent values
# are None with a note saying so, never invented).
_NO_QUOTES_NOTE = (
    "Basis as published; futures price, change and cash price come "
    "from the page's external quotes feed (jsquote.php) and are not "
    "in the static HTML — left as None, never invented; futures "
    "month decoded from the contract symbol"
)


def futures_month_from_symbol(symbol: str | None) -> str | None:
    """Decode a futures contract symbol to its month label.

    'ZCZ26' -> 'Dec 2026'; 'ZSF27' -> 'Jan 2027'. Same decoder as
    ``fmn_source.futures_month_from_symbol``. An unrecognised symbol
    returns None.
    """
    if not symbol:
        return None
    match = _SYMBOL_RE.match(symbol.strip().upper())
    if not match:
        return None
    _root, month_code, year2 = match.groups()
    month = _MONTH_CODES.get(month_code)
    if month is None:
        return None
    return f"{month} 20{year2}"


# ─── jsquote helpers (shared logic with ganaraska_source) ────────────────────

def _js_obj_to_dict(js_text: str) -> dict:
    """
    Parse an Agricharts JS object literal (unquoted keys, single-quoted strings)
    into a Python dict of dicts.  Extracts name, month, last per symbol.
    """
    result: dict = {}
    sym_rx   = re.compile(r"['\"]([A-Z0-9]+)['\"]\s*:\s*\{([^}]+)\}", re.DOTALL)
    field_rx = re.compile(r"(\w+)\s*:\s*'([^']*)'")
    for sm in sym_rx.finditer(js_text):
        symbol = sm.group(1)
        block  = sm.group(2)
        fields = {m.group(1): m.group(2) for m in field_rx.finditer(block)}
        result[symbol] = fields
    return result


def _fetch_jsquote(varname: str, symbols: list) -> dict:
    """Fetch current futures prices from Agricharts jsquote API."""
    params = {
        "varname":     varname,
        "symbols":     ",".join(symbols),
        "fields":      "name,month,last",
        "settle":      "0",
        "displayType": "bids",
    }
    r = requests.get(JSQUOTE_BASE, params=params, headers=_HEADERS, timeout=30)
    r.raise_for_status()
    data = _js_obj_to_dict(r.text)
    if not data:
        print(f"[US-AG] jsquote parse failed. Preview: {r.text[:200]}")
    return data


# ─── Main scraper ─────────────────────────────────────────────────────────────

def fetch_us_agricharts(url: str, company_name: str, playwright=None) -> pd.DataFrame:
    """
    Scrape a US elevator page that uses the Agricharts writeBidRow() pattern.

    Args:
        url:          The cash bids page URL (e.g. https://site.com/markets/cash.php)
        company_name: Human-readable company/elevator name for the Location column
        playwright:   Unused; accepted for orchestrator compatibility

    Returns:
        Normalized DataFrame with columns matching the rest of GrainBidder.
    """
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30)
        r.raise_for_status()
        html = r.text

        # 1. Find jsquote.php script tag → varname + symbols
        # Cycle 24, option (a): when the tag is missing, do NOT bail
        # before parsing. The writeBidRow rows still carry the basis,
        # delivery, location, name and futures symbol — only the
        # futures price (and the cash prices derived from it) need
        # the feed. Parse the rows as basis-only: futures price /
        # change / cash are None with a note (FMN precedent), and
        # Futures Month is decoded from the contract symbol.
        jm = _JSQUOTE_SCRIPT_RX.search(html)
        quotes: dict = {}
        degraded = False
        if not jm:
            print(
                f"[US-AG WARN] {company_name}: jsquote script tag not "
                "found in page — parsing basis-only rows"
            )
            degraded = True
        else:
            varname = jm.group(1)
            symbols = jm.group(2).split(",")

            # 2. Fetch futures prices from jsquote API
            # Cycle 25: an empty feed degrades exactly like the
            # no-tag path (basis-only rows, §9 scope note) instead
            # of returning an empty DataFrame. A feed WITH data
            # behaves exactly as before.
            # Cycle 26: a feed fetch that RAISES (HTTP error, timeout,
            # any exception from _fetch_jsquote) degrades the same
            # way — the page is already fetched, so the basis-only
            # rows survive. Only the feed call is wrapped in this
            # try: if the PAGE fetch itself fails there is no HTML
            # to parse, and the outer except still returns empty.
            try:
                quotes = _fetch_jsquote(varname, symbols)
            except Exception as e:
                print(
                    f"[US-AG WARN] {company_name}: jsquote fetch failed "
                    f"({e}) — parsing basis-only rows"
                )
                degraded = True
            if not quotes and not degraded:
                print(
                    f"[US-AG WARN] {company_name}: jsquote returned no "
                    "data — parsing basis-only rows"
                )
                degraded = True

        # 3. Walk HTML in document order, tracking current <h4> location name
        events: list = []
        for m in _H4_RX.finditer(html):
            events.append((m.start(), "h4", m.group(1).strip()))
        for m in _WRITEBIDROW_RX.finditer(html):
            events.append((m.start(), "row", m))
        events.sort(key=lambda e: e[0])

        rows: list = []
        current_loc = company_name   # fallback if no <h4> precedes first row

        for _pos, etype, data in events:
            if etype == "h4":
                current_loc = data
                continue

            m = data
            name        = m.group(1).strip()
            basis_cents = float(m.group(2))
            del_start   = m.group(3)          # MM/DD/YYYY or month label, verbatim (Cycle 12)
            del_end     = m.group(4)          # MM/DD/YYYY or month label, verbatim (Cycle 12)
            # group(5) = location param in writeBidRow — often 'All', use h4 instead
            # group(6) = chartsym
            symbol      = m.group(7)

            q = quotes.get(symbol, {}) if not degraded else {}
            if degraded:
                # Basis-only row: no feed, so no futures price, no
                # change, no cash price — None with a note, never
                # invented. Futures Month comes from the symbol.
                futures_raw: object = None
                futures_month: object = futures_month_from_symbol(symbol)
                bushel_cash: object = None
                mt_cash: object = None
                change: object = None
                note = _NO_QUOTES_NOTE
            else:
                futures_raw = q.get("last", "")
                futures_month = q.get("month", "")
                change = ""

                bushel_cash = mt_cash = ""
                if futures_raw:
                    try:
                        # futures_raw is decimal cents/bu (e.g. "439", "449.5")
                        cash_cents = float(futures_raw) + basis_cents
                        cash_bu    = cash_cents / 100.0
                        bushel_cash = f"${cash_bu:.2f}"
                        bpu = _BU_PER_MT.get(name.lower(), 39.3683)
                        mt_cash = str(round(cash_bu * bpu, 2))
                    except Exception:
                        pass
                note = ""

            # Basis as ¢/bu for display  (e.g. 5 → "+5¢", -40 → "-40¢")
            basis_disp = (
                f"+{int(basis_cents)}" if basis_cents > 0
                else str(int(basis_cents)) if basis_cents == int(basis_cents)
                else str(basis_cents)
            )

            # Cycle 22: an <h4> that is a commodity heading (Heritage)
            # is not a location — fall back to the company name.
            loc = company_name if _is_commodity_heading(current_loc, name) else current_loc

            rows.append({
                "Location":          f"{company_name} - {loc}",
                "Name":              name,
                "Delivery":          del_start,
                "Delivery End":      del_end,
                "Futures Month":     futures_month,
                "Futures Price":     futures_raw,
                "Change":            change,
                "Basis":             basis_disp,
                "Bushel Cash Price": bushel_cash,
                "MT Cash Price":     mt_cash,
                # "" on feed-backed rows (schema-stable); the
                # basis-only note on degraded rows (Cycle 24).
                "Note":              note,
            })

        if not rows:
            print(f"[US-AG WARN] {company_name}: 0 rows parsed — page structure may differ")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        print(f"[US-AG OK] {company_name}: {len(df)} rows from {len(set(r['Location'] for r in rows))} locations")
        return df

    except Exception as e:
        print(f"[US-AG ERR] {company_name}: {e}")
        return pd.DataFrame()


# ─── URL-bound registry adapters (Cycle 20) ────────────────────────────────
# Zero-argument wrappers over fetch_us_agricharts() for the enabled
# `agricharts` entries in us_elevators_urls.toml. The platform registry
# (app/services/source_registry.py) calls fetch_fn() with no arguments,
# so each entry gets its own bound wrapper; the coordinator wires them
# as SourceAdapter rows (mode "direct" — these return a DataFrame).
#
# All 13 entries are static writeBidRow() pages — confirmed in Cycle 1
# discovery or verified live in Cycles 11–12 — so no browser is needed.
# Live verification of the wrappers themselves is a later cycle's
# GET-probe work; nothing here fetches a page.

US_AGRICHARTS_SITES: dict[str, tuple[str, str]] = {
    # key: (company_name, url) — mirrors the enabled `agricharts`
    # entries in us_elevators_urls.toml.
    "ag_plus": ("Ag Plus", "https://www.agplusinc.com/markets/cash.php"),
    "farmers_win_coop": ("Farmers Win Coop", "https://www.farmerswin.com/markets/cash.php"),
    "heartland_coop": ("Heartland Coop", "https://www.heartlandcoop.com/markets/cash.php"),
    "heritage_grain_cooperative": ("Heritage Grain Cooperative", "https://www.heritagegrain.com/markets/cash.php"),
    "keller": ("Keller", "https://www.kellergrain.com/markets/cash.php"),
    "kokomo_grain": ("Kokomo Grain", "https://www.kokomograin.com/markets/cash.php?location_filter="),
    "legacy_farmers": ("Legacy Farmers", "https://www.legacyfarmers.com/markets/cash.php"),
    "pro_ag": ("Pro Ag", "https://www.proagfarmers.com/markets/cash.php"),
    "west_con": ("West-Con", "https://www.west-con.com/markets/cash.php"),
    "wheaton_dumont": ("Wheaton Dumont", "https://www.wdcoop.com/markets/cash.php"),
    "central_farmers_coop": ("Central Farmers Coop", "https://www.cenfarmcoop.com/markets/cash.php"),
    "anthony_farmers_coop": ("Anthony Farmers Co-op", "https://www.anthonycoop.com/markets/cash.php"),
    "mulvane_coop": ("Mulvane Coop", "https://www.mulvanecoop.com/markets/cash.php"),
}


def fetch_ag_plus() -> pd.DataFrame:
    """Fetch Ag Plus (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["ag_plus"]
    return fetch_us_agricharts(url, name)


def fetch_farmers_win_coop() -> pd.DataFrame:
    """Fetch Farmers Win Coop (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["farmers_win_coop"]
    return fetch_us_agricharts(url, name)


def fetch_heartland_coop() -> pd.DataFrame:
    """Fetch Heartland Coop (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["heartland_coop"]
    return fetch_us_agricharts(url, name)


def fetch_heritage_grain_cooperative() -> pd.DataFrame:
    """Fetch Heritage Grain Cooperative (static writeBidRow cash page) via the generic collector.

    Distinct from ``heritage_coop`` (Heritage Cooperative, an
    agricharts-embed site) — different company, different URL.
    """
    name, url = US_AGRICHARTS_SITES["heritage_grain_cooperative"]
    return fetch_us_agricharts(url, name)


def fetch_keller() -> pd.DataFrame:
    """Fetch Keller (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["keller"]
    return fetch_us_agricharts(url, name)


def fetch_kokomo_grain() -> pd.DataFrame:
    """Fetch Kokomo Grain (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["kokomo_grain"]
    return fetch_us_agricharts(url, name)


def fetch_legacy_farmers() -> pd.DataFrame:
    """Fetch Legacy Farmers (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["legacy_farmers"]
    return fetch_us_agricharts(url, name)


def fetch_pro_ag() -> pd.DataFrame:
    """Fetch Pro Ag (static writeBidRow cash page) via the generic collector.

    Verified live Cycle 11: 78 static writeBidRow rows at
    /markets/cash.php (Corn / Soybeans / Wheat, 6 h4 locations).
    """
    name, url = US_AGRICHARTS_SITES["pro_ag"]
    return fetch_us_agricharts(url, name)


def fetch_west_con() -> pd.DataFrame:
    """Fetch West-Con (static writeBidRow cash page) via the generic collector.

    Verified live Cycles 11–12: 84 static writeBidRow rows at
    /markets/cash.php; delivery labels are month names ('Dec 2026'),
    kept verbatim by the parser (Cycle 12).
    """
    name, url = US_AGRICHARTS_SITES["west_con"]
    return fetch_us_agricharts(url, name)


def fetch_wheaton_dumont() -> pd.DataFrame:
    """Fetch Wheaton Dumont (static writeBidRow cash page) via the generic collector.

    Verified live Cycle 12: 43 static writeBidRow rows at
    /markets/cash.php; delivery labels are the short month form
    ('Nov 26', 'Jan 27'), kept verbatim by the parser.
    """
    name, url = US_AGRICHARTS_SITES["wheaton_dumont"]
    return fetch_us_agricharts(url, name)


def fetch_central_farmers_coop() -> pd.DataFrame:
    """Fetch Central Farmers Coop (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["central_farmers_coop"]
    return fetch_us_agricharts(url, name)


def fetch_anthony_farmers_coop() -> pd.DataFrame:
    """Fetch Anthony Farmers Co-op (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["anthony_farmers_coop"]
    return fetch_us_agricharts(url, name)


def fetch_mulvane_coop() -> pd.DataFrame:
    """Fetch Mulvane Coop (static writeBidRow cash page) via the generic collector."""
    name, url = US_AGRICHARTS_SITES["mulvane_coop"]
    return fetch_us_agricharts(url, name)
