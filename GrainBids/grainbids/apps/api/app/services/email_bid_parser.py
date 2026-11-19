"""Pure email-bid parsing for the GrainHub price finder.

Parses cash-bid rows out of plain-text email bodies and OCR text recovered
from inline bid-table images.  This module is deliberately dependency-free
(stdlib only) and side-effect-free:

* no Outlook / mailbox access, no network, no sending;
* no database, no file writes (callers own OCR text and image storage);
* no Bank of Canada FX lookup -- FX conversion accepts an ``fx_rate``
  parameter (CAD per USD, the Bank of Canada ``FXUSDCAD`` convention) and
  leaves USD-derived fields blank when none is supplied.

Conventions inherited from the legacy CashGrainBids pipeline
(``CashGrainBids/cashgrainbids/processing.py`` and
``CashGrainBids/email_bid_sources.py``):

* Bushels per metric tonne: corn 39.3683, soybeans/wheat 36.7437.
* Delivery months are normalized to ``"Nov 2026"``, ``"Harvest 2026"``,
  ``"Nov-Dec 2026"`` or ``"Spot"``.
* Futures months use CBOT codes (F/G/H/J/K/M/N/Q/U/V/X/Z + year).
* A printed USD basis is only trusted inside +/-2.00 USD/bu.
* Only complete rows are returned as valid.  Incomplete rows are returned
  separately as rejected, with a reason.  A price is never invented from a
  partial row.
* OCR text is noisy: misread digits are flagged as low-confidence rather
  than silently corrected.

Sender quirks documented in ``CashGrainBids/SETUP.md`` that this module
knows about:

* MacEwen -- "Morning Report" tables quote MT-only prices (no futures);
  the $/bu price is derived from the MT price.
* Andersons -- six-column bid sheet: delivery, futures contract, futures
  price, basis, cash $/bu, cash $/MT.
* BroadGrain (Dylan Stewart), Richardson (Andrea Baron Mancera) and P&H
  (Richard Kricsfalusy) send bid tables as inline images, so their rows
  normally arrive as OCR text.  BroadGrain favours the printed CAD/MT
  price; Richardson prints a USD-basis column whose leading minus OCR can
  lose; P&H prints CAD basis, CAD/bu and CAD/MT plus a USD basis.
* Bunge (jose.borunda@bunge.com) sends basis-only emails: a USD/bu basis
  against a CME contract, with no cash price.  Those rows are complete
  basis quotes, not incomplete cash rows.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

__all__ = [
    "ParsedBidRow",
    "RejectedBidRow",
    "EmailBidParseResult",
    "parse_email_bid_text",
    "parse_ocr_bid_rows",
    "ocr_image_to_text",
    "normalize_delivery_month",
    "normalize_commodity",
    "normalize_futures_month",
    "month_to_key",
    "bu_per_mt",
    "convert_cash_price",
    "convert_currency",
    "usd_basis_from_cad_cash",
    "detect_sender_company",
]

# ---------------------------------------------------------------------------
# Constants (same conventions as CashGrainBids/cashgrainbids/processing.py)
# ---------------------------------------------------------------------------

SOY_BU_PER_MT = 36.7437
CORN_BU_PER_MT = 39.3683
WHEAT_BU_PER_MT = 36.7437

#: USD/bu basis is only trusted inside this range (legacy rule).
MAX_USD_BASIS = 2.00
#: CAD/bu basis outside this range is treated as a parse error, not a basis.
MAX_CAD_BASIS = 5.00
#: Plausible cash-price ranges; outside them a row is rejected, not guessed.
MIN_CASH_PER_BU = 0.50
MAX_CASH_PER_BU = 30.00
MIN_CASH_PER_MT = 50.00
MAX_CASH_PER_MT = 1500.00

_MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_MONTH_LOOKUP: dict[str, int] = {}
for _index, _name in enumerate(_MONTH_NAMES, 1):
    _MONTH_LOOKUP[_name.lower()] = _index
    _MONTH_LOOKUP[_name[:3].lower()] = _index
_MONTH_LOOKUP["sept"] = 9

_FUTURES_MONTH_CODES = {
    "F": "January", "G": "February", "H": "March", "J": "April",
    "K": "May", "M": "June", "N": "July", "Q": "August",
    "U": "September", "V": "October", "X": "November", "Z": "December",
}

#: Canonical commodity names and the spellings that map to them.
COMMODITY_ALIASES: dict[str, str] = {
    "corn": "Corn",
    "maize": "Corn",
    "soybean": "Soybeans",
    "soybeans": "Soybeans",
    "soy": "Soybeans",
    "beans": "Soybeans",
    "wheat": "Wheat",
    "srw wheat": "SRW Wheat",
    "wheat - srw": "SRW Wheat",
    "srw": "SRW Wheat",
    "hrw wheat": "HRW Wheat",
    "wheat - hrw": "HRW Wheat",
    "hrw": "HRW Wheat",
    "hrs wheat": "HRS Wheat",
    "wheat - hrs": "HRS Wheat",
    "hrs": "HRS Wheat",
    "canola": "Canola",
    "oats": "Oats",
    "barley": "Barley",
    "rye": "Rye",
}

#: Sender identities from SETUP.md / the legacy Outlook matcher.
_SENDER_COMPANIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("MacEwen", ("macewen", "morning report")),
    ("Andersons", ("andersons", "anderson", "producer commodity bid sheet")),
    ("BroadGrain", ("broadgrain", "dylan stewart", "dylan.stewart@broadgrain.com")),
    ("Richardson", ("richardson", "andrea baron mancera", "andrea.baronmancera@richardson.ca")),
    ("P&H", ("p&h", "parrish", "richard kricsfalusy", "rkricsfalusy@pandh.ca")),
    ("Bunge", ("bunge", "jose.borunda@bunge.com", "jose borunda")),
)

#: MacEwen location labels (legacy ``parse_macewen`` location map).
_MACEWEN_LOCATIONS = {
    "cobden": "MacEwen Cobden",
    "maxville": "MacEwen Maxville",
    "port prescott": "Port Prescott",
}

#: Characters OCR commonly confuses with digits.
_OCR_AMBIGUOUS_LETTERS = set("lIOSsBgOio")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ParsedBidRow:
    """One complete, validated bid row."""

    company: str
    commodity: str
    delivery_month: str
    cash_price: float | None = None
    cash_price_unit: str | None = None  # "bu" or "mt" (unit as quoted)
    currency: str = "CAD"
    basis: float | None = None  # CAD/bu unless basis_currency == "USD"
    basis_currency: str | None = None
    futures_month: str | None = None
    futures_price: float | None = None
    us_basis_usd_per_bu: float | None = None
    location: str | None = None
    # Normalized equivalents, derived only from printed values.
    cash_price_cad_per_bu: float | None = None
    cash_price_cad_per_mt: float | None = None
    cash_price_usd_per_bu: float | None = None
    confidence: float = 1.0
    notes: list[str] = field(default_factory=list)
    raw_text: str = ""
    source: str = "text"  # "text" or "ocr"

    @property
    def delivery_key(self) -> str:
        """Sortable key: ``YYYY-MM``, ``YYYY-harvest`` or ``spot``."""
        return month_to_key(self.delivery_month)

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "commodity": self.commodity,
            "delivery_month": self.delivery_month,
            "delivery_key": self.delivery_key,
            "cash_price": self.cash_price,
            "cash_price_unit": self.cash_price_unit,
            "currency": self.currency,
            "basis": self.basis,
            "basis_currency": self.basis_currency,
            "futures_month": self.futures_month,
            "futures_price": self.futures_price,
            "us_basis_usd_per_bu": self.us_basis_usd_per_bu,
            "location": self.location,
            "cash_price_cad_per_bu": self.cash_price_cad_per_bu,
            "cash_price_cad_per_mt": self.cash_price_cad_per_mt,
            "cash_price_usd_per_bu": self.cash_price_usd_per_bu,
            "confidence": self.confidence,
            "notes": list(self.notes),
            "raw_text": self.raw_text,
            "source": self.source,
        }


@dataclass
class RejectedBidRow:
    """A candidate row that could not be validated. Never silently fixed."""

    raw_text: str
    reason: str
    status: str = "rejected"  # "incomplete" (missing field) or "rejected"
    company: str | None = None
    commodity: str | None = None
    fields_present: list[str] = field(default_factory=list)


@dataclass
class EmailBidParseResult:
    company: str
    sender: str = ""
    subject: str = ""
    valid_rows: list[ParsedBidRow] = field(default_factory=list)
    rejected_rows: list[RejectedBidRow] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return len(self.valid_rows) + len(self.rejected_rows)

    @property
    def parse_success_rate(self) -> float:
        if not self.total_rows:
            return 1.0
        return len(self.valid_rows) / self.total_rows


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def bu_per_mt(commodity: str) -> float:
    """Bushels per metric tonne for a commodity (legacy factors)."""
    return CORN_BU_PER_MT if commodity.strip().lower() == "corn" else SOY_BU_PER_MT


def convert_cash_price(
    value: float, from_unit: str, to_unit: str, commodity: str
) -> float | None:
    """Convert a cash price between $/bu and $/MT for a commodity."""
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()
    if from_unit == to_unit:
        return value
    factor = bu_per_mt(commodity)
    if from_unit in {"bu", "bushel", "bushels"} and to_unit in {"mt", "t", "tonne", "tonnes"}:
        return value * factor
    if from_unit in {"mt", "t", "tonne", "tonnes"} and to_unit in {"bu", "bushel", "bushels"}:
        return value / factor
    return None


def convert_currency(
    amount: float, from_currency: str, to_currency: str, fx_rate: float | None
) -> float | None:
    """Convert between CAD and USD.

    ``fx_rate`` is CAD per USD (Bank of Canada ``FXUSDCAD`` convention).
    Returns ``None`` when conversion is impossible -- no rate supplied, or
    the currencies are not CAD/USD -- instead of guessing a rate.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    if from_currency == to_currency:
        return amount
    if fx_rate is None or fx_rate <= 0:
        return None
    if from_currency == "USD" and to_currency == "CAD":
        return amount * fx_rate
    if from_currency == "CAD" and to_currency == "USD":
        return amount / fx_rate
    return None


