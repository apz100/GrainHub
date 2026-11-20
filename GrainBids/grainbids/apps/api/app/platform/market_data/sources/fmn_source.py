"""Farm Market News (AgriCharts) cash-bid collector.

Covers the FMN cash page — the default (all-locations) view:

  https://fmn1.agricharts.com/markets/cash.php

Verified live 2026-11-19 (one polite GET, 200, ~354 KB, saved to
/tmp/fmn/fmn_cash.html — scratch only, never the repo): 204
``homepage_quoteboard`` tables, 453 bid rows, 87 distinct delivery
points (one more than the 86 counted on 2026-11-18; the extra point
comes from how compound titles split — see ``_split_title`` — the
live page itself lists one more titled point than the earlier count).

Page shape — read this before assuming it is a plain HTML table
page, because it is not:

  * Each bid "table" is a real ``<table class="homepage_quoteboard">``
    with a title row (``<tr class="section"><th colspan="10">``,
    e.g. "Alliston", "Alliston Corn", "Hensall HDC Barley") and the
    9-column header row (Name / Delivery / Delivery End / Futures
    Month / Futures Price / Change / Basis / Cash Price / Settlement).
  * The data rows are NOT ``<tr>`` elements in the static HTML. Each
    table's ``<tbody>`` holds one ``<script>`` block of
    ``writeBidRow(...)`` calls (19 or 20 arguments) that render the
    rows in the browser. The parser below reads those calls from the
    static HTML — no JavaScript is executed and no browser is needed.
  * The futures data (futures month / price / change, and therefore
    the cash price) is NOT in the static HTML. It arrives through a
    separate ``<script src>`` feed
    (``www.agricharts.com/marketdata/jsquote.php?varname=quotes&...``)
    that populates a ``quotes`` dictionary (10 symbols on the verified
    page) which the ``writeBidRow`` calls reference as
    ``quotes['ZCZ26']`` etc. ``fetch_fmn_cash`` fetches that feed
    (verified live 2026-11-19, Cycle 11: 200, ``var quotes`` with all
    10 symbols) and ``parse_quotes_feed`` parses it into
    {symbol: {rawLast, change, exchange, ...}}; ``parse_fmn_html``
    accepts the mapping as ``quotes=`` and fills ``futures_price``,
    ``change`` and ``cash_price`` on futures-linked rows. When the
    feed is not passed (or a row's symbol is missing from it) those
    values stay None with a note saying so — never invented. What IS
    static per row: the row name, the basis argument, the delivery
    window, the contract symbol, and the settlement fallback (see
    below).
  * ``writeBidRow`` signature (from the page's own inline script):
    ``(name, basis, manual, eod, incwt, rounding, start, end,
    location, group, notes, weight, rowclass, chartsym, quote,
    settlement, displayOrigPrice, basisInActualCents, currConv,
    exchDisplayType)``. Columns render as: Name=name,
    Delivery=start, Delivery End=end, Futures Month=quote.month,
    Futures Price=quote.rawLast, Change=quote.change, Basis=basis,
    Cash Price=computed (see below), Settlement=quote.settlement
    or the ``settlement`` argument, falling back to "0-0".
  * Cash price (page's own render rule, replicated in
    ``quote_cash_price`` from the page's inline ``writeBidRow`` in
    the saved HTML): ``price = quote.rawLast * (exchange == 'WCE'
    ? 100 : 1)``; for MW/ZR/ZM symbols ``rounded = price + basis/100``
    and the cash cell is ``rounded`` in dollars, otherwise
    ``rounded = price + basis`` in cents and — when ``rounding > -1``
    (0.5 on every FMN row observed) — the page rounds to whole cents
    (ceil when the fraction >= rounding, else floor) and writes
    ``rounded / 100``. Units, verified from the live feed
    (2026-11-19, Cycle 11): CBOT quotes arrive in cents
    (rawLast/change in cents, / 100 for dollars); Minneapolis-wheat
    quotes (MWU27/MWZ26, exchange MIAX, basecode 'C') arrive in
    dollars (rawLast/change as-is). The feed carries no ``unitcode``
    field, so the page's unitcode branch never fires here.
    ``currConv`` is false on every FMN row observed and the feed's
    exchangeRate is '1', so no currency conversion applies. For
    manual rows (barley/oats), ``cash = basis / 100`` deterministically
    from static arguments, so it IS published here. Manual rows carry
    no quote argument at all (19 arguments instead of 20) and their
    rendered Basis / Futures / Change cells are blank.
  * Basis is published in cents scale: the page's cash rule adds the
    basis argument directly to the cent-denominated futures price,
    and the manual barley/oats arguments are five-figure cents
    (cash = basis / 100 gives a per-tonne price). ``basis`` is kept
    exactly as published (NOT divided by 100), following this repo's
    "published numbers, NOT normalized" convention — consumers must
    not read it as dollars per bushel. The row note says so.
  * Settlement is the literal fallback "0-0" on every row observed:
    the ``settlement`` argument is ``0-0`` in every call and the
    jsquote feed requests ``settle=0``, so no quote settlement
    overrides it. Kept verbatim as the string "0-0".
  * Currency / unit: the page labels NO currency or unit anywhere
    (no CAD / CDN / tonne / bushel text in the static HTML). CAD is
    used because this is the Ontario Farm Market News service (all
    delivery points are Ontario/Quebec) and the cash rule's levels
    are Canadian-dollar levels. ``unit`` is "$/bu" for corn/soy/wheat
    and "$/t" for the manual barley/oats rows (whose cash values are
    only sensible per tonne). Both are flagged here as the FMN
    Ontario convention, not a label read off the page — confirm
    against a rendered page before treating them as verified.
  * Date: the page publishes no as-of/trade date, so ``date`` is the
    fetch date (America/Toronto), passed in as ``as_of``.
  * The Location dropdown lists 336 options — far more than the 204
    tables — so the default view is NOT the complete FMN set. The
    dropdown filter submits a ``location_filter`` GET and is
    JS/render-dependent; it is out of scope here (needs a Playwright
    render check in a later cycle). This collector covers the
    default view only.
  * Delivery points are kept VERBATIM as titled, including regional
    averages and FOB points ("Chatham-Kent Avg", "London Avg",
    "Huron FOB", "Quebec FOB", ...). A plain-named table (e.g.
    "Alliston") is a wheat table; a table named "X Corn" /
    "X Soybeans" / "X Barley" / "X Oats" covers that one crop.
    Compound titles keep their full text ("Hamilton Transfer
    Transfer Soybeans" titles its location "Hamilton Transfer
    Transfer" — doubled on the page itself, kept as-is, not fixed).
    Wheat classes (HRS/HRW/SRW/SWW, New/Old Crop) appear as row
    names inside the wheat tables; the class is canonicalised into
    ``commodity`` ("Wheat — HRW") and the full label is kept verbatim
    in ``name``.

Rows never contain invented values: anything that needs the external
quotes feed is None with a ``note`` explaining what is missing.
Every row carries ``source`` ("fmn") and ``date`` (the fetch date).

Return shape (matches the other direct_dict collectors):
{"company", "location", "rows", "status", "notes"} where ``status``
is "ok" (rows found), "empty" (bid tables present but no parseable
rows) or "unsupported" (no ``homepage_quoteboard`` tables found).
``location`` is the first row's location.
"""

