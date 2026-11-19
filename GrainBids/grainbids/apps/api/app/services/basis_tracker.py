"""Basis tracker service (Cycle 2).

Computes basis = cash price minus futures price using only data already
stored on ``NormalizedPrice`` rows (``cash_price_bu``, ``futures_price``,
``futures_month``). Both stored prices are per-bushel values, so the
computed basis is per bushel too.

Rules, by design:

* If the cash price or the futures price is missing (or non-finite), the
  basis is ``None`` and an explicit ``missing_reason`` is returned. A basis
  is never invented or estimated.
* ``NormalizedPrice`` rows carry no currency or unit column (the commodity
  table defaults to ``bu``). Responses therefore report ``currency=None``
  with a data-quality note saying so, and ``unit="bu"``. If a caller
  supplies per-row currency/unit metadata that disagrees with the expected
  currency/unit, the row is refused with a ``unit_mismatch`` /
  ``currency_mismatch`` reason instead of being computed across mismatched
  units.
* The stored ``basis`` column is only a cross-check: it is compared with
  the recomputed value (applying the same legacy cents-per-bushel
  normalisation the preview route uses) and any disagreement is flagged in
  ``data_quality``. The recomputed value is what is reported.

Testville is the pilot location: it is resolved by looking up a stored
``Location`` whose canonical name is "Testville" / "Test Elevator Co."
(see :func:`find_default_origin`). No coordinates are hardcoded anywhere
here -- if no such location (or no coordinates for it) is stored, ranking
falls back to all locations and says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import uuid

from app.api.routes.market_search import haversine_km
from app.api.routes.normalized_prices import _month_sort_key_value
from app.models.location import Location
from app.models.normalized_price import NormalizedPrice
from app.models.price_snapshot import PriceSnapshot
from app.services.market_canonicalization import canonical_key, normalize_text

# Canonical names that identify the Testville pilot location/company in
# stored Location rows. These are names to look up, not coordinates.
DEFAULT_LOCATION_NAMES = ("testville", "test elevator co.")

# Basis values are per bushel; the stored ``basis`` column is trusted only
# within this tolerance when cross-checked against the recomputed value.
BASIS_MATCH_TOLERANCE = 0.005

CURRENCY_NOT_STORED_NOTE = (
    "Currency is not stored on normalized price rows; cash and futures "
    "prices are per-bushel values as stored, so only compare basis values "
    "within the same currency."
)


@dataclass
class BasisComputation:
    """Result of computing the basis for one normalized price row."""

    basis: float | None = None
    cash_price_bu: float | None = None
    futures_price: float | None = None
    futures_month: str | None = None
    stored_basis: float | None = None
    basis_matches_stored: bool | None = None
    missing_reason: str | None = None
    currency: str | None = None
    unit: str = "bu"
    data_quality: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "basis": self.basis,
            "cash_price_bu": self.cash_price_bu,
            "futures_price": self.futures_price,
            "futures_month": self.futures_month,
            "stored_basis": self.stored_basis,
            "basis_matches_stored": self.basis_matches_stored,
            "missing_reason": self.missing_reason,
            "currency": self.currency,
            "unit": self.unit,
            "data_quality": self.data_quality,
        }


def compute_basis_for_row(
    row: NormalizedPrice,
    *,
    expected_unit: str = "bu",
    expected_currency: str | None = None,
    row_unit: str | None = None,
    row_currency: str | None = None,
) -> BasisComputation:
    """Compute basis = cash_price_bu - futures_price for one row.

    ``row_unit`` / ``row_currency`` are optional per-row metadata supplied
    by the caller (the model stores neither today, so they are normally
    ``None``); a stored ``unit`` / ``currency`` attribute on the row, if one
    ever exists, is picked up the same way. A mismatch is refused, never
    silently converted.
    """
    effective_unit = row_unit if row_unit is not None else getattr(row, "unit", None)
    effective_currency = (
        row_currency if row_currency is not None else getattr(row, "currency", None)
    )
    notes = [CURRENCY_NOT_STORED_NOTE] if effective_currency is None else []

    if effective_unit is not None and effective_unit != expected_unit:
        return BasisComputation(
            cash_price_bu=_to_float(row.cash_price_bu),
            futures_price=_to_float(row.futures_price),
            futures_month=normalize_text(row.futures_month),
            stored_basis=_normalize_stored_basis(row.basis),
            missing_reason="unit_mismatch",
            currency=effective_currency,
            unit=str(effective_unit),
            data_quality=(
                f"Unit mismatch: row is per {effective_unit}, expected per "
                f"{expected_unit}; basis not computed across mismatched units."
            ),
        )
    if (
        effective_currency is not None
        and expected_currency is not None
        and effective_currency != expected_currency
    ):
        return BasisComputation(
            cash_price_bu=_to_float(row.cash_price_bu),
            futures_price=_to_float(row.futures_price),
            futures_month=normalize_text(row.futures_month),
            stored_basis=_normalize_stored_basis(row.basis),
            missing_reason="currency_mismatch",
            currency=effective_currency,
            unit=str(effective_unit or expected_unit),
            data_quality=(
                f"Currency mismatch: row is {effective_currency}, expected "
                f"{expected_currency}; basis not computed across currencies."
            ),
        )

    cash = _to_decimal(row.cash_price_bu)
    futures = _to_decimal(row.futures_price)
    stored_basis = _normalize_stored_basis(row.basis)

    if cash is None and futures is None:
        return BasisComputation(
            cash_price_bu=None,
            futures_price=None,
            futures_month=normalize_text(row.futures_month),
            stored_basis=stored_basis,
            missing_reason="missing_cash_and_futures_prices",
            currency=effective_currency,
            unit=str(effective_unit or expected_unit),
            data_quality="; ".join(
                [*notes, "Cash price and futures price are both missing; basis not computed."]
            ),
        )
    if cash is None:
        return BasisComputation(
            cash_price_bu=None,
            futures_price=_to_float(row.futures_price),
            futures_month=normalize_text(row.futures_month),
            stored_basis=stored_basis,
            missing_reason="missing_cash_price",
            currency=effective_currency,
            unit=str(effective_unit or expected_unit),
            data_quality="; ".join([*notes, "Cash price is missing; basis not computed."]),
        )
    if futures is None:
        return BasisComputation(
            cash_price_bu=_to_float(row.cash_price_bu),
            futures_price=None,
            futures_month=normalize_text(row.futures_month),
            stored_basis=stored_basis,
            missing_reason="missing_futures_price",
            currency=effective_currency,
            unit=str(effective_unit or expected_unit),
            data_quality="; ".join([*notes, "Futures price is missing; basis not computed."]),
        )

    basis = float(cash - futures)
    basis = round(basis, 6)
    matches_stored: bool | None = None
    if stored_basis is not None:
        matches_stored = abs(stored_basis - basis) <= BASIS_MATCH_TOLERANCE
        if not matches_stored:
            notes.append(
                f"Stored basis ({stored_basis}) differs from recomputed "
                f"basis ({basis}); recomputed value reported."
            )
    else:
        notes.append("No stored basis on the row to cross-check against.")
    if not notes:
        notes.append("Computed from stored cash and futures prices.")
    return BasisComputation(
        basis=basis,
        cash_price_bu=float(cash),
        futures_price=float(futures),
        futures_month=normalize_text(row.futures_month),
        stored_basis=stored_basis,
        basis_matches_stored=matches_stored,
        missing_reason=None,
        currency=effective_currency,
        unit=str(effective_unit or expected_unit),
        data_quality="; ".join(notes),
    )


def quote_date_for_row(
    row: NormalizedPrice, snapshot: PriceSnapshot | None
) -> datetime | None:
    """Quote date for a row: its snapshot's captured_at, else created_at."""
    if snapshot is not None and snapshot.captured_at is not None:
        return snapshot.captured_at
    return row.created_at