def usd_basis_from_cad_cash(
    cash_cad_per_bu: float | None,
    futures_price_usd: float | None,
    fx_rate: float | None,
) -> float | None:
    """USD/bu basis from a CAD cash price and a USD futures price.

    Mirrors the legacy ``add_us_basis_from_spot`` economics (USD cash minus
    futures) without fetching any FX rate.  Returns ``None`` when an input
    is missing, and also when the result falls outside the trusted
    +/-2.00 USD/bu range -- the caller must leave the field blank rather
    than store an implausible basis.
    """
    if cash_cad_per_bu is None or futures_price_usd is None or not fx_rate:
        return None
    usd_cash = cash_cad_per_bu / fx_rate
    basis = usd_cash - futures_price_usd
    if abs(basis) > MAX_USD_BASIS:
        return None
    return round(basis, 4)


def normalize_commodity(value: str) -> str | None:
    """Canonical commodity name, or ``None`` for an unknown commodity."""
    key = " ".join(str(value or "").strip().lower().split())
    if not key:
        return None
    if key in COMMODITY_ALIASES:
        return COMMODITY_ALIASES[key]
    for alias, canonical in COMMODITY_ALIASES.items():
        if alias in key:
            return canonical
    return None


def normalize_futures_month(code: str) -> str | None:
    """CBOT futures code (``CH27``, ``SX26``) -> ``"March 2027"``."""
    raw = re.sub(r"[^A-Za-z0-9]", "", str(code or "")).upper()
    match = re.search(r"([FGHJKMNQUVXZ])(\d{1,2})$", raw)
    if not match:
        return None
    month_code, year_text = match.groups()
    year = 2020 + int(year_text) if len(year_text) == 1 else 2000 + int(year_text)
    return f"{_FUTURES_MONTH_CODES[month_code]} {year}"