from __future__ import annotations

import math
import re
from datetime import date as _date
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

FMN_URL = "https://fmn1.agricharts.com/markets/cash.php"
FMN_COMPANY = "Farm Market News"
SOURCE_KEY = "fmn"
# The quotes feed URL, verbatim from the cash page's own <script src>
# (saved /tmp/fmn/fmn_cash.html; verified live 2026-11-19, Cycle 11:
# 200, var quotes with all 10 symbols). The empty user=/pass= params
# are the page's own public-feed params, not credentials — do not put
# any other credentials anywhere near this URL.
FMN_QUOTES_URL = (
    "https://www.agricharts.com/marketdata/jsquote.php"
    "?varname=quotes&symbols=ZWN27,ZWZ26,ZCZ26,ZCZ27,ZSF27,ZSX27,MWU27,"
    "MWZ26,ZCH27,ZSH27&fields=name,month,last&user=&pass=&settle=0"
    "&display_ice=0&ice_exchanges=&exchsyms=&currencyconv="
    "&displayType=bids"
)
# The page publishes no as-of date; rows are dated with the fetch
# date in the market's timezone.
FETCH_TZ = ZoneInfo("America/Toronto")

# Table-title suffix (trailing crop word) -> crop. A title with no
# suffix is a wheat table.
_TITLE_CROPS = ("Soybeans", "Corn", "Barley", "Oats")

