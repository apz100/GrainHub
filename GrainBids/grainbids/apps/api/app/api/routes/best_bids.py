"""Public best-bid page API (Cycle 2).

``GET /api/best-bids`` is public: no auth, no ``X-Org-Id`` header,
no user data. It returns the top cash bids by company from real
``NormalizedPrice`` rows already in the database, grouped by
commodity, delivery month and currency. Elevator cash bids are published
publicly by the elevators themselves, so no per-organisation scoping
is applied here — and no watchlists, alerts, accounts, or any other
user data appear in the response.

One row per company (its best cash price for that commodity +
delivery month + currency), sorted by cash price descending within
its currency, capped by ``limit`` per currency (default 30). Empty
states return empty groups, never invented bids.

Currency (decision 2026-11-20): each bid carries its stored source
currency (migration 0022); bids whose source records none report
``currency: null`` with ``currency_unknown: true``. Bids are grouped
by currency by default and never compared across currencies.
Conversion happens only when the caller explicitly passes
``convert_to=CAD|USD``; converted bids are labelled with the Bank of
Canada daily noon rate and its as-of date (see ``app.services.fx_rates``),
and bids with an unknown currency are never converted.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, defer

from app.api.routes.normalized_prices import (
    _canonical_month_label,
    _display_company_name_for_row,
    _load_company_name_map,
    _load_location_company_map,
    _to_basis_float,
    _to_float,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.normalized_price import NormalizedPrice
from app.models.price_snapshot import PriceSnapshot
from app.services import fx_rates
from app.services.market_canonicalization import canonical_commodity_name, normalize_text

router = APIRouter(prefix="/api/best-bids", tags=["best-bids"])

_BEST_BIDS_FETCH_LIMIT = 300

NOTE = (
    "Top cash bids by company from real normalized prices already in "
    "the database. Each bid carries its stored source currency; bids "
    "whose source records no currency show currency null with "
    "currency_unknown true, and no currency is assumed for them. "
    "Bids are grouped by currency and ranked only within their own "
    "currency; the limit applies per currency. No conversion is "
    "applied unless convert_to is passed. "
    "Unit is \"bu\" for cash_price_bu (cash_price_mt is also shown, unit \"mt\")."
)

CONVERTED_NOTE = (
    "Converted figures use the Bank of Canada daily noon rate shown "
    "in fx (with its as-of date); each converted bid is labelled "
    "converted true with its original currency and original cash "
    "price. Bids with an unknown currency are never converted."
)


def _delivery_label(price: NormalizedPrice) -> str:
    return _canonical_month_label(
        normalize_text(price.delivery_label)
        or normalize_text(price.delivery_end)
        or normalize_text(price.futures_month)
    ) or "Unspecified"


@router.get("")
def best_bids(
    commodity: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    convert_to: str | None = Query(
        None,
        description=(
            "Explicit FX toggle: convert every bid with a known currency "
            "to this ISO currency (CAD or USD) using the Bank of Canada "
            "daily noon rate, labelled in the response. Omitted (the "
            "default): no conversion, bids grouped by currency."
        ),
    ),
    db: Session = Depends(get_db),
):
    target_currency: str | None = None
    # isinstance guard: direct (non-HTTP) callers of this function —
    # the Phase A robustness tests — receive the Query() default
    # object itself when they omit convert_to; that means "not
    # requested", exactly like an absent query parameter.
    if isinstance(convert_to, str) and convert_to.strip():
        target_currency = convert_to.strip().upper()
        if target_currency not in {"CAD", "USD"}:
            raise HTTPException(
                status_code=400,
                detail="convert_to must be CAD or USD (the only currencies stored prices use).",
            )
    invalid = {(label or "").strip().casefold() for label in settings.invalid_commodity_labels_set}
    wanted = (commodity or "").strip().casefold() or None

    query = (
        select(NormalizedPrice, PriceSnapshot)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .where(NormalizedPrice.cash_price_bu.is_not(None))
        .order_by(desc(NormalizedPrice.cash_price_bu), desc(PriceSnapshot.captured_at))
        # Phase A audit (2026-11-20): only snapshot.captured_at is
        # read; defer the unbounded raw_payload_json.
        .options(defer(PriceSnapshot.raw_payload_json))
    )
    rows = db.execute(query.limit(_BEST_BIDS_FETCH_LIMIT)).all()

    location_ids = {price.location_id for price, _s in rows if price.location_id is not None}
    company_ids = {price.company_id for price, _s in rows if price.company_id is not None}
    location_company_map = _load_location_company_map(db, location_ids=location_ids)
    company_ids.update(location_company_map.values())
    company_name_map = _load_company_name_map(db, company_ids=company_ids)

    # Sort in Python as well as SQL so the per-company best pick does not
    # depend on the database returning rows in order.
    rows = sorted(
        rows,
        key=lambda pair: (
            -(_to_float(pair[0].cash_price_bu) if _to_float(pair[0].cash_price_bu) is not None else float("-inf")),
            -(pair[1].captured_at.timestamp() if pair[1] is not None and pair[1].captured_at is not None else 0.0),
        ),
    )

    # Best row per company per (commodity, delivery month, currency):
    # rows arrive cash-price descending, so the first row seen for a
    # key wins. Currency is part of the key so a company's CAD best
    # and USD best are separate bids, never merged or compared.
    best_by_key: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for price, snapshot in rows:
        name = (price.commodity_name or "").strip()
        if not name or name.casefold() in invalid:
            continue
        if wanted and wanted not in name.casefold():
            continue
        company = _display_company_name_for_row(
            price,
            company_name_map=company_name_map,
            location_company_map=location_company_map,
        ) or (price.source_name or "Unknown")
        commodity_label = canonical_commodity_name(name) or name
        delivery = _delivery_label(price)
        currency = (price.currency or "").strip().upper() or None
        key = (commodity_label.casefold(), delivery.casefold(), company.casefold(), currency or "")
        if key in best_by_key:
            continue
        captured = snapshot.captured_at if snapshot is not None else None
        if captured is not None and captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
        best_by_key[key] = {
            "company_name": company,
            "location": price.location,
            "location_id": str(price.location_id) if price.location_id else None,
            "commodity_name": commodity_label,
            "delivery_month": delivery,
            "cash_price_bu": _to_float(price.cash_price_bu),
            "cash_price_mt": _to_float(price.cash_price_mt),
            "basis": _to_basis_float(price.basis),
            "futures_month": _canonical_month_label(normalize_text(price.futures_month)),
            "futures_price": _to_float(price.futures_price),
            "currency": currency,
            "currency_unknown": currency is None,
            "converted": False,
            "unit": "bu",
            "quote_date": captured.date().isoformat() if captured else None,
            "captured_at": captured.isoformat() if captured else None,
            "source": price.source_name,
        }

    bids = list(best_by_key.values())

    fx_payload: dict[str, object] | None = None
    if target_currency is not None:
        fx_payload = _convert_bids(bids, target_currency=target_currency)

    # Group by currency: known currencies in ISO order, unknown last;
    # cash price descending within a currency. The limit caps each
    # currency block, so one currency can never crowd out another.
    def _bid_order(bid: dict[str, object]) -> tuple[bool, str, float, str]:
        cash = bid["cash_price_bu"]
        return (
            bid["currency"] is None,
            str(bid["currency"] or ""),
            -(cash if isinstance(cash, (int, float)) else float("-inf")),
            str(bid["company_name"] or ""),
        )

    bids.sort(key=_bid_order)
    per_currency_count: dict[str, int] = {}
    top: list[dict[str, object]] = []
    for bid in bids:
        block = str(bid["currency"] or "")
        if per_currency_count.get(block, 0) >= limit:
            continue
        per_currency_count[block] = per_currency_count.get(block, 0) + 1
        top.append(bid)

    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for bid in top:
        grouped[(str(bid["commodity_name"]), str(bid["delivery_month"]), str(bid["currency"] or ""))].append(bid)
    groups = [
        {
            "commodity": commodity_label,
            "delivery_month": delivery,
            "currency": currency or None,
            "currency_unknown": not currency,
            "bids": bids_in_group,
        }
        for (commodity_label, delivery, currency), bids_in_group in sorted(
            grouped.items(),
            key=lambda item: (item[0][0], item[0][1], item[0][2] == "", item[0][2]),
        )
    ]
    note = NOTE if target_currency is None else f"{NOTE} {CONVERTED_NOTE}"
    return {
        "commodity": commodity,
        "limit": limit,
        "convert_to": target_currency,
        "fx": fx_payload,
        "bid_count": len(top),
        "groups": groups,
        "note": note,
    }


def _convert_bids(
    bids: list[dict[str, object]], *, target_currency: str
) -> dict[str, object] | None:
    """Convert every convertible bid to ``target_currency``, in place.

    Only bids whose stored currency is known and differs from the
    target are converted, using the Bank of Canada daily noon rate;
    each converted bid keeps its original currency and original cash
    price alongside. Bids already in the target currency and bids
    with an unknown currency are left exactly as stored. Returns the
    FX label for the response, or None when nothing needed
    converting. Raises 502 when a conversion is needed but no rate
    is available — an unlabelled fallback would be a silent
    conversion at an unknown rate.
    """
    convertible = [
        bid
        for bid in bids
        if bid["currency"] is not None and bid["currency"] != target_currency
    ]
    if not convertible:
        return None
    rate = fx_rates.get_usd_cad_rate()
    if rate is None:
        raise HTTPException(
            status_code=502,
            detail=(
                "convert_to was requested but the Bank of Canada daily "
                "noon rate could not be fetched; no conversion was applied."
            ),
        )
    for bid in convertible:
        original_currency = str(bid["currency"])
        converted_bu = fx_rates.convert_amount(
            bid["cash_price_bu"],
            from_currency=original_currency,
            to_currency=target_currency,
            fx_rate=rate,
        )
        if converted_bu is None:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"A bid in {original_currency} could not be converted "
                    f"to {target_currency}; no conversion was applied."
                ),
            )
        bid["original_currency"] = original_currency
        bid["original_cash_price_bu"] = bid["cash_price_bu"]
        bid["cash_price_bu"] = float(converted_bu)
        for field in ("cash_price_mt", "basis", "futures_price"):
            converted_value = fx_rates.convert_amount(
                bid[field],
                from_currency=original_currency,
                to_currency=target_currency,
                fx_rate=rate,
            )
            bid[field] = float(converted_value) if converted_value is not None else None
        bid["currency"] = target_currency
        bid["currency_unknown"] = False
        bid["converted"] = True
    return rate.to_dict()