def _expand_year(year_text: str | None, *, reference_year: int | None = None) -> int | None:
    if not year_text:
        return reference_year or datetime.now().year
    year = int(year_text)
    return 2000 + year if year < 100 else year


_MONTH_WORD = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DELIVERY_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    # Harvest 2026 / Harvest-26 / Récoltes/Harvest 2026
    (re.compile(rf"(?:r[ée]coltes?/)?harvest[\s\-]*(\d{{2,4}})?", re.I), "harvest"),
    # Nov-Dec 2026 (delivery range)
    (re.compile(rf"{_MONTH_WORD}\s*-\s*{_MONTH_WORD}\s+(\d{{2,4}})", re.I), "range"),
    # 26-Nov (reversed, as printed by P&H/Richard)
    (re.compile(rf"(\d{{2}})-{_MONTH_WORD}\b", re.I), "reversed"),
    # Dec26 (compact)
    (re.compile(rf"\b{_MONTH_WORD}(\d{{2}})\b", re.I), "compact"),
    # Nov 2026 / Nov-26 / Nov 26 / November 2026
    (re.compile(rf"\b{_MONTH_WORD}[\s\-]+(\d{{2,4}})\b", re.I), "standard"),
    # Bare month name -> current year
    (re.compile(rf"\b{_MONTH_WORD}\b", re.I), "bare"),
    # Spot / nearby
    (re.compile(r"\b(spot|nearby|cash)\b", re.I), "spot"),
)


def normalize_delivery_month(value: str, *, reference_year: int | None = None) -> str | None:
    """Normalize a delivery label to ``"Nov 2026"`` / ``"Harvest 2026"`` / ``"Spot"``.

    Returns ``None`` when the label cannot be understood.  A bare month
    name takes the current year (or ``reference_year`` when given).
    """
    raw = " ".join(str(value or "").strip().split())
    if not raw:
        return None
    for pattern, kind in _DELIVERY_PATTERNS:
        match = pattern.search(raw)
        if not match:
            continue
        if kind == "harvest":
            year = _expand_year(match.group(1), reference_year=reference_year)
            return f"Harvest {year}"
        if kind == "range":
            start, end, year_text = match.group(1), match.group(2), match.group(3)
            year = _expand_year(year_text, reference_year=reference_year)
            return f"{start[:3].title()}-{end[:3].title()} {year}"
        if kind == "reversed":
            year_text, month = match.group(1), match.group(2)
            year = _expand_year(year_text, reference_year=reference_year)
            return f"{month[:3].title()} {year}"
        if kind in {"compact", "standard"}:
            month, year_text = match.group(1), match.group(2)
            year = _expand_year(year_text, reference_year=reference_year)
            return f"{month[:3].title()} {year}"
        if kind == "bare":
            month = match.group(1)
            year = reference_year or datetime.now().year
            return f"{month[:3].title()} {year}"
        if kind == "spot":
            return "Spot"
    return None


def month_to_key(value: str) -> str:
    """Sortable key for a normalized delivery label."""
    raw = str(value or "").strip()
    harvest = re.match(r"^Harvest (\d{4})$", raw, re.I)
    if harvest:
        return f"{harvest.group(1)}-harvest"
    if raw.lower() == "spot":
        return "spot"
    match = re.match(r"^([A-Za-z]{3})-([A-Za-z]{3}) (\d{4})$", raw)
    if match:
        month = _MONTH_LOOKUP.get(match.group(1).lower())
        return f"{match.group(3)}-{month:02d}" if month else raw.lower()
    match = re.match(r"^([A-Za-z]{3,9}) (\d{4})$", raw)
    if match:
        month = _MONTH_LOOKUP.get(match.group(1).lower())
        return f"{match.group(2)}-{month:02d}" if month else raw.lower()
    return raw.lower()


def detect_sender_company(sender: str = "", subject: str = "", body_text: str = "") -> str:
    """Identify the email sender company from sender/subject/body text."""
    searchable = f"{sender} {subject} {body_text[:2000]}".lower()
    for company, markers in _SENDER_COMPANIES:
        if any(marker in searchable for marker in markers):
            return company
    return "Unknown"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _html_to_lines(text: str) -> list[str]:
    """Flatten an HTML or plain-text body into clean, non-empty lines."""
    plain = html.unescape(str(text or ""))
    plain = re.sub(r"<br[^>]*>", "\n", plain, flags=re.I)
    plain = re.sub(r"</(p|div|tr|li|h[1-6])>", "\n", plain, flags=re.I)
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = plain.replace("\xa0", " ").replace("\u200b", "")
    return [re.sub(r"\s+", " ", line).strip() for line in plain.splitlines() if line.strip()]


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b)))
        previous = current
    return previous[-1]


def _fuzzy_month_word(token: str) -> str | None:
    """Match an OCR-mangled month word (edit distance <= 2, min length 4).

    Used only for OCR text, and the caller flags the row low-confidence.
    """
    token = token.strip().lower()
    if len(token) < 4 or token in _MONTH_LOOKUP:
        return None
    best: str | None = None
    best_distance = 3
    for candidate in {name.lower() for name in _MONTH_NAMES} | {"sept"}:
        distance = _levenshtein(token, candidate)
        if distance < best_distance:
            best, best_distance = candidate, distance
    return best.title() if best and best_distance <= 2 else None


_NUMBER_RE = re.compile(r"[-+]?\$?\s*\d[\d,]*(?:\.\d+)?|[-+]?\.\d+")
_EIGHTHS_RE = re.compile(r"^(\d{1,2})-([0-7])$")
# CBOT contract: optional commodity letter(s) + month code + 1-2 digit year
# (CH27 corn/March 2027, SX26 soy/November 2026, WN26 wheat/July 2026).
_CONTRACT_RE = re.compile(r"\b([A-Z]{0,2}[FGHJKMNQUVXZ]\d{1,2})\b", re.I)
_USD_BASIS_RANGE = (-MAX_USD_BASIS, MAX_USD_BASIS)