# Row-name prefix -> canonical wheat commodity. The full row label
# (e.g. "HRW New Crop Wheat") is kept verbatim in ``name``.
_WHEAT_CLASS_MAP = {
    "HRS": "Wheat — HRS",
    "HRW": "Wheat — HRW",
    "SRW": "Wheat — SRW",
    "SWW": "Wheat — SWW",
}

# CBOT / MGEX futures month codes -> "%b" abbreviation.
_MONTH_CODES = {
    "F": "Jan", "G": "Feb", "H": "Mar", "J": "Apr", "K": "May",
    "M": "Jun", "N": "Jul", "Q": "Aug", "U": "Sep", "V": "Oct",
    "X": "Nov", "Z": "Dec",
}
# Contract symbol: root letters + month code + 2-digit year,
# e.g. ZCZ26 (Dec 2026 corn), ZSF27 (Jan 2027 soybeans),
# MWU27 (Sep 2027 Minneapolis wheat).
_SYMBOL_RE = re.compile(r"^([A-Z]+)([FGHJKMNQUVXZ])(\d{2})$")
_QUOTE_REF_RE = re.compile(r"""^quotes\[['"]([A-Z0-9]+)['"]\]$""")
# writeBidRow( ... ); — matched by a balanced-paren scan, not by
# regex, because arguments contain nested brackets/quotes.
_CALL_START = "writeBidRow("
# The jsquote feed is a JS object literal (unquoted keys, single-quoted
# string values), not JSON: ``var quotes = {'ZCZ26': {symbol: 'ZCZ26',
# ..., rawLast: '434.75', change: '-0.75', ...}, ...};``. Parsed with a
# brace-matching scan plus per-field regexes — no JS is executed.
_QUOTES_START = "var quotes = {"
_QUOTE_BLOCK_RE = re.compile(r"'([A-Z0-9]+)'\s*:\s*\{")
_QUOTE_FIELDS = ("symbol", "rawLast", "change", "exchange", "exchangeRate", "month")
# writeBidRow's cash branch keys on the symbol prefix: MW / ZR / ZM
# symbols are dollar-denominated (their rawLast/change arrive in
# dollars, not cents). Everything else on this page is CBOT cents.
_DOLLAR_QUOTE_PREFIXES = ("MW", "ZR", "ZM")


def _today_iso() -> str:
    return datetime.now(FETCH_TZ).date().isoformat()


def _as_of_iso(as_of: str | _date | None) -> str:
    if as_of is None:
        return _today_iso()
    if isinstance(as_of, _date):
        return as_of.isoformat()
    return str(as_of).strip()


def _split_title(title: str) -> tuple[str, str]:
    """'Alliston Corn' -> ('Alliston', 'Corn'); 'Alliston' -> ('Alliston', 'Wheat').

    The location half is kept verbatim as titled, including regional
    averages and FOB points.
    """
    text = title.strip()
    for crop in _TITLE_CROPS:
        suffix = f" {crop}"
        if text.endswith(suffix):
            return text[: -len(suffix)], crop
    return text, "Wheat"


