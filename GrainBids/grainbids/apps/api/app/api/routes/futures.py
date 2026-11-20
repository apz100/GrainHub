"""Futures strip + ICE canola desk (read-only).

GET /api/futures/strip   — CBOT corn/soybeans/wheat, KC HRW, MGEX HRS, oats
GET /api/futures/canola  — ICE canola desk

No licensed or delayed market-data feed is wired yet, and the
``app.services.market_data`` service stores cash-bid frames, not
futures rows — there is no futures table to read from. These endpoints
therefore return the contract structure (exchange, symbol, contract
months) with every price/change/settle explicitly ``null`` and
``available: false``, plus a note saying the feed is not wired.
**No futures price is ever invented.** Once a licensed/delayed feed
(Barchart OnDemand, DTN, CME DataMine, or a broker feed) is wired,
fill the contract values from that feed and flip ``available`` to
``true`` — do not fill them from an unofficial scraper.

Delay reference (research notes, 2026-11-19): CME/Barchart/TradingView
delayed pages are 10–15 min delayed; that is the delay label the feed
will carry once wired.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/futures", tags=["futures"])

FEED_NOT_WIRED_NOTE = (
    "No licensed/delayed futures feed is wired yet. Contract months "
    "are listed so the strip layout is ready, but every price, change "
    "and settle is null — no price is shown until a licensed feed "
    "(Barchart OnDemand, DTN, CME DataMine or a broker feed) is "
    "connected. Delayed vendor pages (CME/Barchart/TradingView) are "
    "10-15 min delayed once a feed is wired."
)

_MONTH_CODES = {
    1: "F",
    2: "G",
    3: "H",
    4: "J",
    5: "K",
    6: "M",
    7: "N",
    8: "Q",
    9: "U",
    10: "V",
    11: "X",
    12: "Z",
}
_MONTH_NAMES = {
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

# (commodity, exchange, symbol root, contract months, unit, currency)
STRIP_COMMODITIES: tuple[tuple[str, str, str, tuple[int, ...], str, str], ...] = (
    ("Corn", "CBOT", "ZC", (3, 5, 7, 9, 12), "cents/bushel", "USD"),
    ("Soybeans", "CBOT", "ZS", (1, 3, 5, 7, 8, 9, 11), "cents/bushel", "USD"),
    ("Wheat (SRW)", "CBOT", "ZW", (3, 5, 7, 9, 12), "cents/bushel", "USD"),
    ("Wheat (HRW)", "KCBT", "KE", (3, 5, 7, 9, 12), "cents/bushel", "USD"),
    ("Wheat (HRS)", "MGEX", "MWE", (3, 5, 7, 9, 12), "cents/bushel", "USD"),
    ("Oats", "CBOT", "ZO", (3, 5, 7, 9, 12), "cents/bushel", "USD"),
)

CANOLA = ("Canola", "ICE Futures Canada", "RS", (1, 3, 5, 7, 11), "CAD/tonne", "CAD")


def next_contracts(
    symbol_root: str,
    months: tuple[int, ...],
    ref: date,
    count: int = 5,
) -> list[dict[str, Any]]:
    """Next ``count`` contract months on/after ``ref`` (structure only)."""
    contracts: list[dict[str, Any]] = []
    year, month = ref.year, ref.month
    while len(contracts) < count:
        if month in months:
            code = _MONTH_CODES[month]
            contracts.append(
                {
                    "symbol": f"{symbol_root}{code}{str(year)[-2:]}",
                    "contract_month": f"{_MONTH_NAMES[month]} {year}",
                    "month_code": code,
                    "year": year,
                    "price": None,
                    "change": None,
                    "settle": None,
                    "as_of": None,
                }
            )
        month += 1
        if month > 12:
            month = 1
            year += 1
    return contracts


def _commodity_block(
    commodity: str,
    exchange: str,
    symbol_root: str,
    months: tuple[int, ...],
    unit: str,
    currency: str,
    ref: date,
) -> dict[str, Any]:
    return {
        "commodity": commodity,
        "exchange": exchange,
        "symbol_root": symbol_root,
        "unit": unit,
        "currency": currency,
        "contracts": next_contracts(symbol_root, months, ref),
    }


def _feed_block() -> dict[str, Any]:
    return {
        "available": False,
        "feed_status": "not_wired",
        "source": None,
        "delay": "10-15 min delayed (once a licensed feed is wired)",
        "as_of": None,
        "note": FEED_NOT_WIRED_NOTE,
    }


@router.get("/strip")
def futures_strip():
    ref = date.today()
    return {
        **_feed_block(),
        "commodities": [
            _commodity_block(commodity, exchange, root, months, unit, currency, ref)
            for commodity, exchange, root, months, unit, currency in STRIP_COMMODITIES
        ],
    }


@router.get("/canola")
def canola_desk():
    ref = date.today()
    commodity, exchange, root, months, unit, currency = CANOLA
    return {
        **_feed_block(),
        "desk": "ICE Canola Desk",
        **_commodity_block(commodity, exchange, root, months, unit, currency, ref),
        "note": (
            FEED_NOT_WIRED_NOTE
            + " ICE canola has the thinnest free coverage of any "
            "contract here (absent from Twelve Data and Alpha Vantage; "
            "free delayed pages only on Barchart/TradingView/e-ADM), "
            "so a licensed feed is needed first for this desk."
        ),
    }