def _strip_delivery(line: str) -> tuple[str | None, str]:
    """Return (normalized delivery month, line with the delivery token removed)."""
    for pattern, _kind in _DELIVERY_PATTERNS:
        match = pattern.search(line)
        if match:
            month = normalize_delivery_month(match.group(0))
            remainder = line[: match.start()] + " " + line[match.end():]
            return month, remainder
    return None, line


def _extract_contract(line: str) -> tuple[str | None, str]:
    """Pull a CBOT contract code (CH27, SX26, WN26) out of a line."""
    match = _CONTRACT_RE.search(line)
    if not match:
        return None, line
    code = match.group(1).upper()
    return code, line[: match.start()] + " " + line[match.end():]


def _ocr_suspect_tokens(line: str) -> list[str]:
    """Whitespace tokens where OCR may have misread a digit.

    A token counts as suspect when it mixes digits with a letter OCR
    confuses with a digit (l/I/O/S/B/g).  Callers pass the line with the
    delivery token and contract code already removed, so month words and
    contract codes are never flagged.
    """
    suspects: list[str] = []
    for token in line.split():
        if re.search(r"\d", token) and any(
            char in _OCR_AMBIGUOUS_LETTERS for char in token if char.isalpha()
        ):
            suspects.append(token)
    return suspects


def _tokenize_numbers(line: str) -> tuple[list[float], list[str]]:
    """Numeric tokens in a line, keeping the raw token for OCR flagging."""
    values: list[float] = []
    raws: list[str] = []
    for match in _NUMBER_RE.finditer(line):
        raw = match.group(0)
        cleaned = raw.replace("$", "").replace(",", "").strip()
        eighths = _EIGHTHS_RE.match(cleaned)
        try:
            if eighths:
                values.append(int(eighths.group(1)) + int(eighths.group(2)) / 8)
            else:
                values.append(float(cleaned))
        except ValueError:
            continue
        raws.append(raw)
    return values, raws


def _clean_ocr_line(line: str) -> str:
    """Remove OCR grid/artefact characters without touching digits."""
    return (
        line.replace("|", " ")
        .replace("_", " ")
        .replace("§", " ")
        .replace("Â", " ")
        .replace('"', " ")
        .replace("'", " ")
    )


# ---------------------------------------------------------------------------
# Row construction / validation
# ---------------------------------------------------------------------------

def _finalize_row(
    *,
    company: str,
    commodity: str,
    delivery_month: str,
    cash_price: float | None,
    cash_price_unit: str | None,
    currency: str,
    basis: float | None,
    basis_currency: str | None,
    futures_month: str | None,
    futures_price: float | None,
    us_basis: float | None,
    location: str | None,
    raw_text: str,
    source: str,
    confidence: float,
    notes: list[str],
    fx_rate: float | None,
) -> tuple[ParsedBidRow | None, RejectedBidRow | None]:
    """Validate a candidate row. Complete rows pass; the rest are rejected."""
    fields = ["company", "commodity", "delivery_month"]
    if cash_price is not None:
        fields.append("cash_price")
    if basis is not None:
        fields.append("basis")

    if cash_price is None and basis is None and us_basis is None:
        return None, RejectedBidRow(
            raw_text=raw_text, reason="missing cash price and basis",
            status="incomplete", company=company, commodity=commodity,
            fields_present=fields,
        )
    if cash_price is not None:
        if cash_price_unit == "mt":
            if not MIN_CASH_PER_MT <= cash_price <= MAX_CASH_PER_MT:
                return None, RejectedBidRow(
                    raw_text=raw_text,
                    reason=f"cash price {cash_price} $/MT outside plausible range",
                    status="rejected", company=company, commodity=commodity,
                    fields_present=fields,
                )
        elif not MIN_CASH_PER_BU <= cash_price <= MAX_CASH_PER_BU:
            return None, RejectedBidRow(
                raw_text=raw_text,
                reason=f"cash price {cash_price} $/bu outside plausible range",
                status="rejected", company=company, commodity=commodity,
                fields_present=fields,
            )
    if basis is not None and basis_currency == "USD" and not (
        _USD_BASIS_RANGE[0] <= basis <= _USD_BASIS_RANGE[1]
    ):
        return None, RejectedBidRow(
            raw_text=raw_text,
            reason=f"USD basis {basis} outside trusted +/-{MAX_USD_BASIS:.2f} USD/bu range",
            status="rejected", company=company, commodity=commodity,
            fields_present=fields,
        )
    if basis is not None and basis_currency != "USD" and abs(basis) > MAX_CAD_BASIS:
        return None, RejectedBidRow(
            raw_text=raw_text,
            reason=f"CAD basis {basis} outside plausible +/-{MAX_CAD_BASIS:.2f} range",
            status="rejected", company=company, commodity=commodity,
            fields_present=fields,
        )

    cash_cad_bu: float | None = None
    cash_cad_mt: float | None = None
    cash_usd_bu: float | None = None
    if cash_price is not None and cash_price_unit:
        if cash_price_unit == "mt":
            cash_cad_mt = convert_currency(cash_price, currency, "CAD", fx_rate)
            if currency == "CAD":
                cash_cad_mt = cash_price
            cash_bu_as_quoted = convert_cash_price(cash_price, "mt", "bu", commodity)
            cash_cad_bu = (
                convert_currency(cash_bu_as_quoted, currency, "CAD", fx_rate)
                if cash_bu_as_quoted is not None
                else None
            )
            if currency == "CAD" and cash_bu_as_quoted is not None:
                cash_cad_bu = cash_bu_as_quoted
        else:
            cash_cad_bu = convert_currency(cash_price, currency, "CAD", fx_rate)
            if currency == "CAD":
                cash_cad_bu = cash_price
            cash_mt_as_quoted = convert_cash_price(cash_price, "bu", "mt", commodity)
            cash_cad_mt = (
                convert_currency(cash_mt_as_quoted, currency, "CAD", fx_rate)
                if cash_mt_as_quoted is not None
                else None
            )
            if currency == "CAD" and cash_mt_as_quoted is not None:
                cash_cad_mt = cash_mt_as_quoted
        if cash_cad_bu is not None:
            cash_usd_bu = convert_currency(cash_cad_bu, "CAD", "USD", fx_rate)

    derived_us_basis = us_basis
    if derived_us_basis is None and cash_cad_bu is not None and futures_price is not None:
        derived_us_basis = usd_basis_from_cad_cash(cash_cad_bu, futures_price, fx_rate)

    return ParsedBidRow(
        company=company,
        commodity=commodity,
        delivery_month=delivery_month,
        cash_price=cash_price,
        cash_price_unit=cash_price_unit,
        currency=currency,
        basis=basis,
        basis_currency=basis_currency,
        futures_month=futures_month,
        futures_price=futures_price,
        us_basis_usd_per_bu=derived_us_basis,
        location=location,
        cash_price_cad_per_bu=round(cash_cad_bu, 4) if cash_cad_bu is not None else None,
        cash_price_cad_per_mt=round(cash_cad_mt, 2) if cash_cad_mt is not None else None,
        cash_price_usd_per_bu=round(cash_usd_bu, 4) if cash_usd_bu is not None else None,
        confidence=confidence,
        notes=notes,
        raw_text=raw_text,
        source=source,
    ), None