def _canonical_commodity(crop: str, row_name: str) -> str:
    """Wheat rows carry their class ('Wheat — HRW'); other crops as titled."""
    if crop != "Wheat":
        return crop
    prefix = row_name.strip().split(" ", 1)[0].upper()
    return _WHEAT_CLASS_MAP.get(prefix, "Wheat")


def futures_month_from_symbol(symbol: str | None) -> str | None:
    """Decode a futures contract symbol to its month label.

    'ZCZ26' -> 'Dec 2026'; 'ZSF27' -> 'Jan 2027'. This decodes the
    symbol the page itself references — it is not a quote-feed
    reading. An unrecognised symbol returns None.
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


def _extract_js_object(text: str, start: int) -> tuple[str, int] | None:
    """Return (body, end_pos) for the {...} starting at text[start].

    Brace-matching scan that skips quoted strings, so braces inside
    string values do not end the object early. None when unbalanced.
    """
    if start < 0 or start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_quote: str | None = None
    escaped = False
    pos = start
    while pos < len(text):
        ch = text[pos]
        if in_quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_quote:
                in_quote = None
        else:
            if ch in ("'", '"'):
                in_quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start + 1 : pos], pos + 1
        pos += 1
    return None


def _js_field(body: str, field: str) -> str | None:
    """Return one scalar field from a JS object-literal block.

    Accepts a quoted string or a bare number. The negative lookbehind
    keeps ``change`` from matching inside ``exchange`` and ``month``
    from matching inside ``shortmonth``.
    """
    match = re.search(
        r"(?<![A-Za-z])" + re.escape(field) + r"\s*:\s*(?:'([^']*)'|(-?[\d.]+))",
        body,
    )
    if not match:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2)


def parse_quotes_feed(text: str) -> dict[str, dict[str, str]]:
    """Parse a jsquote.php ``var quotes = {...};`` response.

    Returns {symbol: {field: value}} for the fields the collector
    uses (rawLast, change, exchange, exchangeRate, month). Values are
    kept as strings; conversion happens when a row is filled. Returns
    {} when the feed has no quotes object or no symbols.
    """
    start = text.find(_QUOTES_START)
    if start < 0:
        return {}
    brace = text.find("{", start)
    extracted = _extract_js_object(text, brace)
    if extracted is None:
        return {}
    body, _ = extracted
    quotes: dict[str, dict[str, str]] = {}
    for match in _QUOTE_BLOCK_RE.finditer(body):
        symbol = match.group(1)
        block = _extract_js_object(body, match.end() - 1)  # the "{" itself
        if block is None:
            continue
        block_body, _ = block
        entry = {}
        for field in _QUOTE_FIELDS:
            value = _js_field(block_body, field)
            if value is not None:
                entry[field] = value
        if entry:
            quotes[symbol] = entry
    return quotes


def _is_dollar_quote(symbol: str | None) -> bool:
    """True for MW / ZR / ZM symbols, whose feed values are dollars."""
    return bool(symbol) and symbol[:2].upper() in _DOLLAR_QUOTE_PREFIXES


def _quote_float(value: Any) -> float | None:
    """Parse a feed value ('600.5' / 600.5) to float; None when absent/unparseable."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def quote_to_dollars(
    value: Any, *, symbol: str | None, exchange: str | None = None
) -> float | None:
    """Convert a feed rawLast/change value to dollars per bushel.

    CBOT quotes arrive in cents (rawLast 434.75 -> $4.3475). MW/ZR/ZM
    quotes and WCE quotes arrive in dollars already (MW rawLast 6.575
    -> $6.575) — the page's own writeBidRow treats those branches as
    dollars (see quote_cash_price). None when the value is missing or
    unparseable — never invented.
    """
    num = _quote_float(value)
    if num is None:
        return None
    if _is_dollar_quote(symbol) or (exchange or "").strip().upper() == "WCE":
        return num
    return num / 100.0


