"""``[sources]`` toggle gating for the FastAPI orchestrator (Cycle 20).

``config.toml`` (``app/platform/market_data/sources/config.toml``) has a
``[sources]`` table with one boolean per registry adapter key — the
legacy GrainBidder orchestrator already honours it, but the FastAPI
side never read it, so toggled-off adapters (today ``bunge`` and
``mapleview``) were still seedable into the ``Source`` table and still
polled on schedule.

This module is the single place the FastAPI side consults those
toggles. It reuses the existing config loader
(``app.platform.market_data.sources.grain_bids.config.config``), whose
``source_enabled()`` already implements the rule "missing toggle =
enabled". No new config mechanism is introduced here.

Rules:
- Only an explicit ``false`` in ``[sources]`` disables an adapter.
- A missing toggle entry defaults to enabled, so adapters without a
  config entry keep working.
- If the config file cannot be read at all (missing file, parse
  error), every adapter defaults to enabled rather than failing the
  seed/poll path — the toggle is a gate, not a hard dependency.
"""

from __future__ import annotations

try:
    from app.platform.market_data.sources.grain_bids.config import config as _config
except Exception:  # noqa: BLE001 - config file missing/unreadable: fail open
    _config = None


def is_adapter_enabled(adapter_key: str) -> bool:
    """Return True unless ``[sources]`` explicitly sets this key false.

    The key is normalised (stripped, lower-cased) to match how the
    registry stores adapter keys. A blank key is treated as enabled.
    """
    key = (adapter_key or "").strip().lower()
    if not key:
        return True
    if _config is None:
        return True
    try:
        return bool(_config.source_enabled(key))
    except Exception:  # noqa: BLE001 - any loader failure fails open
        return True


def disabled_adapter_keys(adapter_keys: list[str]) -> list[str]:
    """Return the subset of ``adapter_keys`` whose toggle is off, sorted."""
    return sorted(key for key in adapter_keys if not is_adapter_enabled(key))