def _currency_and_unit_hints(line: str, header_text: str = "") -> tuple[str, str | None]:
    """Currency (CAD default) and price unit hinted at by a line/header."""
    haystack = f"{header_text} {line}".lower()
    currency = "USD" if re.search(r"\busd\b|\$/us|us\s*\$", haystack) else "CAD"
    unit: str | None = None
    if re.search(r"/\s*(mt|t\b|tonne)", haystack) or "per tonne" in haystack or "per mt" in haystack:
        unit = "mt"
    elif re.search(r"/\s*bu\b|per bushel|/\s*bushel", haystack):
        unit = "bu"
    return currency, unit


def _parse_generic_row(
    line: str,
    *,
    company: str,
    commodity: str | None,
    location: str | None,
    source: str,
    fx_rate: float | None,
    header_text: str = "",
) -> tuple[ParsedBidRow | None, RejectedBidRow | None]:
    """Parse one table-style row: delivery token followed by numbers.

    Number order follows the legacy sheets: basis, futures price, cash
    $/bu, cash $/MT (later numbers override earlier interpretations when
    their magnitude proves the unit -- a value above $30/bu must be $/MT).
    """
    raw_line = line
    notes: list[str] = []
    confidence = 1.0

    if source == "ocr":
        line = _clean_ocr_line(line)
        if line != raw_line:
            confidence = 0.5
            notes.append("OCR: artefact characters removed from line")

    # Delivery token first -- it also contains digits ("26-Nov", "Dec26").
    delivery_month, line_wo_delivery = _strip_delivery(line)
    if source == "ocr" and delivery_month is None:
        # One-character OCR mangling of a month word, flagged not corrected.
        for token in re.findall(r"[A-Za-z]{4,9}", line):
            fuzzy = _fuzzy_month_word(token)
            if fuzzy:
                year_match = re.search(r"(\d{2,4})", line)
                year = _expand_year(year_match.group(1)) if year_match else datetime.now().year
                delivery_month = f"{fuzzy[:3]} {year}"
                confidence = min(confidence, 0.75)
                notes.append(f"OCR: delivery month read as '{token}' (fuzzy match to {fuzzy})")
                break
    if delivery_month is None:
        return None, None  # Not a bid row at all; caller skips silently.

    contract, line_wo_contract = _extract_contract(line_wo_delivery)

    # A commodity named inline in the row wins over the section header.
    inline_commodity = normalize_commodity(line_wo_contract)
    effective_commodity = inline_commodity or commodity
    if effective_commodity is None and contract:
        # Legacy BroadGrain behaviour: the contract's commodity letter
        # (S/C/W) identifies the row when no heading was recognised.
        # A W-series contract means SRW Wheat for BroadGrain OCR, where
        # the "Wheat - SRW" heading is the one OCR most often loses.
        first_letter = contract[0]
        if first_letter == "S":
            effective_commodity = "Soybeans"
        elif first_letter == "C":
            effective_commodity = "Corn"
        elif first_letter == "W":
            effective_commodity = "SRW Wheat" if company == "BroadGrain" else "Wheat"
        if effective_commodity is not None:
            notes.append(f"Commodity inferred from futures contract {contract}")
    if effective_commodity is None:
        return None, RejectedBidRow(
            raw_text=raw_line, reason="unknown commodity",
            status="rejected", company=company, commodity=None,
            fields_present=["delivery_month"],
        )

    futures_month = normalize_futures_month(contract) if contract else None

    currency, unit_hint = _currency_and_unit_hints(line, header_text)
    numbers, _raw_numbers = _tokenize_numbers(line_wo_contract)
    if source == "ocr":
        for suspect in _ocr_suspect_tokens(line_wo_contract):
            confidence = min(confidence, 0.5)
            notes.append(
                f"OCR: possible misread digit in '{suspect}' "
                "(low confidence, not corrected)"
            )

    if not numbers:
        return None, RejectedBidRow(
            raw_text=raw_line, reason="missing cash price and basis",
            status="incomplete", company=company, commodity=effective_commodity,
            fields_present=["commodity", "delivery_month"],
        )

    basis: float | None = None
    basis_currency: str | None = None
    futures_price: float | None = None
    cash_price: float | None = None
    cash_unit: str | None = None

    # A trailing value far above any $/bu price must be a $/MT price.
    if numbers[-1] > MAX_CASH_PER_BU and (unit_hint != "bu"):
        cash_price = numbers[-1]
        cash_unit = "mt"
        numbers = numbers[:-1]
    elif unit_hint == "mt":
        cash_price = numbers[-1]
        cash_unit = "mt"
        numbers = numbers[:-1]
    elif len(numbers) >= 2 and unit_hint is None:
        # Last number is the cash price unless it looks like a basis.
        cash_price = numbers[-1]
        cash_unit = "bu"
        numbers = numbers[:-1]
    elif len(numbers) == 1:
        cash_price = numbers[0]
        cash_unit = "bu"
        numbers = []

    if numbers:
        # Remaining numbers, in legacy order: basis, futures price.
        basis = numbers[0]
        basis_currency = currency
        if len(numbers) >= 2:
            futures_price = numbers[1]
            # P&H OCR quirk: grid lines read as a leading "1" on corn
            # futures (14.8275 instead of 4.8275). Corn futures are
            # otherwise below $10.
            if (
                source == "ocr"
                and company == "P&H"
                and effective_commodity == "Corn"
                and 10 <= futures_price < 20
            ):
                futures_price = round(futures_price - 10, 4)
                notes.append("OCR: P&H corn futures corrected for grid-line '1' prefix")

    return _finalize_row(
        company=company,
        commodity=effective_commodity,
        delivery_month=delivery_month,
        cash_price=cash_price,
        cash_price_unit=cash_unit,
        currency=currency,
        basis=basis,
        basis_currency=basis_currency,
        futures_month=futures_month,
        futures_price=futures_price,
        us_basis=None,
        location=location,
        raw_text=raw_line,
        source=source,
        confidence=confidence,
        notes=notes,
        fx_rate=fx_rate,
    )


