from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.market_search import (  # noqa: E402
    _row_delivery_month_key,
    haversine_km,
    parse_delivery_month,
)


def test_haversine_km_north_gower_to_russell_is_about_20km() -> None:
    # Testville ~45.05, -75.55; Russell ~45.26, -75.36.
    distance = haversine_km(45.05, -75.55, 45.26, -75.36)
    assert 25.0 < distance < 35.0


def test_haversine_km_same_point_is_zero() -> None:
    assert haversine_km(45.0, -75.0, 45.0, -75.0) == pytest.approx(0.0)


def test_haversine_km_is_symmetric() -> None:
    assert haversine_km(45.0, -75.0, 46.0, -76.0) == pytest.approx(
        haversine_km(46.0, -76.0, 45.0, -75.0)
    )


def test_parse_delivery_month_accepts_iso_and_names() -> None:
    assert parse_delivery_month("2026-12") == 2026 * 12 + 12
    assert parse_delivery_month("December 2026") == 2026 * 12 + 12
    assert parse_delivery_month("Dec 2026") == 2026 * 12 + 12
    assert parse_delivery_month(None) is None
    assert parse_delivery_month("  ") is None


def test_parse_delivery_month_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_delivery_month("not a month")
    with pytest.raises(ValueError):
        parse_delivery_month("2026-13")


def test_row_delivery_month_key_prefers_delivery_label() -> None:
    row = {"delivery_label": "December 2026", "futures_month": "March 2027"}
    assert _row_delivery_month_key(row) == 2026 * 12 + 12


def test_row_delivery_month_key_falls_back_to_futures_month() -> None:
    row = {"delivery_label": None, "futures_month": "Mar 2027"}
    assert _row_delivery_month_key(row) == 2027 * 12 + 3


def test_row_delivery_month_key_is_none_without_a_month() -> None:
    assert _row_delivery_month_key({"delivery_label": "Spot", "futures_month": None}) is None
