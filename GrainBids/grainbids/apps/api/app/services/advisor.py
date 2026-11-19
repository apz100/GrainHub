"""Advisor silo v1: pure-function grain-marketing math.

Everything in this module is a pure function: no database access, no
network calls, no LLM calls, and no invented prices. Every price that goes
into a calculation must be supplied by the caller — either typed in by the
farmer or read from a real ``NormalizedPrice`` row. When a required input
is missing, the signal functions return ``insufficient_data`` instead of
guessing.

Rules (v1, deliberately simple and explainable):

* Breakeven: ``cost_per_acre / yield_bu_per_acre`` ($/bu).
* Sell/hold: compare the real cash price against breakeven plus a cushion
  that depends on the farm's risk tolerance — conservative farmers need
  cash >= breakeven + 10% before a "sell" signal, moderate +5%, aggressive
  +0%. Below that threshold the signal is "hold" (selling would lock in
  less than the cushion above cost, or a loss).
* Scenario planner: sell-now net vs hold net, where holding earns the
  user-supplied deferred price but pays the user-supplied storage cost.
  The deferred price is an input, never a forecast.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

# Cushion above breakeven required before the signal says "sell".
RISK_MARGIN = {
    "conservative": Decimal("0.10"),
    "moderate": Decimal("0.05"),
    "aggressive": Decimal("0.00"),
}

# Env vars that count as "an LLM key is configured". v1 never calls an LLM
# even when one is set (see llm_config_status); the key only changes the
# 501 message on POST /api/advisor/ask.
LLM_API_KEY_ENV_VARS = ("GRAINHUB_LLM_API_KEY", "OPENAI_API_KEY")


@dataclass(frozen=True)
class BreakevenResult:
    breakeven_per_bu: float
    margin_per_bu: float | None
    profit_per_acre: float | None
    profit_total: float | None
    cash_price_bu: float | None


@dataclass(frozen=True)
class ScenarioResult:
    sell_now_net: float
    hold_net: float
    storage_cost_total: float
    difference_hold_minus_sell_now: float
    recommendation: str  # "sell_now" | "hold"
    note: str


@dataclass(frozen=True)
class SellHoldSignal:
    signal: str  # "sell" | "hold" | "insufficient_data"
    breakeven_per_bu: float | None
    cash_price_bu: float | None
    futures_price: float | None
    required_margin: float | None
    reasons: list[str]


def calculate_breakeven(
    *,
    yield_bu_per_acre: Decimal | float | int,
    cost_per_acre: Decimal | float | int,
    cash_price_bu: Decimal | float | int | None = None,
    acres: Decimal | float | int | None = None,
) -> BreakevenResult:
    """Breakeven $/bu and profit at a supplied cash price.

    Raises ValueError on non-positive yield, negative cost/price, or
    non-positive acres. ``cash_price_bu`` is optional: without it only the
    breakeven itself is returned.
    """
    yield_value = _positive_decimal(yield_bu_per_acre, "yield_bu_per_acre")
    cost = _non_negative_decimal(cost_per_acre, "cost_per_acre")
    cash = _non_negative_decimal(cash_price_bu, "cash_price_bu") if cash_price_bu is not None else None
    acres_value = _positive_decimal(acres, "acres") if acres is not None else None

    breakeven = cost / yield_value
    margin = cash - breakeven if cash is not None else None
    profit_per_acre = margin * yield_value if margin is not None else None
    profit_total = profit_per_acre * acres_value if profit_per_acre is not None and acres_value is not None else None
    return BreakevenResult(
        breakeven_per_bu=_to_float(breakeven),
        margin_per_bu=_to_float(margin),
        profit_per_acre=_to_float(profit_per_acre),
        profit_total=_to_float(profit_total),
        cash_price_bu=_to_float(cash),
    )


def compare_sell_vs_hold(
    *,
    cash_price_now: Decimal | float | int,
    deferred_price: Decimal | float | int,
    storage_cost_per_bu_per_month: Decimal | float | int,
    months_held: Decimal | float | int,
    bushels: Decimal | float | int,
) -> ScenarioResult:
    """Sell-now vs hold comparison using ONLY supplied inputs.

    ``deferred_price`` is the price the farmer expects (or is offered) for
    deferred delivery — it is an input, not a forecast made here. Holding
    costs ``storage_cost_per_bu_per_month * months_held`` per bushel.
    Raises ValueError on negative prices/costs/months or non-positive bushels.
    """
    cash = _non_negative_decimal(cash_price_now, "cash_price_now")
    deferred = _non_negative_decimal(deferred_price, "deferred_price")
    storage_rate = _non_negative_decimal(storage_cost_per_bu_per_month, "storage_cost_per_bu_per_month")
    months = _non_negative_decimal(months_held, "months_held")
    bushels_value = _positive_decimal(bushels, "bushels")

    sell_now_net = cash * bushels_value
    storage_total = storage_rate * months * bushels_value
    hold_net = deferred * bushels_value - storage_total
    difference = hold_net - sell_now_net
    return ScenarioResult(
        sell_now_net=_to_float(sell_now_net),
        hold_net=_to_float(hold_net),
        storage_cost_total=_to_float(storage_total),
        difference_hold_minus_sell_now=_to_float(difference),
        recommendation="hold" if difference > 0 else "sell_now",
        note=(
            "Holding only wins if the supplied deferred price beats the cash "
            "price by more than the supplied storage cost. No price is "
            "forecast here; change the deferred price input to test other outcomes."
        ),
    )


def build_sell_hold_signal(
    *,
    cash_price_bu: Decimal | float | int | None,
    breakeven_per_bu: Decimal | float | int | None,
    risk_tolerance: str = "moderate",
    futures_price: Decimal | float | int | None = None,
    commodity: str | None = None,
    location: str | None = None,
) -> SellHoldSignal:
    """Sell/hold signal from a real cash price and a breakeven.

    Returns ``insufficient_data`` when the cash price or the breakeven is
    missing — never a signal built on a guessed number. Raises ValueError
    on an unknown risk tolerance.
    """
    cash = _to_decimal(cash_price_bu) if cash_price_bu is not None else None
    breakeven = _to_decimal(breakeven_per_bu) if breakeven_per_bu is not None else None
    futures = _to_decimal(futures_price) if futures_price is not None else None
    what = _describe(commodity, location)

    if cash is None or breakeven is None:
        missing = []
        if cash is None:
            missing.append("cash price")
        if breakeven is None:
            missing.append("breakeven (needs yield and cost per acre)")
        return SellHoldSignal(
            signal="insufficient_data",
            breakeven_per_bu=_to_float(breakeven),
            cash_price_bu=_to_float(cash),
            futures_price=_to_float(futures),
            required_margin=None,
            reasons=[f"Cannot signal {what}: missing {', '.join(missing)}."],
        )

    tolerance = (risk_tolerance or "moderate").strip().lower()
    if tolerance not in RISK_MARGIN:
        raise ValueError(f"unknown risk_tolerance: {risk_tolerance!r}")
    margin = RISK_MARGIN[tolerance]
    threshold = breakeven * (Decimal("1") + margin)
    reasons = [
        f"Cash price ${_to_float(cash):.2f}/bu vs breakeven ${_to_float(breakeven):.2f}/bu{what}.",
        f"{tolerance.capitalize()} risk tolerance requires cash at or above "
        f"${_to_float(threshold):.2f}/bu (breakeven + {int(margin * 100)}%).",
    ]
    if futures is not None:
        reasons.append(f"Deferred/futures reference supplied with the price: ${float(futures):.2f}/bu.")
    if cash >= threshold:
        reasons.append("Cash price clears the required cushion above breakeven: sell signal.")
        signal = "sell"
    else:
        reasons.append("Cash price does not clear the required cushion above breakeven: hold signal.")
        signal = "hold"
    return SellHoldSignal(
        signal=signal,
        breakeven_per_bu=_to_float(breakeven),
        cash_price_bu=_to_float(cash),
        futures_price=_to_float(futures),
        required_margin=_to_float(margin),
        reasons=reasons,
    )


def find_crop_entry(crop_mix: list[dict[str, Any]] | dict[str, Any] | None, commodity: str | None) -> dict[str, Any] | None:
    """Find the crop-mix entry for a commodity (case-insensitive).

    ``crop_mix`` is the list stored in ``FarmProfile.crop_mix_json``.
    Returns None when there is no entry for the commodity.
    """
    if not crop_mix or not commodity:
        return None
    wanted = " ".join(str(commodity).strip().lower().split())
    entries = crop_mix if isinstance(crop_mix, list) else [crop_mix]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("commodity")
        if name and " ".join(str(name).strip().lower().split()) == wanted:
            return entry
    return None


def signal_for_profile_and_price(*, farm_profile: Any | None, price_row: Any | None) -> SellHoldSignal:
    """Sell/hold signal for a farm profile against a real price row.

    ``price_row`` is a ``NormalizedPrice`` (or any duck-typed object with
    ``cash_price_bu`` / ``futures_price`` / ``commodity_name`` /
    ``location`` attributes). Returns ``insufficient_data`` when the
    profile is missing, the price row is missing, the profile has no
    crop-mix entry for the price's commodity, or yield/cost are missing.
    """
    if farm_profile is None:
        return SellHoldSignal(
            signal="insufficient_data",
            breakeven_per_bu=None,
            cash_price_bu=None,
            futures_price=None,
            required_margin=None,
            reasons=["Cannot signal: no farm profile supplied. Create one first."],
        )
    if price_row is None:
        return SellHoldSignal(
            signal="insufficient_data",
            breakeven_per_bu=None,
            cash_price_bu=None,
            futures_price=None,
            required_margin=None,
            reasons=["Cannot signal: no cash price found for this commodity/location."],
        )

    commodity = getattr(price_row, "commodity_name", None)
    location = getattr(price_row, "location", None)
    cash = getattr(price_row, "cash_price_bu", None)
    futures = getattr(price_row, "futures_price", None)
    what = _describe(commodity, location)

    entry = find_crop_entry(getattr(farm_profile, "crop_mix_json", None), commodity)
    if entry is None:
        return SellHoldSignal(
            signal="insufficient_data",
            breakeven_per_bu=None,
            cash_price_bu=_to_float(_to_decimal(cash)) if cash is not None else None,
            futures_price=_to_float(_to_decimal(futures)) if futures is not None else None,
            required_margin=None,
            reasons=[
                f"Cannot signal {what}: farm profile has no crop-mix entry "
                f"for {commodity or 'this commodity'} (no yield/cost to build a breakeven)."
            ],
        )

    try:
        breakeven = calculate_breakeven(
            yield_bu_per_acre=entry.get("expected_yield_bu_per_acre"),
            cost_per_acre=entry.get("cost_per_acre"),
        )
    except (ValueError, TypeError, InvalidOperation):
        return SellHoldSignal(
            signal="insufficient_data",
            breakeven_per_bu=None,
            cash_price_bu=_to_float(_to_decimal(cash)) if cash is not None else None,
            futures_price=_to_float(_to_decimal(futures)) if futures is not None else None,
            required_margin=None,
            reasons=[
                f"Cannot signal {what}: crop-mix entry for {commodity} is "
                "missing a positive yield or a non-negative cost per acre."
            ],
        )

    return build_sell_hold_signal(
        cash_price_bu=cash,
        breakeven_per_bu=breakeven.breakeven_per_bu,
        risk_tolerance=getattr(farm_profile, "risk_tolerance", "moderate") or "moderate",
        futures_price=futures,
        commodity=commodity,
        location=location,
    )


def llm_config_status() -> dict[str, Any]:
    """Report whether an LLM key is configured — without calling anything.

    v1 is a scaffold: even when a key IS set, no provider is wired up and
    no paid API is called. The route returns 501 either way; this only
    changes the message so Adam knows what is missing.
    """
    configured_var = next((name for name in LLM_API_KEY_ENV_VARS if os.environ.get(name)), None)
    if configured_var is None:
        return {
            "configured": False,
            "detail": (
                "LLM key/config not configured: set GRAINHUB_LLM_API_KEY "
                "(or OPENAI_API_KEY) and choose a provider before the "
                "Advisor assistant can answer. No LLM was called."
            ),
        }
    return {
        "configured": True,
        "detail": (
            "LLM key is configured via "
            f"{configured_var}, but no LLM provider integration is wired up "
            "in Cycle 1, so the assistant is not available yet. No LLM was called."
        ),
    }


def _describe(commodity: str | None, location: str | None) -> str:
    if commodity and location:
        return f" for {commodity} at {location}"
    if commodity:
        return f" for {commodity}"
    if location:
        return f" at {location}"
    return ""


def _to_decimal(value: Decimal | float | int | None) -> Decimal | None:
    if value is None:
        return None
    parsed = Decimal(str(value))
    return parsed if parsed.is_finite() else None


def _positive_decimal(value: Decimal | float | int | None, field: str) -> Decimal:
    parsed = _to_decimal(value)
    if parsed is None or parsed <= 0:
        raise ValueError(f"{field} must be a positive number")
    return parsed


def _non_negative_decimal(value: Decimal | float | int | None, field: str) -> Decimal:
    parsed = _to_decimal(value)
    if parsed is None or parsed < 0:
        raise ValueError(f"{field} must be a non-negative number")
    return parsed


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if number == number else None  # guard against NaN