def serialize_basis_row(
    row: NormalizedPrice,
    snapshot: PriceSnapshot | None = None,
    *,
    computation: BasisComputation | None = None,
) -> dict[str, object]:
    """One JSON-ready basis row, including source and data quality."""
    computed = computation if computation is not None else compute_basis_for_row(row)
    quote_date = quote_date_for_row(row, snapshot)
    return {
        "location": row.location,
        "location_id": str(row.location_id) if row.location_id else None,
        "commodity_name": row.commodity_name,
        "source": normalize_text(row.source_name),
        "currency": computed.currency,
        "unit": computed.unit,
        "quote_date": quote_date.date().isoformat() if quote_date is not None else None,
        "futures_month": computed.futures_month,
        "cash_price_bu": computed.cash_price_bu,
        "futures_price": computed.futures_price,
        "basis": computed.basis,
        "stored_basis": computed.stored_basis,
        "basis_matches_stored": computed.basis_matches_stored,
        "missing_reason": computed.missing_reason,
        "data_quality": computed.data_quality,
        "delivery_label": normalize_text(row.delivery_label),
    }


def row_delivery_month_keys(row: NormalizedPrice) -> set[int]:
    """Month sort keys (year*12+month) a row claims, via either month field."""
    keys: set[int] = set()
    for value in (row.futures_month, row.delivery_label, row.delivery_end):
        key = _month_sort_key_value(value)
        if key is not None and key < 9999 * 12:
            keys.add(key)
    return keys


