"""Mapleview Grain (London, Ontario) cash-bid collector — STUB.

Source: https://www.mapleviewgrain.ca/ links its bids out to
https://mapleview.graindiscovery.com/ ("View current bids").

Status (verified 2026-11-19, one polite GET each):
  * The Mapleview homepage's "#bids" section is marketing copy only —
    no prices in static HTML.
  * https://mapleview.graindiscovery.com/ is a Next.js single-page
    app: the static HTML is just the app shell ("Grain Discovery",
    no <table>, no bid content, no prices). Bids render client-side.

So there is currently NO plain-HTML structure to parse reliably, and
this module deliberately does not guess one. ``parse_mapleview_html``
returns an explicit "unsupported" result with the reason, and the
fetch helpers still do one polite GET each so a future Playwright or
Grain Discovery API pass has a place to land.

Next step (later cycle, not this one): render the Grain Discovery
page in Playwright and inspect the loaded bid table / network calls,
or ask Mapleview / Grain Discovery about a public feed. Do not scrape
the app's private API endpoints without confirming they are public.
"""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

MAPLEVIEW_URL = "https://www.mapleviewgrain.ca/"
MAPLEVIEW_BIDS_URL = "https://mapleview.graindiscovery.com/"
MAPLEVIEW_COMPANY = "Mapleview Grain"
MAPLEVIEW_LOCATION = "London"
CONTACT_USER_AGENT = "GrainHub-Research/1.0 +https://github.com/apz100/GrainHub"

UNSUPPORTED_REASON = (
    "bids live in a JS-rendered Grain Discovery app "
    "(mapleview.graindiscovery.com); no bid table in static HTML — "
    "needs a Playwright render or a public Grain Discovery feed"
)


def parse_mapleview_html(html: str) -> dict[str, Any]:
    """Inspect Mapleview / Grain Discovery HTML for a parseable bid table.

    Always returns status "unsupported" with an explicit reason until
    a parseable structure is confirmed: the homepage has no prices
    and the Grain Discovery page is a JS app shell. Returns no rows
    and never invents values.
    """
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    bid_tables = [
        t
        for t in tables
        if "cash" in t.get_text(" ", strip=True).lower()
    ]
    notes = [UNSUPPORTED_REASON]
    if bid_tables:
        # A table with cash-bid text appeared — flag it for a human to
        # confirm rather than silently parsing an unknown structure.
        notes.append(
            f"unexpected: {len(bid_tables)} table(s) mention cash bids; "
            "structure not yet verified — parser left unsupported"
        )
    return {
        "company": MAPLEVIEW_COMPANY,
        "location": MAPLEVIEW_LOCATION,
        "rows": [],
        "status": "unsupported",
        "notes": notes,
    }


def fetch_mapleview_html(url: str = MAPLEVIEW_BIDS_URL, timeout: int = 30) -> str:
    """One polite GET of the Mapleview bids page."""
    response = requests.get(
        url, headers={"User-Agent": CONTACT_USER_AGENT}, timeout=timeout
    )
    response.raise_for_status()
    return response.text


def fetch_mapleview(url: str = MAPLEVIEW_BIDS_URL) -> dict[str, Any]:
    """Fetch and (not yet) parse Mapleview bids."""
    return parse_mapleview_html(fetch_mapleview_html(url))