def quote_cash_price(
    raw_last: Any,
    basis: float | None,
    rounding: float | None,
    *,
    symbol: str | None,
    exchange: str | None = None,
) -> float | None:
    """Replicate the page's writeBidRow cash rule for a futures-linked row.

    From the page's own inline script (saved /tmp/fmn/fmn_cash.html):
    ``price = quote.rawLast * (quote.exchange == 'WCE' ? 100 : 1)``;
    for MW/ZR/ZM symbols ``rounded = price + basis/100`` and the cash
    cell is ``rounded`` in dollars (toFixed(2)); otherwise
    ``rounded = price + basis`` in cents and — when ``rounding > -1``
    (0.5 on every FMN row observed) — the page rounds to whole cents
    (ceil when the fraction >= rounding, else floor) and writes
    ``rounded / 100``. ``currConv`` is false on every FMN row observed
    and the feed's exchangeRate is '1', so no currency conversion
    applies. Returns None when the quote or the basis is missing.
    """
    raw = _quote_float(raw_last)
    if raw is None or basis is None:
        return None
    if _is_dollar_quote(symbol):
        return round(raw + basis / 100.0, 2)
    price_cents = raw * 100.0 if (exchange or "").strip().upper() == "WCE" else raw
    rounded = price_cents + basis
    if rounding is not None and rounding > -1:
        remainder = rounded - math.floor(rounded)
        rounded = math.ceil(rounded) if remainder >= rounding else math.floor(rounded)
    return round(rounded / 100.0, 2)


def _extract_calls(script_text: str) -> list[str]:
    """Return the raw argument text of every writeBidRow(...) call.

    Balanced-paren scan so quoted strings and nested brackets
    (``quotes['ZCZ26']``) do not end a call early.
    """
    calls: list[str] = []
    idx = 0
    while True:
        start = script_text.find(_CALL_START, idx)
        if start < 0:
            break
        pos = start + len(_CALL_START)
        depth = 1
        in_quote: str | None = None
        escaped = False
        while pos < len(script_text) and depth > 0:
            ch = script_text[pos]
            if in_quote is not None:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == in_quote:
                    in_quote = None
            else:
                if ch in ("'", '"'):
                    in_quote = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
            pos += 1
        calls.append(script_text[start + len(_CALL_START) : pos - 1])
        idx = pos
    return calls


def _split_args(call_text: str) -> list[str]:
    """Split a call's argument text on top-level commas."""
    parts: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    escaped = False
    bracket_depth = 0
    for ch in call_text:
        if in_quote is not None:
            current.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_quote:
                in_quote = None
        else:
            if ch in ("'", '"'):
                in_quote = ch
                current.append(ch)
            elif ch == "[":
                bracket_depth += 1
                current.append(ch)
            elif ch == "]":
                bracket_depth -= 1
                current.append(ch)
            elif ch == "," and bracket_depth == 0:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
    parts.append("".join(current).strip())
    return parts


def _unquote(token: str | None) -> str | None:
    """'Nov 2026' -> 'Nov 2026'; an unquoted token is returned as-is."""
    if token is None:
        return None
    text = token.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        body = text[1:-1]
        return body.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
    return text or None


def _number(token: str | None) -> float | None:
    """Parse a bare numeric argument ('-35', '30000', '0.5') to float."""
    if token is None:
        return None
    text = token.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _is_quoted(token: str | None) -> bool:
    if not token:
        return False
    text = token.strip()
    return len(text) >= 2 and text[0] in ("'", '"') and text[0] == text[-1]


def manual_cash_price(basis: float | None, rounding: float | None) -> float | None:
    """Replicate the page's own cash rule for manual (cash-only) rows.

    The page's ``writeBidRow`` sets ``rounded = basis`` for manual
    rows, then applies the rounding step (``rounding`` is 0.5 on every
    row observed) and writes ``rounded / 100``. With an integer basis
    this is just ``basis / 100``; the floor/ceil step is reproduced
    here so a non-integer basis behaves the same as the rendered
    page. Returns None when the basis is missing.
    """
    if basis is None:
        return None
    rounded = basis
    step = -1.0 if rounding is None else rounding
    if step > -1:
        remainder = rounded - math.floor(rounded)
        rounded = (
            math.ceil(rounded) if remainder >= step else math.floor(rounded)
        )
    return round(rounded / 100, 2)


