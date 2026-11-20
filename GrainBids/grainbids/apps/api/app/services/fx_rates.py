"""Bank of Canada FX rates for display-time currency conversion.

Currency decision (2026-11-20, docs/plans/currency-design.md):
prices are stored in their source currency and are never converted
at ingest. Conversion exists only as an explicit, labelled display
toggle, and the rate used is the Bank of Canada daily noon rate,
always shown with its as-of date.

The BoC Valet series ``FX_USDCAD`` is that daily rate, quoted as
Canadian dollars per one US dollar (e.g. 1.3642 means 1 USD =
1.3642 CAD). Only the CAD<->USD pair is supported — it is the only
pair the stored data can currently contain.

A failed fetch returns ``None``; callers must then refuse to convert
rather than fall back to an unlabelled or stale number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import requests

BOC_VALET_URL = "https://www.bankofcanada.ca/valet/observations/FX_USDCAD/json"
FX_SOURCE_LABEL = "Bank of Canada daily noon rate (series FX_USDCAD)"
_FETCH_TIMEOUT_SECONDS = 10

# One fetch per process per day is plenty for a daily rate; the
# as-of date on the rate itself is what responses display.
_rate_cache: dict[str, "FxRate | None"] = {}


@dataclass(frozen=True)
class FxRate:
    """A labelled USD/CAD rate: ``rate`` CAD per 1 USD, as of ``as_of``."""

    rate: Decimal
    as_of: date
    source: str = FX_SOURCE_LABEL

    def to_dict(self) -> dict[str, object]:
        return {
            "pair": "USD/CAD",
            "rate": float(self.rate),
            "as_of": self.as_of.isoformat(),
            "source": self.source,
        }


def _parse_boc_payload(payload: object) -> FxRate | None:
    """Latest usable observation from a BoC Valet JSON payload."""
    if not isinstance(payload, dict):
        return None
    observations = payload.get("observations")
    if not isinstance(observations, list):
        return None
    latest: FxRate | None = None
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        raw_date = observation.get("d")
        series = observation.get("FX_USDCAD")
        if not isinstance(raw_date, str) or not isinstance(series, dict):
            continue
        try:
            as_of = date.fromisoformat(raw_date)
            rate = Decimal(str(series.get("v")))
        except (ValueError, InvalidOperation):
            continue
        if not rate.is_finite() or rate <= 0:
            continue
        if latest is None or as_of > latest.as_of:
            latest = FxRate(rate=rate, as_of=as_of)
    return latest


def fetch_usd_cad_rate() -> FxRate | None:
    """Fetch the latest BoC daily noon USD/CAD rate; None on failure."""
    try:
        response = requests.get(
            BOC_VALET_URL,
            params={"recent": 7},
            timeout=_FETCH_TIMEOUT_SECONDS,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:  # noqa: BLE001 - any failure means "no rate", never a guess
        return None
    return _parse_boc_payload(payload)


def get_usd_cad_rate() -> FxRate | None:
    """Today's cached BoC rate (one upstream fetch per day per process)."""
    cache_key = datetime.now(timezone.utc).date().isoformat()
    if cache_key not in _rate_cache:
        _rate_cache[cache_key] = fetch_usd_cad_rate()
    return _rate_cache[cache_key]


def convert_amount(
    amount: Decimal | float | int | None,
    *,
    from_currency: str | None,
    to_currency: str | None,
    fx_rate: FxRate | None,
) -> Decimal | None:
    """Convert ``amount`` between CAD and USD using ``fx_rate``.

    Returns the amount unchanged when the currencies already match,
    and ``None`` when conversion is impossible (missing amount,
    unknown currency, unsupported pair, or no rate) — a caller must
    surface that, never silently present the unconverted figure as
    converted.
    """
    if amount is None or from_currency is None or to_currency is None:
        return None
    source = str(from_currency).strip().upper()
    target = str(to_currency).strip().upper()
    if not source or not target:
        return None
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    if source == target:
        return value
    if fx_rate is None:
        return None
    if source == "USD" and target == "CAD":
        return (value * fx_rate.rate).quantize(Decimal("0.0001"))
    if source == "CAD" and target == "USD":
        return (value / fx_rate.rate).quantize(Decimal("0.0001"))
    return None