def build_basis_history(
    pairs: list[tuple[NormalizedPrice, PriceSnapshot | None]],
    *,
    commodity: str | None = None,
    location_id: uuid.UUID | None = None,
    limit: int = 90,
) -> dict[str, object]:
    """Basis over time for one location + commodity, oldest quote first.

    Rows whose basis cannot be computed are kept in the series with
    ``basis=None`` and their ``missing_reason`` so gaps stay visible.
    """
    wanted_commodity = canonical_key(commodity) if commodity else None
    entries: list[dict[str, object]] = []
    missing_count = 0
    for row, snapshot in pairs:
        if wanted_commodity is not None and canonical_key(row.commodity_name) != wanted_commodity:
            continue
        if location_id is not None and row.location_id != location_id:
            continue
        computed = compute_basis_for_row(row)
        if computed.missing_reason is not None:
            missing_count += 1
        entries.append(serialize_basis_row(row, snapshot, computation=computed))

    def _sort_key(entry: dict[str, object]) -> tuple[bool, str, str, str]:
        quote_date = entry.get("quote_date")
        return (
            quote_date is None,
            str(quote_date or ""),
            str(entry.get("location") or "").casefold(),
            str(entry.get("commodity_name") or "").casefold(),
        )

    entries.sort(key=_sort_key)
    entries = entries[: max(1, limit)]
    if entries:
        quality = (
            f"Basis over time from stored normalized prices ({len(entries)} rows"
            + (f", {missing_count} without a computable basis" if missing_count else "")
            + "). "
            + CURRENCY_NOT_STORED_NOTE
        )
    else:
        quality = (
            "No normalized price rows found for this commodity/location; "
            "no basis history exists yet. " + CURRENCY_NOT_STORED_NOTE
        )
    return {
        "commodity": commodity,
        "location_id": str(location_id) if location_id else None,
        "currency": None,
        "unit": "bu",
        "row_count": len(entries),
        "missing_count": missing_count,
        "rows": entries,
        "data_quality": quality,
    }


def find_default_origin(locations: list[Location]) -> Location | None:
    """Find the stored Testville pilot location, preferring one with coords.

    Returns ``None`` when no stored location matches the pilot names at all.
    Coordinates are never invented: a match without coordinates is returned
    so the caller can report that, rather than guessing a position.
    """
    matches = [
        loc
        for loc in locations
        if canonical_key(loc.name) in DEFAULT_LOCATION_NAMES
    ]
    if not matches:
        return None
    for loc in matches:
        if loc.latitude is not None and loc.longitude is not None:
            return loc
    return matches[0]


def resolve_origin_location(
    locations: list[Location],
    *,
    location_id: uuid.UUID | None = None,
    location: str | None = None,
) -> Location | None:
    """Resolve an origin location by id, then by canonical name, then pilot."""
    if location_id is not None:
        for loc in locations:
            if loc.id == location_id:
                return loc
        return None
    if location:
        wanted = canonical_key(location)
        for loc in locations:
            if canonical_key(loc.name) == wanted:
                return loc
        return None
    return find_default_origin(locations)