def _parse_call(args: list[str]) -> dict[str, Any] | None:
    """Parse one writeBidRow argument list into row fields.

    Returns None for anything that is not a data call (e.g. the
    ``function writeBidRow(name, basis, ...)`` definition, whose
    arguments are bare identifiers rather than literals).

    Layout (20 args): name, basis, manual, eod, incwt, rounding,
    start, end, location, group, notes, weight, rowclass, chartsym,
    quote, settlement, displayOrigPrice, basisInActualCents,
    currConv, exchDisplayType. Manual rows omit the quote argument
    entirely (19 args): the settlement slot then holds ``0-0`` and
    everything after it shifts one place left.
    """
    if len(args) not in (19, 20):
        return None
    # A data call's first argument is a quoted row name; the function
    # definition (and any other stray code) has a bare identifier.
    if not _is_quoted(args[0]):
        return None
    name = _unquote(args[0])
    if not name:
        return None
    basis = _number(args[1])
    manual = args[2].strip().lower() == "true"
    rounding = _number(args[5])
    start = _unquote(args[6])
    end = _unquote(args[7])
    if len(args) == 20:
        quote_token = args[14].strip()
        settlement_token = args[15]
    else:  # 19 args: manual row, quote argument omitted.
        quote_token = ""
        settlement_token = args[14]
    quote_match = _QUOTE_REF_RE.match(quote_token)
    symbol = quote_match.group(1) if quote_match else None
    settlement = _unquote(settlement_token)
    if settlement is None:
        # The page's own fallback when no settlement is given.
        settlement = "0-0"
    return {
        "name": name,
        "basis": basis,
        "manual": manual,
        "rounding": rounding,
        "delivery_month": start,
        "delivery_end": end,
        "futures_symbol": symbol,
        "settlement": settlement,
    }