# ---------------------------------------------------------------------------
# Sender-specific parsers
# ---------------------------------------------------------------------------

_BUNGE_SECTION_RE = re.compile(r"\b(soybeans?|corn)\s+(bcc|mtl)\b", re.I)
_BUNGE_BID_RE = re.compile(
    r"^\s*([A-Za-z]{3,9}-\d{2})(?:\s+\d{1,2}-\d{1,2}(?:st|nd|rd|th)?\.?)?\s*:?\s*"
    r"([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*([A-Z]{1,3}\d{2})\b",
    re.I,
)


def _parse_bunge_lines(lines: list[str], *, fx_rate: float | None) -> tuple[list[ParsedBidRow], list[RejectedBidRow]]:
    """Bunge basis-only emails: sections like ``Soybeans BCC`` then rows
    like ``Nov-26: +0.45 CH27``.  Cash price is intentionally absent."""
    valid: list[ParsedBidRow] = []
    rejected: list[RejectedBidRow] = []
    commodity: str | None = None
    location: str | None = None
    for line in lines:
        section = _BUNGE_SECTION_RE.search(line)
        if section:
            commodity = "Soybeans" if section.group(1).lower().startswith("soy") else "Corn"
            location = f"Bunge {section.group(2).upper()}"
            continue
        match = _BUNGE_BID_RE.match(line)
        if not match or not commodity or not location:
            continue
        delivery_raw, basis_raw, contract = match.groups()
        delivery_month = normalize_delivery_month(delivery_raw)
        if delivery_month is None:
            rejected.append(RejectedBidRow(
                raw_text=line, reason="unparseable delivery month",
                status="incomplete", company="Bunge", commodity=commodity,
                fields_present=["commodity"],
            ))
            continue
        try:
            basis = float(basis_raw)
        except ValueError:
            rejected.append(RejectedBidRow(
                raw_text=line, reason="unparseable USD basis",
                status="incomplete", company="Bunge", commodity=commodity,
                fields_present=["commodity", "delivery_month"],
            ))
            continue
        row, rejection = _finalize_row(
            company="Bunge", commodity=commodity, delivery_month=delivery_month,
            cash_price=None, cash_price_unit=None, currency="USD",
            basis=basis, basis_currency="USD",
            futures_month=normalize_futures_month(contract),
            futures_price=None, us_basis=basis, location=location,
            raw_text=line, source="text", confidence=1.0, notes=[],
            fx_rate=fx_rate,
        )
        if row is not None:
            valid.append(row)
        elif rejection is not None:
            rejected.append(rejection)
    return valid, rejected


def _parse_macewen_lines(lines: list[str], *, fx_rate: float | None) -> tuple[list[ParsedBidRow], list[RejectedBidRow]]:
    """MacEwen "Morning Report": commodity sections, a location header row,
    then delivery rows with one MT price per location column.  MT-only: no
    futures price, so no USD basis is derived."""
    valid: list[ParsedBidRow] = []
    rejected: list[RejectedBidRow] = []
    commodity: str | None = None
    locations: dict[int, str] = {}
    for line in lines:
        lower = line.lower()
        if "corn" in lower and len(line.split()) <= 3:
            commodity = "Corn"
            locations = {}
            continue
        if "soybean" in lower and len(line.split()) <= 3:
            commodity = "Soybeans"
            locations = {}
            continue
        if "wheat" in lower and len(line.split()) <= 3:
            commodity = "Wheat"
            locations = {}
            continue
        if not commodity:
            continue
        delivery_month, remainder = _strip_delivery(line)
        if delivery_month is not None and re.search(r"\d", remainder):
            _values, _raws = _tokenize_numbers(remainder)
            # Skip the location header row itself (no delivery + no numbers
            # is handled below); a delivery row must carry prices.
            if not _values:
                rejected.append(RejectedBidRow(
                    raw_text=line, reason="missing cash price and basis",
                    status="incomplete", company="MacEwen", commodity=commodity,
                    fields_present=["commodity", "delivery_month"],
                ))
                continue
            for index, mt_price in enumerate(_values):
                location = locations.get(index, f"Column {index + 1}")
                row, rejection = _finalize_row(
                    company="MacEwen", commodity=commodity,
                    delivery_month=delivery_month, cash_price=mt_price,
                    cash_price_unit="mt", currency="CAD",
                    basis=None, basis_currency=None,
                    futures_month=None, futures_price=None, us_basis=None,
                    location=location, raw_text=line, source="text",
                    confidence=1.0, notes=["MT-only quote; $/bu derived"],
                    fx_rate=fx_rate,
                )
                if row is not None:
                    valid.append(row)
                elif rejection is not None:
                    rejected.append(rejection)
            continue
        # Header row: location names, no $ prices.  In flattened text the
        # columns are space-separated, so match known multi-word locations
        # greedily and treat any other word as its own location.
        if any(token in lower for token in ("maxville", "prescott", "cardinal", "johnstown", "cobden", "montreal", "testville")):
            words = line.split()
            locations = {}
            index = 0
            while index < len(words):
                two_word = " ".join(words[index:index + 2]).lower()
                if two_word in _MACEWEN_LOCATIONS:
                    locations[len(locations)] = _MACEWEN_LOCATIONS[two_word]
                    index += 2
                    continue
                word = words[index]
                if not word.startswith("$"):
                    key = word.lower()
                    locations[len(locations)] = _MACEWEN_LOCATIONS.get(key, word.title())
                index += 1
    return valid, rejected