def rank_basis(
    pairs: list[tuple[NormalizedPrice, PriceSnapshot | None]],
    *,
    locations: list[Location] | dict[str, tuple[float, float]] | None = None,
    origin: tuple[float, float] | None = None,
    radius_km: float | None = None,
    commodity: str | None = None,
    delivery_month_key: int | None = None,
) -> dict[str, object]:
    """Rank latest basis per location for a commodity + delivery month.

    Rank 1 is the strongest (highest) basis. Only the latest quote per
    location is ranked. Rows that cannot produce a basis go to ``unranked``
    with their reason. When ``radius_km`` is set, rows without stored
    coordinates are excluded and counted (``excluded_unknown_distance``)
    and rows beyond the radius are counted (``excluded_outside_radius``).
    When ``origin`` is ``None``, every location is ranked and the note says
    so -- no fallback coordinates are invented.
    """
    coords: dict[str, tuple[float, float]] = {}
    if isinstance(locations, dict):
        coords = dict(locations)
    elif locations:
        for loc in locations:
            if loc.latitude is not None and loc.longitude is not None:
                coords[str(loc.id)] = (float(loc.latitude), float(loc.longitude))

    wanted_commodity = canonical_key(commodity) if commodity else None

    # Latest quote per location (keyed by location_id, falling back to the
    # canonical location name when no id is stored).
    latest: dict[str, tuple[NormalizedPrice, PriceSnapshot | None, datetime | None]] = {}
    for row, snapshot in pairs:
        if wanted_commodity is not None and canonical_key(row.commodity_name) != wanted_commodity:
            continue
        if delivery_month_key is not None and delivery_month_key not in row_delivery_month_keys(row):
            continue
        key = str(row.location_id) if row.location_id else (canonical_key(row.location) or row.location)
        quote_date = quote_date_for_row(row, snapshot)
        previous = latest.get(key)
        if previous is None:
            latest[key] = (row, snapshot, quote_date)
            continue
        prev_date = previous[2]
        if quote_date is not None and (prev_date is None or quote_date > prev_date):
            latest[key] = (row, snapshot, quote_date)

    ranked: list[dict[str, object]] = []
    unranked: list[dict[str, object]] = []
    excluded_unknown_distance = 0
    excluded_outside_radius = 0
    for _key, (row, snapshot, _quote_date) in latest.items():
        computed = compute_basis_for_row(row)
        entry = serialize_basis_row(row, snapshot, computation=computed)
        distance_km: float | None = None
        if origin is not None:
            point = coords.get(str(row.location_id)) if row.location_id else None
            if point is None:
                if radius_km is not None:
                    excluded_unknown_distance += 1
                    continue
            else:
                distance_km = round(
                    haversine_km(origin[0], origin[1], point[0], point[1]), 2
                )
                if radius_km is not None and distance_km > radius_km:
                    excluded_outside_radius += 1
                    continue
        entry["distance_km"] = distance_km
        if computed.basis is None:
            unranked.append(entry)
        else:
            ranked.append(entry)

    ranked.sort(
        key=lambda item: (
            -(float(item["basis"]) if isinstance(item.get("basis"), (int, float)) else 0.0),
            str(item.get("location") or "").casefold(),
        )
    )
    for index, entry in enumerate(ranked, start=1):
        entry["rank"] = index
    unranked.sort(key=lambda item: str(item.get("location") or "").casefold())

    if origin is None:
        quality = (
            "No origin coordinates resolved (no location_id/location supplied "
            "and no stored Testville pilot location with coordinates); "
            "ranked across all locations with a basis. " + CURRENCY_NOT_STORED_NOTE
        )
    elif radius_km is not None:
        quality = (
            f"Ranked locations within {radius_km} km of the origin. "
            + CURRENCY_NOT_STORED_NOTE
        )
    else:
        quality = (
            "Ranked across all locations; distances are from the resolved "
            "origin. " + CURRENCY_NOT_STORED_NOTE
        )
    return {
        "ranked": ranked,
        "unranked": unranked,
        "row_count": len(ranked),
        "unranked_count": len(unranked),
        "excluded_unknown_distance": excluded_unknown_distance,
        "excluded_outside_radius": excluded_outside_radius,
        "currency": None,
        "unit": "bu",
        "data_quality": quality,
    }


def _normalize_stored_basis(value: Decimal | float | int | None) -> float | None:
    """Stored basis, applying the legacy cents-per-bushel rule (>= 10 -> /100)."""
    number = _to_float(value)
    if number is None:
        return None
    if abs(number) >= 10:
        return round(number / 100.0, 6)
    return number


def _to_decimal(value: Decimal | float | int | None) -> Decimal | None:
    if value is None:
        return None
    decimal = Decimal(str(value))
    return decimal if decimal.is_finite() else None


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number