def _make_row(
    *,
    location: str,
    crop: str,
    fields: dict[str, Any],
    as_of: str,
    quote: dict[str, Any] | None = None,
    quotes_given: bool = False,
) -> dict[str, Any]:
    """Build one normalized row; feed-dependent values stay None
    unless the row's quote is supplied."""
    commodity = _canonical_commodity(crop, fields["name"])
    manual = fields["manual"]
    if manual:
        # Cash-only row: the rendered Basis / Futures / Change cells
        # are blank and the cash price is the published manual value
        # (basis arg / 100, per tonne). No futures/basis is invented.
        cash_price = manual_cash_price(fields["basis"], fields["rounding"])
        unit = "$/t"
        note = (
            "Cash-only (manual) row: no futures, basis or change "
            "published; cash price is the page's published manual "
            "value (basis arg / 100), per tonne"
        )
        return {
            "company": FMN_COMPANY,
            "source": SOURCE_KEY,
            "location": location,
            "commodity": commodity,
            "name": fields["name"],
            "delivery_month": fields["delivery_month"],
            "delivery_end": fields["delivery_end"],
            "cash_price": cash_price,
            # Published per-tonne cash for $/t rows (same number,
            # not a conversion).
            "cash_price_mt": cash_price,
            "basis": None,
            "futures_price": None,
            "futures_month": None,
            "futures_symbol": None,
            "last_trade": None,
            "change": None,
            "currency": "CAD",
            "unit": unit,
            "date": as_of,
            "settlement": fields["settlement"],
            "note": note,
        }
    if quote is not None:
        # Futures-linked row with its quote: fill futures price /
        # change / cash price from the feed, per the page's own
        # render rule (see quote_cash_price). A value the quote does
        # not carry stays None — never invented.
        symbol = fields["futures_symbol"]
        exchange = quote.get("exchange")
        futures_price = quote_to_dollars(
            quote.get("rawLast"), symbol=symbol, exchange=exchange
        )
        change = quote_to_dollars(
            quote.get("change"), symbol=symbol, exchange=exchange
        )
        cash_price = quote_cash_price(
            quote.get("rawLast"),
            fields["basis"],
            fields["rounding"],
            symbol=symbol,
            exchange=exchange,
        )
        note = (
            "Basis as published (cents scale); futures price, "
            "change and cash price from the page's quotes feed "
            "(jsquote.php)"
        )
        missing = [
            label
            for label, value in (
                ("futures price", futures_price),
                ("change", change),
                ("cash price", cash_price),
            )
            if value is None
        ]
        if missing:
            note += "; quote present but missing: " + ", ".join(missing)
    else:
        futures_price = None
        change = None
        cash_price = None
        if quotes_given:
            note = (
                "Basis as published (cents scale); no quote for "
                f"{fields['futures_symbol']} in the page's quotes "
                "feed — futures price, change and cash price left "
                "as None, never invented"
            )
        else:
            note = (
                "Basis as published (cents scale); futures price, "
                "change and cash price come from the page's external "
                "quotes feed and are not in the static HTML (futures "
                "month decoded from the contract symbol)"
            )
    return {
        "company": FMN_COMPANY,
        "source": SOURCE_KEY,
        "location": location,
        "commodity": commodity,
        "name": fields["name"],
        "delivery_month": fields["delivery_month"],
        "delivery_end": fields["delivery_end"],
        "cash_price": cash_price,
        "cash_price_mt": None,
        # Basis as published (cents scale — see module docstring);
        # NOT divided by 100, NOT dollars per bushel.
        "basis": fields["basis"],
        "futures_price": futures_price,
        "futures_month": futures_month_from_symbol(fields["futures_symbol"]),
        "futures_symbol": fields["futures_symbol"],
        "last_trade": None,
        "change": change,
        "currency": "CAD",
        "unit": "$/bu",
        "date": as_of,
        "settlement": fields["settlement"],
        "note": note,
    }


def _result(
    *,
    location: str | None,
    rows: list[dict[str, Any]],
    status: str,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "company": FMN_COMPANY,
        "location": location,
        "rows": rows,
        "status": status,
        "notes": notes,
    }