def _parse_andersons_lines(lines: list[str], *, fx_rate: float | None) -> tuple[list[ParsedBidRow], list[RejectedBidRow]]:
    """Andersons six-column sheet: delivery, futures contract, futures
    price, basis, cash $/bu, cash $/MT -- under commodity/location headers."""
    valid: list[ParsedBidRow] = []
    rejected: list[RejectedBidRow] = []
    commodity: str | None = None
    location: str | None = None
    for line in lines:
        lower = line.lower()
        if lower in {"corn", "soybeans", "soybeans / soya", "wheat"}:
            commodity = "Soybeans" if "soy" in lower else line.title()
            location = None
            continue
        if lower in {"ship mo", "ship month"}:
            continue
        delivery_month, remainder = _strip_delivery(line)
        if delivery_month is None:
            # A single-token line under a commodity section is a location.
            if commodity and line and not re.search(r"\d", line) and len(line.split()) <= 4:
                location = line.title()
            continue
        if not commodity or not location:
            rejected.append(RejectedBidRow(
                raw_text=line, reason="missing commodity or location context",
                status="incomplete", company="Andersons", commodity=commodity,
                fields_present=["delivery_month"],
            ))
            continue
        contract, remainder = _extract_contract(remainder)
        numbers, _raws = _tokenize_numbers(remainder)
        if len(numbers) < 4:
            rejected.append(RejectedBidRow(
                raw_text=line, reason="incomplete Andersons row: expected futures, basis, cash $/bu, cash $/MT",
                status="incomplete", company="Andersons", commodity=commodity,
                fields_present=["commodity", "delivery_month"],
            ))
            continue
        futures_price, basis, cash_bu, _cash_mt = numbers[:4]
        row, rejection = _finalize_row(
            company="Andersons", commodity=commodity,
            delivery_month=delivery_month, cash_price=cash_bu,
            cash_price_unit="bu", currency="CAD",
            basis=basis, basis_currency="CAD",
            futures_month=normalize_futures_month(contract) if contract else None,
            futures_price=futures_price, us_basis=None, location=location,
            raw_text=line, source="text", confidence=1.0, notes=[],
            fx_rate=fx_rate,
        )
        if row is not None:
            valid.append(row)
        elif rejection is not None:
            rejected.append(rejection)
    return valid, rejected


_PANDH_LOCATIONS = ("Prescott", "Picton", "DLVD Johnstown/Cardinal")
_PANDH_ROW_RE = re.compile(
    r"^(?P<delivery>\d{2}-[A-Za-z]{3,9}).*?"
    r"(?P<futures>\d+\.\d+).*?"
    r"(?P<contract>z?[sc][a-z]{1,3}\d{2}).*?"
    r"(?P<us_basis_mt>-?\d+\.\d+).*?"
    r"(?P<fx>\d+\.\d+).*?"
    r"(?P<fx_month>ca[a-z0-9]*\d{1,2}).*?"
    r"(?P<basis>-?\d+\.\d+).*?"
    r"(?P<cash>\d+\.\d+).*?"
    r"(?P<mt>\d+\.\d+).*?"
    r"(?P<us_basis>[+-]?\d+(?:\.\d+)?)\s*$",
    re.I,
)


def _parse_pandh_ocr_row(
    line: str, *, location: str | None, fx_rate: float | None
) -> tuple[ParsedBidRow | None, RejectedBidRow | None]:
    """P&H OCR row: delivery, futures, contract, US basis/MT, FX, FX month,
    CAD basis, CAD/bu, CAD/MT, USD basis.  Mirrors the legacy column order."""
    match = _PANDH_ROW_RE.search(line.replace("|", " ").replace("_", " "))
    if not match:
        return None, None
    values = match.groupdict()
    contract = values["contract"]
    commodity = "Soybeans" if contract[0].lower() == "s" or "s" in contract[1:2].lower() else "Corn"
    # Contract letters are commodity + month (SX26 = soy/November 2026);
    # normalize_futures_month finds the month code at the end.
    futures_price = float(values["futures"])
    notes: list[str] = []
    # Grid lines can be read as a leading "1" on P&H corn futures
    # (14.8275 instead of 4.8275). Corn futures are otherwise below $10.
    if commodity == "Corn" and 10 <= futures_price < 20:
        futures_price = round(futures_price - 10, 4)
        notes.append("OCR: P&H corn futures corrected for grid-line '1' prefix")
    delivery_month = normalize_delivery_month(values["delivery"])
    if delivery_month is None:
        return None, RejectedBidRow(
            raw_text=line, reason="unparseable delivery month",
            status="incomplete", company="P&H", commodity=commodity,
            fields_present=["commodity"],
        )
    try:
        us_basis = float(values["us_basis"])
    except ValueError:
        us_basis = None
    return _finalize_row(
        company="P&H", commodity=commodity, delivery_month=delivery_month,
        cash_price=float(values["cash"]), cash_price_unit="bu", currency="CAD",
        basis=float(values["basis"]), basis_currency="CAD",
        futures_month=normalize_futures_month(contract),
        futures_price=futures_price, us_basis=us_basis, location=location,
        raw_text=line, source="ocr", confidence=1.0, notes=notes,
        fx_rate=fx_rate,
    )


