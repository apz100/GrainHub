"""Collwest Grain (Collingwood, Ontario) cash-bid collector.

Source: https://www.collwestgrain.com/ (homepage cash-bid widget).
Plain HTML — no browser needed.

Page structure (verified 2026-11-19, one polite GET):
  <div class="cbmod">
    <div class="cashBidLocation"><h2>Collwest</h2>
      <p class="fcControlsSectionHeader">Cash bids for <date></p>
    <div class="cbCommodity"><h3>Corn</h3>
      <ul class="... fcControlsSubHdr"> Delivery | Bid | Basis | Futures | Change
      <ul class="... fcControls1">  (one per delivery)
        <li class="c1"><span class="cashBidsColumnOne">2026 Crop</span>
        <li class="c2"> Bid ($/bu)
        <li class="c3"> Basis
        <li class="c4"> Futures
        <li class="c5"> Change

Commodities seen: Corn, Soybeans, Soft Red Wheat, Hard Red Winter Wheat
(Protein in), Hard Red Spring Wheat (Protein In), Canola, Barley, Oats.
Deliveries are crop-year labels ("2026 Crop", "2027 Crop", "2028 Crop").

Currency: CAD — Collwest is an Ontario elevator and the widget's bid
values track CAD/bu (basis + CBOT futures ≈ bid). The page does not
state a currency explicitly; this is recorded as an inference, not a
page fact. Basis is in $/bu (same check: bid − futures ≈ basis).

Rows carry ``cash_price`` (Bid), ``basis``, ``futures_price`` and
``delivery_month`` (the crop-year label). ``cash_price_mt`` is not
published by this widget, so it is None.
"""

from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup

COLLWEST_URL = "https://www.collwestgrain.com/"
COLLWEST_COMPANY = "Collwest Grain"
COLLWEST_LOCATION = "Collingwood"
CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

# Raw widget commodity label -> canonical commodity name.
COMMODITY_MAP = {
    "corn": "Corn",
    "soybeans": "Soybeans",
    "soft red wheat": "Wheat — SRW",
    "hard red winter wheat (protein in)": "Wheat — HRW",
    "hard red spring wheat (protein in)": "Wheat — HRS",
    "canola": "Canola",
    "barley": "Barley",
    "oats": "Oats",
}

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _money(text: str | None) -> float | None:
    """Parse a plain number like '5.58' / '+1.25' / '4.3325' to float."""
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


def parse_collwest_html(html: str) -> dict[str, Any]:
    """Parse Collwest homepage HTML into normalized bid rows.

    Returns {"company", "location", "rows", "status", "notes"} where
    ``status`` is "ok" (rows found), "empty" (widget present but no
    parseable rows) or "unsupported" (widget structure not found).
    Rows never contain invented values: unparseable cells become None.
    """
    soup = BeautifulSoup(html, "lxml")
    widget = soup.find("div", class_="cbmod")
    if widget is None:
        return {
            "company": COLLWEST_COMPANY,
            "location": COLLWEST_LOCATION,
            "rows": [],
            "status": "unsupported",
            "notes": ["cash-bid widget (.cbmod) not found in page HTML"],
        }

    header = widget.find("p", class_="fcControlsSectionHeader")
    as_of = header.get_text(" ", strip=True) if header else ""
    rows: list[dict[str, Any]] = []
    notes: list[str] = []
    if as_of:
        notes.append(f"widget header: {as_of}")

    for section in widget.find_all("div", class_="cbCommodity"):
        heading = section.find("h3")
        raw_name = heading.get_text(" ", strip=True) if heading else ""
        commodity = COMMODITY_MAP.get(raw_name.lower(), raw_name or "Unknown")
        for row_ul in section.find_all("ul"):
            classes = " ".join(row_ul.get("class") or [])
            if "fcControlsSubHdr" in classes:
                continue  # header row
            if "fcControls1" not in classes and "fcControls2" not in classes:
                continue
            cells = row_ul.find_all("li")
            if len(cells) < 5:
                continue
            delivery_el = cells[0].find("span", class_="cashBidsColumnOne")
            delivery = (
                delivery_el.get_text(" ", strip=True)
                if delivery_el
                else cells[0].get_text(" ", strip=True)
            )
            bid = _money(cells[1].get_text(" ", strip=True))
            basis = _money(cells[2].get_text(" ", strip=True))
            futures = _money(cells[3].get_text(" ", strip=True))
            if bid is None and basis is None and futures is None:
                continue
            rows.append(
                {
                    "company": COLLWEST_COMPANY,
                    "location": COLLWEST_LOCATION,
                    "commodity": commodity,
                    "delivery_month": delivery,
                    "cash_price": bid,
                    "cash_price_mt": None,
                    "basis": basis,
                    "futures_price": futures,
                    "currency": "CAD",
                    "unit": "$/bu",
                    "note": "",
                }
            )

    if not rows:
        return {
            "company": COLLWEST_COMPANY,
            "location": COLLWEST_LOCATION,
            "rows": [],
            "status": "empty",
            "notes": notes + ["widget found but no bid rows parsed"],
        }
    return {
        "company": COLLWEST_COMPANY,
        "location": COLLWEST_LOCATION,
        "rows": rows,
        "status": "ok",
        "notes": notes,
    }


def fetch_collwest_html(url: str = COLLWEST_URL, timeout: int = 30) -> str:
    """One polite GET of the Collwest homepage. Contact User-Agent."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_collwest(url: str = COLLWEST_URL) -> dict[str, Any]:
    """Fetch and parse Collwest bids in one call."""
    return parse_collwest_html(fetch_collwest_html(url))