def parse_fmn_html(
    html: str,
    *,
    as_of: str | _date | None = None,
    quotes: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Parse FMN cash-bid HTML (default all-locations view) into rows.

    Only the static page is read: ``homepage_quoteboard`` tables and
    the ``writeBidRow`` calls in each table's ``<tbody>`` script.
    ``quotes`` is an optional mapping from ``parse_quotes_feed`` —
    when given, futures price / change / cash price are filled on
    futures-linked rows whose symbol is in the mapping (per the
    page's own render rule); rows with no quote stay None.
    Returns {"company", "location", "rows", "status", "notes"};
    see the module docstring.
    """
    as_of_iso = _as_of_iso(as_of)
    quotes_given = quotes is not None
    notes: list[str] = [
        "Default all-locations view only: the Location dropdown "
        "lists far more points than the 204 tables, so this is not "
        "the complete FMN set (dropdown filter out of scope).",
    ]
    if quotes_given:
        notes.append(
            "Quotes feed (jsquote.php) applied: futures price, "
            "change and cash price on futures-linked rows come from "
            "the feed (see the per-row note); rows whose symbol is "
            "missing from the feed stay None, never invented.",
        )
    else:
        notes.append(
            "Futures price, change and cash price on futures-linked rows "
            "come from the page's external quotes feed (jsquote.php) and "
            "are not in the static HTML — left as None, never invented; "
            "futures month is decoded from the contract symbol.",
        )
    notes.append(
        "Basis is published as-is in cents scale (see module "
        "docstring); currency CAD and units $/bu ($/t for manual "
        "barley/oats rows) are the FMN Ontario convention — the page "
        "labels no currency or unit.",
    )
    notes.append(
        f"No as-of date is published on the page; date is the fetch date ({as_of_iso}).",
    )

    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table", class_="homepage_quoteboard")
    if not tables:
        return _result(
            location=None,
            rows=[],
            status="unsupported",
            notes=notes
            + [
                "no cash-bid tables found (expected tables with "
                "class 'homepage_quoteboard')"
            ],
        )

    rows: list[dict[str, Any]] = []
    locations: set[str] = set()
    tables_seen = 0
    linked = 0
    filled = 0
    missing_quote = 0
    for table in tables:
        title_row = table.find("tr", class_="section")
        if title_row is None:
            continue
        title = title_row.get_text(" ", strip=True)
        if not title:
            continue
        tables_seen += 1
        location, crop = _split_title(title)
        locations.add(location)
        tbody = table.find("tbody")
        if tbody is None:
            continue
        for script in tbody.find_all("script"):
            for call_text in _extract_calls(script.get_text()):
                fields = _parse_call(_split_args(call_text))
                if fields is None:
                    continue
                quote = None
                if not fields["manual"]:
                    linked += 1
                    if quotes_given:
                        quote = quotes.get(fields["futures_symbol"] or "")
                        if quote is not None:
                            filled += 1
                        else:
                            missing_quote += 1
                rows.append(
                    _make_row(
                        location=location,
                        crop=crop,
                        fields=fields,
                        as_of=as_of_iso,
                        quote=quote,
                        quotes_given=quotes_given,
                    )
                )

    if quotes_given:
        notes.append(
            f"quotes feed applied: {filled} of {linked} futures-linked "
            f"rows filled; {missing_quote} had no quote in the feed"
        )
    notes.append(
        f"parsed {len(rows)} rows from {tables_seen} bid tables "
        f"({len(locations)} delivery points)"
    )
    location = rows[0]["location"] if rows else None
    if not rows:
        return _result(
            location=location,
            rows=[],
            status="empty",
            notes=notes + ["bid tables found but no bid rows parsed"],
        )
    return _result(
        location=location,
        rows=rows,
        status="ok",
        notes=notes,
    )


def fetch_fmn_html(url: str = FMN_URL, timeout: int = 30) -> str:
    """One polite GET with the contact User-Agent."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_fmn_quotes_text(url: str = FMN_QUOTES_URL, timeout: int = 30) -> str:
    """One polite GET of the jsquote quotes feed."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_fmn_quotes(
    url: str = FMN_QUOTES_URL, timeout: int = 30
) -> dict[str, dict[str, str]]:
    """Fetch and parse the jsquote quotes feed into {symbol: fields}."""
    return parse_quotes_feed(fetch_fmn_quotes_text(url, timeout=timeout))


def fetch_fmn_cash(
    url: str = FMN_URL,
    *,
    as_of: str | _date | None = None,
    quotes_url: str = FMN_QUOTES_URL,
) -> dict[str, Any]:
    """Fetch and parse FMN cash bids (default all-locations view).

    Two polite GETs: the cash page and its jsquote quotes feed, which
    fills futures price / change / cash price on futures-linked rows.
    ``as_of`` defaults to the fetch date (America/Toronto) because the
    page publishes no trade date. If the feed fetch fails (or returns
    no symbols), the page still parses with those values left as None
    and a note saying so.
    """
    html = fetch_fmn_html(url)
    try:
        quotes = fetch_fmn_quotes(quotes_url)
    except requests.RequestException as exc:
        result = parse_fmn_html(html, as_of=as_of)
        result["notes"].append(
            "quotes feed fetch failed "
            f"({exc}); futures price, change and cash price left as "
            "None on futures-linked rows"
        )
        return result
    if not quotes:
        result = parse_fmn_html(html, as_of=as_of)
        result["notes"].append(
            "quotes feed returned no symbols; futures price, change "
            "and cash price left as None on futures-linked rows"
        )
        return result
    return parse_fmn_html(html, as_of=as_of, quotes=quotes)