def _parse_generic_lines(
    lines: list[str],
    *,
    company: str,
    source: str,
    fx_rate: float | None,
) -> tuple[list[ParsedBidRow], list[RejectedBidRow]]:
    """Section-aware generic table parsing (text or OCR)."""
    valid: list[ParsedBidRow] = []
    rejected: list[RejectedBidRow] = []
    commodity: str | None = None
    location: str | None = None
    header_text = ""
    for line in lines:
        lower = line.lower()
        if "#value!" in lower:
            continue  # P&H OCR: formula error cell, never a bid.
        if lower.startswith("unconfirmed"):
            continue
        if company == "P&H" and source == "ocr":
            for candidate in _PANDH_LOCATIONS:
                if candidate.lower() in lower:
                    location = candidate
            if re.match(r"^\d{2}-[A-Za-z]{3,9}\b", line):
                row, rejection = _parse_pandh_ocr_row(
                    line, location=location, fx_rate=fx_rate
                )
                if row is not None:
                    valid.append(row)
                    continue
                if rejection is not None:
                    rejected.append(rejection)
                    continue
        section_commodity = normalize_commodity(line)
        if section_commodity and len(line.split()) <= 3 and not re.search(r"\d", line):
            commodity = section_commodity
            continue
        if "wheat - srw" in lower:
            commodity = "SRW Wheat"
            continue
        if "wheat - hrw" in lower:
            commodity = "HRW Wheat"
            continue
        if "wheat - hrs" in lower:
            commodity = "HRS Wheat"
            continue
        delivery_location = re.search(r"del\s*-?\s*([A-Za-z]+(?:[ /.\-][A-Za-z]+)*)", line, re.I)
        if delivery_location and not re.search(r"\d", line):
            location = delivery_location.group(1).strip().title()
            continue
        if re.search(r"delivery|futures|basis|cash price", lower) and not re.search(r"\d", line):
            header_text = line
            continue
        row, rejection = _parse_generic_row(
            line, company=company, commodity=commodity, location=location,
            source=source, fx_rate=fx_rate, header_text=header_text,
        )
        if row is not None:
            valid.append(row)
        elif rejection is not None:
            rejected.append(rejection)
    return valid, rejected


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def parse_email_bid_text(
    sender: str = "",
    subject: str = "",
    body_text: str = "",
    *,
    fx_rate: float | None = None,
) -> EmailBidParseResult:
    """Parse a plain-text (or HTML) email body into validated bid rows.

    ``sender`` may be a name or an email address; ``subject`` helps
    identify the sender company (e.g. MacEwen "Morning Report").  Only
    complete rows land in ``valid_rows``; everything else that looked like
    a bid is in ``rejected_rows`` with a reason.
    """
    company = detect_sender_company(sender, subject, body_text)
    lines = _html_to_lines(body_text)
    if company == "Bunge":
        valid, rejected = _parse_bunge_lines(lines, fx_rate=fx_rate)
    elif company == "MacEwen":
        valid, rejected = _parse_macewen_lines(lines, fx_rate=fx_rate)
    elif company == "Andersons":
        valid, rejected = _parse_andersons_lines(lines, fx_rate=fx_rate)
    else:
        valid, rejected = _parse_generic_lines(
            lines, company=company, source="text", fx_rate=fx_rate
        )
    return EmailBidParseResult(
        company=company, sender=sender, subject=subject,
        valid_rows=valid, rejected_rows=rejected,
    )


def parse_ocr_bid_rows(
    ocr_text: str,
    *,
    company: str | None = None,
    fx_rate: float | None = None,
) -> EmailBidParseResult:
    """Parse OCR text from an inline bid-table image into validated rows.

    ``company`` may name the sender (BroadGrain, Richardson, P&H); when
    omitted it is guessed from the text.  Rows whose digits OCR may have
    misread are returned with ``confidence`` 0.5 and a note naming the
    suspect token -- they are flagged, never silently corrected.
    """
    text = str(ocr_text or "")
    resolved_company = company or detect_sender_company("", "", text)
    if resolved_company == "Unknown":
        resolved_company = company or "Unknown (OCR)"
    lines = _html_to_lines(text)
    valid, rejected = _parse_generic_lines(
        lines, company=resolved_company, source="ocr", fx_rate=fx_rate
    )
    return EmailBidParseResult(
        company=resolved_company, valid_rows=valid, rejected_rows=rejected
    )


def ocr_image_to_text(
    image_path: str | Path,
    *,
    psm: int = 6,
    enhance: bool = True,
) -> str:
    """OCR one bid-table image file to text (optional dependency).

    Requires Pillow and pytesseract plus a Tesseract installation.  Both
    are optional: when they are unavailable this raises ``RuntimeError``
    with a clear message instead of failing at import time, so the pure
    parsers above always work without Tesseract installed.
    """
    try:
        from PIL import Image, ImageEnhance, ImageOps
        import pytesseract
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "OCR requires Pillow and pytesseract plus a Tesseract "
            "installation; neither is available in this environment"
        ) from exc
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"OCR image not found: {path}")
    image = Image.open(path)
    if enhance:
        image = ImageOps.grayscale(image)
        image = image.resize((image.width * 2, image.height * 2))
        image = ImageEnhance.Contrast(image).enhance(2)
    return pytesseract.image_to_string(image, config=f"--psm {psm}")
