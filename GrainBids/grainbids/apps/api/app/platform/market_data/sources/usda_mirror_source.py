"""USDA Cash Bid Report mirror collector (James Valley Grain / FS Grain).

Sources (verified 2026-11-19, one polite GET each, HTTP 200):
  https://jamesvalleygrain.com/pages/usdacash.php
  https://www.fsgrain.com/pages/usdacash.php
Both pages mirror the same USDA AMS Daily Cash Bids report, same
report id on the same day (7730 = Nov 18, 2026 on both). Plain static
HTML — no browser needed.

Page structure (verified 2026-11-19):
  <form action="/pages/usdacash.php" method="GET">
    <label>USDA Cash Bid Report for</label>
    <select name="id"> <option value="7730" selected>Nov 18, 2026</option> ...
      (archive back to Nov 05, 2026 on the page fetched; ids are
      sequential, one per USDA report day)
  <table class="table table-condensed">  (227 rows on the page fetched)
    header: Commodity | Type | Low Price | High Price |
            Price Chg. (cents) | Basis (cents) | Bid Chg. (cents)
    section row: one <td colspan="7">, e.g. "Gulf Coast Ports - LA",
      "Pacific Ports" (29 sections on the page fetched)
    data row: 7 <td>s, e.g.
      Soybeans | Export | +13.28 | +13.28 | +0.07 | +110.00 F | UNCH
    Note: on the page fetched, the first 12 data rows precede the
    first section row, so they carry ``region=None`` rather than an
    invented region label.

Units — read carefully, the page is internally inconsistent:
  * The page footnote says "All prices are cents/bushel", but the
    printed cash values are dollar-scale for most rows (+5.36 corn,
    +13.28 soybeans, +8.59 wheat — and cash ≈ futures + basis/100,
    e.g. wheat +230.00 Z basis), while one White Oats export row
    prints cents-scale (+260.00) and another White Oats row prints
    dollar-scale (+4.36). This matches the USDA AMS convention of
    quoting some bids in cents/bushel and others in $/bushel, varying
    by bid line.
    So ``unit`` is inferred per row from the printed magnitude: a low
    price >= 100 is "cents/bu" (no grain trades at $100+/bu), anything
    smaller is "$/bu" (a few cents/bu is not a real cash price).
    That is recorded here as an inference, not a page fact, and the
    raw low/high numbers are always kept alongside so nothing is lost
    if the convention is wrong. The page footnote also says soybean
    oil / corn oil print in cents/lb and soybean meal in $/ton; no
    such rows were on the page fetched, so no commodity-specific rule
    for them is coded — if they ever appear, this inference must be
    revisited for those commodities.
  * Basis is printed in cents with a futures-month code letter, e.g.
    "+110.00 F" or a range "+220.00 Z to +265.00 Z". ``basis_raw``
    keeps the printed string; ``basis`` is the parsed low end in
    $/bu (cents / 100) so the normalizer can read it, and
    ``basis_cents`` / ``basis_high_cents`` hold the parsed low/high
    ends in cents (None when the cell is blank or "UNCH"). The month
    code + the report date also yield ``delivery_month`` ("Dec 2026")
    and ``futures_month`` ("Dec 26") — the next contract of that
    month on or after the report month (see
    ``_contract_window_for_basis_month``).
  * A data row prints a low–high range across the bids in that
    region. ``cash_price`` is the low end of that range; ``low_price``
    and ``high_price`` are both returned so the range is visible.

Rows never contain invented values: an unparseable cell becomes None,
and a row with no parseable price or basis at all is skipped.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

JAMES_VALLEY_URL = "https://jamesvalleygrain.com/pages/usdacash.php"
FS_GRAIN_URL = "https://www.fsgrain.com/pages/usdacash.php"
CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

# Host -> company name for the two known mirrors. Any other host falls
# back to the page <title> prefix ("<Company> - USDA Daily Cash Bids").
_COMPANY_BY_HOST = {
    "jamesvalleygrain.com": "James Valley Grain",
    "www.fsgrain.com": "FS Grain",
    "fsgrain.com": "FS Grain",
}

# The mirrored report is the national USDA AMS Daily Cash Bids report;
# the per-row "region" carries the geography, not the mirror host.
LOCATION = "United States"
CURRENCY = "USD"

# Raw commodity label -> canonical name.
COMMODITY_MAP = {
    "white oats": "Oats",
    "corn": "Corn",
    "soybeans": "Soybeans",
    "wheat": "Wheat",
}

# Per-row magnitude inference for the cash-price unit (see module
# docstring): >= 100 prints cents-scale, anything smaller $/bu-scale.
_CENTS_SCALE_THRESHOLD = 100.0


def _unit_for(low_price: float | None, high_price: float | None) -> str:
    value = low_price if low_price is not None else high_price
    if value is not None and value >= _CENTS_SCALE_THRESHOLD:
        return "cents/bu"
    return "$/bu"

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_BASIS_RE = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*([FGHJKMNQUVXZ])?", re.IGNORECASE)


def _money(text: str | None) -> float | None:
    """Parse a printed price like '+13.28' / '260.00' to float.

    'UNCH' / blank / '-' means no value, not zero.
    """
    if not text:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    if cleaned in ("", "-", "—", "--", "UNCH"):
        return None
    match = _NUM_RE.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_basis(text: str | None) -> tuple[float | None, float | None, str | None]:
    """Parse a basis cell like '+110.00 F' or '+220.00 Z to +265.00 Z'.

    Returns (low_cents, high_cents, month_code). 'UNCH' / blank -> all
    None. A range splits on ' to '; a single value has low == high.
    """
    if not text:
        return None, None, None
    cleaned = text.strip()
    if cleaned in ("", "-", "—", "--", "UNCH"):
        return None, None, None
    parts = [part.strip() for part in re.split(r"\s+to\s+", cleaned, flags=re.IGNORECASE)]
    values: list[float] = []
    month: str | None = None
    for part in parts:
        match = _BASIS_RE.search(part)
        if not match:
            continue
        try:
            values.append(float(match.group(1)))
        except ValueError:
            continue
        if match.group(2):
            month = match.group(2).upper()
    if not values:
        return None, None, None
    return values[0], values[-1], month


# Futures month codes (CBOT): F Jan, G Feb, H Mar, J Apr, K May, M Jun,
# N Jul, Q Aug, U Sep, V Oct, X Nov, Z Dec.
_MONTH_CODE_TO_NUMBER = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}
_MONTH_NUMBER_TO_ABBR = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}
_MONTH_NUMBER_TO_NAME = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def _contract_window_for_basis_month(
    month_code: str | None, report_date: str | None
) -> tuple[str | None, str | None]:
    """Resolve a basis month code + report date to a delivery window.

    Returns (delivery_month, futures_month), e.g. ("Dec 2026", "Dec 26")
    for code "Z" on a November 2026 report, or (None, None) when the
    code is unknown or the report date is unparseable — never guessed.

    The code names the next contract of that month on or after the
    report month: a Z basis on a November report is the December
    contract of the same year; an F basis on the same report is the
    January contract of the next year. The report date comes from the
    page's own archive <select> ("Nov 18, 2026"), never from today.

    Why this exists: until 2026-11-28 these rows carried no delivery
    or futures month at all, so the normalizer dropped all 49 FS Grain
    rows in the first scheduled poll (missing_delivery_window /
    missing_futures_month / missing_basis), even though the month code
    and the report date together name the contract exactly.
    """
    if not month_code or not report_date:
        return None, None
    month_number = _MONTH_CODE_TO_NUMBER.get(month_code.strip().upper())
    if month_number is None:
        return None, None
    try:
        from datetime import datetime as _datetime

        report = _datetime.strptime(report_date.strip(), "%b %d, %Y")
    except (ValueError, TypeError):
        return None, None
    year = report.year if month_number >= report.month else report.year + 1
    delivery_month = f"{_MONTH_NUMBER_TO_NAME[month_number]} {year}"
    futures_month = f"{_MONTH_NUMBER_TO_ABBR[month_number]} {str(year)[-2:]}"
    return delivery_month, futures_month


def _company_for(url: str | None, soup: BeautifulSoup) -> str:
    if url:
        host = (urlparse(url).netloc or "").lower()
        if host in _COMPANY_BY_HOST:
            return _COMPANY_BY_HOST[host]
    if soup.title:
        title = soup.title.get_text(" ", strip=True)
        if " - USDA Daily Cash Bids" in title:
            return title.split(" - USDA Daily Cash Bids")[0].strip()
    return "Unknown USDA mirror"


def parse_usda_mirror_html(html: str, *, url: str | None = None) -> dict[str, Any]:
    """Parse a USDA Cash Bid Report mirror page into normalized bid rows.

    Returns {"company", "location", "rows", "status", "notes"} plus
    "report_id", "report_date" and "history" (the archive <select>:
    [{"id", "date"}]) when the page carries them. ``status`` is "ok"
    (rows found), "empty" (table present but no parseable rows) or
    "unsupported" (no cash-bid table found). Rows never contain
    invented values: unparseable cells become None.
    """
    soup = BeautifulSoup(html, "lxml")
    company = _company_for(url, soup)

    table = soup.find("table", class_="table-condensed")
    if table is None:
        return {
            "company": company,
            "location": LOCATION,
            "rows": [],
            "status": "unsupported",
            "notes": ["cash-bid table (.table-condensed) not found in page HTML"],
            "report_id": None,
            "report_date": None,
            "history": [],
        }

    notes: list[str] = []
    history: list[dict[str, str]] = []
    report_id: str | None = None
    report_date: str | None = None
    select = soup.find("select", {"name": "id"})
    if select is not None:
        for option in select.find_all("option"):
            value = (option.get("value") or "").strip()
            label = option.get_text(" ", strip=True)
            if not value or not label:
                continue
            history.append({"id": value, "date": label})
            if option.has_attr("selected"):
                report_id, report_date = value, label
        if history and report_id is None:
            report_id, report_date = history[0]["id"], history[0]["date"]
    if report_date:
        notes.append(f"USDA Cash Bid Report for {report_date} (id {report_id})")
    if history:
        notes.append(f"archive on page: {len(history)} reports, ids {history[-1]['id']}–{history[0]['id']}")
    notes.append(
        "Unit inference from printed magnitudes (see module docstring): "
        "low price >= 100 is cents/bu, otherwise $/bu; basis in cents "
        "with futures-month code."
    )

    rows: list[dict[str, Any]] = []
    region: str | None = None
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 1:
            # Section row: single <td colspan="7"> with the region name.
            label = cells[0].get_text(" ", strip=True)
            if label:
                region = label
            continue
        if len(cells) != 7:
            continue  # header row (<th>) or an unexpected shape
        raw_commodity = cells[0].get_text(" ", strip=True)
        commodity = COMMODITY_MAP.get(raw_commodity.lower(), raw_commodity or "Unknown")
        bid_type = cells[1].get_text(" ", strip=True)
        low_price = _money(cells[2].get_text(" ", strip=True))
        high_price = _money(cells[3].get_text(" ", strip=True))
        basis_raw = cells[5].get_text(" ", strip=True)
        basis_cents, basis_high_cents, basis_month = _parse_basis(basis_raw)
        if low_price is None and high_price is None and basis_cents is None:
            continue
        unit = _unit_for(low_price, high_price)
        # "basis" is the numeric $/bu value the normalizer reads
        # (low end of the printed range, cents -> dollars); the
        # printed string is kept verbatim in "basis_raw". A range's
        # high end stays in "basis_high_cents". Delivery / futures
        # months come from the basis month code + report date (see
        # _contract_window_for_basis_month); rows without a month
        # code keep None there rather than an invented month.
        delivery_month, futures_month = _contract_window_for_basis_month(basis_month, report_date)
        rows.append(
            {
                "company": company,
                "location": LOCATION,
                "region": region,
                "commodity": commodity,
                "bid_type": bid_type or None,
                "delivery_month": delivery_month,
                "futures_month": futures_month,
                "cash_price": low_price,
                "low_price": low_price,
                "high_price": high_price,
                "basis": (basis_cents / 100.0) if basis_cents is not None else None,
                "basis_raw": basis_raw or None,
                "basis_cents": basis_cents,
                "basis_high_cents": basis_high_cents,
                "basis_month": basis_month,
                "currency": CURRENCY,
                "unit": unit,
                "report_id": report_id,
                "report_date": report_date,
                "note": "",
            }
        )

    if not rows:
        return {
            "company": company,
            "location": LOCATION,
            "rows": [],
            "status": "empty",
            "notes": notes + ["table found but no bid rows parsed"],
            "report_id": report_id,
            "report_date": report_date,
            "history": history,
        }
    return {
        "company": company,
        "location": LOCATION,
        "rows": rows,
        "status": "ok",
        "notes": notes,
        "report_id": report_id,
        "report_date": report_date,
        "history": history,
    }


def fetch_usda_mirror_html(url: str, timeout: int = 30) -> str:
    """One polite GET of a USDA-mirror page. Contact User-Agent."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_usda_mirror(url: str = JAMES_VALLEY_URL) -> dict[str, Any]:
    """Fetch and parse one USDA-mirror page in one call."""
    return parse_usda_mirror_html(fetch_usda_mirror_html(url), url=url)


def fetch_usda_mirror_fs_grain() -> dict[str, Any]:
    """Fetch and parse the FS Grain mirror (same report, second host)."""
    return fetch_usda_mirror(FS_GRAIN_URL)


def usda_mirror_history_url(url: str, report_id: str | int) -> str:
    """Archive URL for one report id (the page's <select name="id"> form is a GET)."""
    base = url.split("?")[0]
    return f"{base}?id={report_id}"
