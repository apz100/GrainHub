"""Basis alerts (Cycle 6).

Pure helpers that let a price-alert rule trigger on **basis moves**,
not just on cash price. The existing evaluator
(:mod:`app.services.alert_evaluator`) already evaluates ``basis`` and
``basis_change`` rule types against stored ``NormalizedPrice`` rows; this
module works one level up, on the **basis tracker response shape**
(:func:`app.services.basis_tracker.rank_basis` /
``GET /api/basis/tracker``):

.. code-block:: python

    {
        "ranked": [
            {"location": "...", "commodity_name": "Corn", "basis": 0.42,
             "futures_month": "Jul 2026", "delivery_label": "...",
             "source_status": "healthy", ...},
            ...
        ],
        "unranked": [  # rows whose basis could not be computed
            {"location": "...", "basis": None, "missing_reason": "..."},
            ...
        ],
        ...
    }

Design rules:

* Pure functions only — no DB access, no network, no sending, no
  invented prices. A basis value is only ever read from the input.
* A row whose basis is missing, non-numeric, or non-finite is skipped
  and counted in ``skipped_missing``; it never triggers and never
  counts as "no cross".
* ``operator=">"`` / ``">="`` means "basis above the threshold"
  (direction ``"up"``); ``"<"`` / ``"<="`` means "basis below the
  threshold" (direction ``"down"``). Any other operator raises
  ``ValueError`` instead of silently doing nothing.
* ``detect_basis_crossing`` answers the move question for one location:
  did the basis cross the threshold between a previous reading and the
  current one (up through it, or down through it)?

All example locations in the docstrings/tests are synthetic
(Testville / Exampletown); no real elevator is used as an example.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation


UP_OPERATORS = (">", ">=")
DOWN_OPERATORS = ("<", "<=")


@dataclass(frozen=True)
class BasisAlertCrossing:
    """One location whose basis crossed the alert threshold."""

    location: str
    basis: Decimal
    threshold: Decimal
    direction: str  # "up" (basis above threshold) or "down" (below)
    operator: str
    commodity_name: str | None = None
    futures_month: str | None = None
    delivery_label: str | None = None
    source_status: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "location": self.location,
            "basis": float(self.basis),
            "threshold": float(self.threshold),
            "direction": self.direction,
            "operator": self.operator,
            "commodity_name": self.commodity_name,
            "futures_month": self.futures_month,
            "delivery_label": self.delivery_label,
            "source_status": self.source_status,
        }


@dataclass(frozen=True)
class BasisAlertEvaluation:
    """Result of checking a basis tracker response against a threshold."""

    crossings: list[BasisAlertCrossing] = field(default_factory=list)
    evaluated: int = 0
    skipped_missing: int = 0

    @property
    def crossed_locations(self) -> list[str]:
        return [crossing.location for crossing in self.crossings]


def detect_basis_crossing(
    previous_basis: Decimal | float | int | str | None,
    current_basis: Decimal | float | int | str | None,
    threshold: Decimal | float | int | str,
) -> str | None:
    """Detect a threshold crossing between two basis readings.

    Returns ``"up"`` when the previous basis was below the threshold and
    the current basis is at or above it, ``"down"`` when the previous
    basis was above the threshold and the current basis is at or below
    it, and ``None`` when there was no crossing (including when either
    reading is missing or non-finite — a missing reading is never treated
    as a crossing).
    """
    previous = _to_decimal(previous_basis)
    current = _to_decimal(current_basis)
    limit = _to_decimal(threshold)
    if previous is None or current is None or limit is None:
        return None
    if previous < limit <= current:
        return "up"
    if previous > limit >= current:
        return "down"
    return None


def find_basis_crossings(
    response_or_rows: dict[str, object] | list[dict[str, object]] | None,
    *,
    threshold: Decimal | float | int | str,
    operator: str = ">",
) -> BasisAlertEvaluation:
    """Find locations whose basis crossed ``threshold``.

    ``response_or_rows`` is either a basis tracker response dict (the
    ``"ranked"`` list is checked; ``"unranked"`` rows are counted as
    skipped-missing, since by construction they have no computable
    basis) or a plain list of per-location row dicts with at least
    ``"location"`` and ``"basis"`` keys. ``None`` or an empty input
    evaluates to zero crossings.

    ``operator`` must be one of ``">"``, ``">="``, ``"<"``, ``"<="``;
    ``">"``/``">="`` report direction ``"up"``, ``"<"``/``"<="`` report
    ``"down"``. Anything else raises ``ValueError``.
    """
    normalized_operator = (operator or "").strip()
    if normalized_operator in UP_OPERATORS:
        direction = "up"
    elif normalized_operator in DOWN_OPERATORS:
        direction = "down"
    else:
        raise ValueError(
            f"Unsupported basis alert operator: {operator!r} "
            "(expected one of '>', '>=', '<', '<=')"
        )

    limit = _to_decimal(threshold)
    if limit is None:
        raise ValueError(f"Threshold is not a finite number: {threshold!r}")

    ranked, unranked = _split_response(response_or_rows)

    crossings: list[BasisAlertCrossing] = []
    evaluated = 0
    skipped_missing = len(unranked)

    for row in ranked:
        if not isinstance(row, dict):
            skipped_missing += 1
            continue
        basis = _to_decimal(row.get("basis"))
        if basis is None:
            skipped_missing += 1
            continue
        evaluated += 1
        if not _compare(basis, limit, normalized_operator):
            continue
        location = _row_location(row)
        crossings.append(
            BasisAlertCrossing(
                location=location,
                basis=basis,
                threshold=limit,
                direction=direction,
                operator=normalized_operator,
                commodity_name=_as_text(row.get("commodity_name")),
                futures_month=_as_text(row.get("futures_month")),
                delivery_label=_as_text(row.get("delivery_label")),
                source_status=_as_text(row.get("source_status")),
            )
        )

    return BasisAlertEvaluation(
        crossings=crossings,
        evaluated=evaluated,
        skipped_missing=skipped_missing,
    )


def _split_response(
    response_or_rows: dict[str, object] | list[dict[str, object]] | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Split tracker-response-or-rows into (ranked, unranked) row lists."""
    if response_or_rows is None:
        return [], []
    if isinstance(response_or_rows, dict):
        ranked = response_or_rows.get("ranked") or []
        unranked = response_or_rows.get("unranked") or []
        return (
            ranked if isinstance(ranked, list) else [],
            unranked if isinstance(unranked, list) else [],
        )
    if isinstance(response_or_rows, list):
        return list(response_or_rows), []
    return [], []


def _row_location(row: dict[str, object]) -> str:
    """Location label for a row, falling back to its location id."""
    location = _as_text(row.get("location"))
    if location:
        return location
    location_id = _as_text(row.get("location_id"))
    if location_id:
        return f"location:{location_id}"
    return "unknown location"


def _compare(value: Decimal, threshold: Decimal, operator: str) -> bool:
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    return False


def _to_decimal(value: Decimal | float | int | str | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value if value.is_finite() else None
    if isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return parsed if parsed.is_finite() else None


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
