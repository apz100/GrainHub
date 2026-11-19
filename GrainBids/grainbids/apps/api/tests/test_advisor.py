"""Advisor silo v1 tests.

Covers breakeven math, scenario math, signal insufficient-data behaviour,
and the /ask scaffold 501. Route tests run the advisor router standalone
(it is not wired into app/main.py yet — the coordinator owns that), with
the DB and request-context dependencies overridden by fakes.
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.advisor import router as advisor_router  # noqa: E402
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.farm_profile import FarmProfile  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.services.advisor import (  # noqa: E402
    build_sell_hold_signal,
    calculate_breakeven,
    compare_sell_vs_hold,
    signal_for_profile_and_price,
)


ORG_ID = uuid.uuid4()
PROFILE_ID = uuid.uuid4()


class _FakeScalars:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeResult:
    """One result serving both accessors routes use.

    scalar_one_or_none() -> the configured single row (farm profile);
    scalars().all() -> the configured row list (profiles or prices).
    Each query in the advisor routes uses only one of the two.
    """

    def __init__(self, *, scalar=None, rows=None) -> None:
        self._scalar = scalar
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeSession:
    def __init__(self, *, scalar=None, rows=None) -> None:
        self._scalar = scalar
        self._rows = rows or []
        self.added = []
        self.commit_count = 0

    def execute(self, _query):
        return _FakeResult(scalar=self._scalar, rows=self._rows)

    def add(self, row) -> None:
        self.added.append(row)

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, _row) -> None:
        pass


def _make_profile(**overrides):
    values = {
        "id": PROFILE_ID,
        "org_id": ORG_ID,
        "farm_name": "Test Farm",
        "crop_mix_json": [
            {
                "commodity": "Corn",
                "acres": 500,
                "expected_yield_bu_per_acre": 200,
                "cost_per_acre": 800,
            }
        ],
        "risk_tolerance": "moderate",
    }
    values.update(overrides)
    return FarmProfile(**values)


def _make_price(**overrides):
    values = {
        "snapshot_id": uuid.uuid4(),
        "location": "Testville",
        "commodity_name": "Corn",
        "cash_price_bu": Decimal("5.00"),
        "futures_price": Decimal("5.20"),
        "composite_key": "testville|corn|||",
    }
    values.update(overrides)
    return NormalizedPrice(**values)


def _make_client(db):
    test_app = FastAPI()
    test_app.include_router(advisor_router)

    def override_db():
        yield db

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_request_context] = lambda: RequestContext(
        org_id=ORG_ID, user_email=None, user_role="admin"
    )
    return TestClient(test_app)


class BreakevenTests(unittest.TestCase):
    def test_breakeven_is_cost_over_yield(self) -> None:
        result = calculate_breakeven(yield_bu_per_acre=200, cost_per_acre=800)
        self.assertAlmostEqual(result.breakeven_per_bu, 4.00)
        self.assertIsNone(result.profit_per_acre)

    def test_profit_at_cash_price(self) -> None:
        # $5.00 cash vs $4.00 breakeven, 200 bu/ac -> $200/acre; 500 ac -> $100,000.
        result = calculate_breakeven(
            yield_bu_per_acre=200, cost_per_acre=800, cash_price_bu=5.00, acres=500
        )
        self.assertAlmostEqual(result.breakeven_per_bu, 4.00)
        self.assertAlmostEqual(result.margin_per_bu, 1.00)
        self.assertAlmostEqual(result.profit_per_acre, 200.00)
        self.assertAlmostEqual(result.profit_total, 100000.00)

    def test_loss_below_breakeven(self) -> None:
        result = calculate_breakeven(
            yield_bu_per_acre=200, cost_per_acre=800, cash_price_bu=3.50, acres=100
        )
        self.assertAlmostEqual(result.profit_per_acre, -100.00)
        self.assertAlmostEqual(result.profit_total, -10000.00)

    def test_zero_yield_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calculate_breakeven(yield_bu_per_acre=0, cost_per_acre=800)

    def test_negative_cost_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calculate_breakeven(yield_bu_per_acre=200, cost_per_acre=-10)


class ScenarioTests(unittest.TestCase):
    def test_hold_wins_when_deferred_beats_storage(self) -> None:
        # Sell now: 10,000 bu x $5.00 = $50,000.
        # Hold: 10,000 x $5.20 - 10,000 x $0.05 x 3 = $52,000 - $1,500 = $50,500.
        result = compare_sell_vs_hold(
            cash_price_now=5.00,
            deferred_price=5.20,
            storage_cost_per_bu_per_month=0.05,
            months_held=3,
            bushels=10000,
        )
        self.assertAlmostEqual(result.sell_now_net, 50000.00)
        self.assertAlmostEqual(result.hold_net, 50500.00)
        self.assertAlmostEqual(result.storage_cost_total, 1500.00)
        self.assertAlmostEqual(result.difference_hold_minus_sell_now, 500.00)
        self.assertEqual(result.recommendation, "hold")

    def test_sell_now_wins_when_storage_eats_the_gain(self) -> None:
        result = compare_sell_vs_hold(
            cash_price_now=5.00,
            deferred_price=5.05,
            storage_cost_per_bu_per_month=0.05,
            months_held=3,
            bushels=10000,
        )
        self.assertAlmostEqual(result.hold_net, 49000.00)
        self.assertEqual(result.recommendation, "sell_now")

    def test_zero_months_hold_is_just_deferred_price(self) -> None:
        result = compare_sell_vs_hold(
            cash_price_now=5.00,
            deferred_price=5.10,
            storage_cost_per_bu_per_month=0.05,
            months_held=0,
            bushels=1000,
        )
        self.assertAlmostEqual(result.storage_cost_total, 0.00)
        self.assertAlmostEqual(result.hold_net, 5100.00)
        self.assertEqual(result.recommendation, "hold")

    def test_negative_storage_rejected(self) -> None:
        with self.assertRaises(ValueError):
            compare_sell_vs_hold(
                cash_price_now=5.00,
                deferred_price=5.20,
                storage_cost_per_bu_per_month=-0.05,
                months_held=3,
                bushels=1000,
            )


class SignalTests(unittest.TestCase):
    def test_sell_when_cash_clears_moderate_cushion(self) -> None:
        # Breakeven $4.00, moderate needs +5% ($4.20); cash $5.00 clears it.
        signal = build_sell_hold_signal(cash_price_bu=5.00, breakeven_per_bu=4.00)
        self.assertEqual(signal.signal, "sell")
        self.assertAlmostEqual(signal.required_margin, 0.05)

    def test_hold_when_cash_below_cushion_but_above_breakeven(self) -> None:
        # $4.10 is above breakeven but below the $4.20 moderate threshold.
        signal = build_sell_hold_signal(cash_price_bu=4.10, breakeven_per_bu=4.00)
        self.assertEqual(signal.signal, "hold")

    def test_conservative_needs_bigger_cushion(self) -> None:
        signal = build_sell_hold_signal(
            cash_price_bu=4.15, breakeven_per_bu=4.00, risk_tolerance="conservative"
        )
        self.assertEqual(signal.signal, "hold")
        signal = build_sell_hold_signal(
            cash_price_bu=4.15, breakeven_per_bu=4.00, risk_tolerance="aggressive"
        )
        self.assertEqual(signal.signal, "sell")

    def test_insufficient_data_when_cash_missing(self) -> None:
        signal = build_sell_hold_signal(cash_price_bu=None, breakeven_per_bu=4.00)
        self.assertEqual(signal.signal, "insufficient_data")
        self.assertIn("cash price", signal.reasons[0])

    def test_insufficient_data_when_breakeven_missing(self) -> None:
        signal = build_sell_hold_signal(cash_price_bu=5.00, breakeven_per_bu=None)
        self.assertEqual(signal.signal, "insufficient_data")

    def test_profile_without_crop_entry_is_insufficient(self) -> None:
        profile = _make_profile(crop_mix_json=[{"commodity": "Soybeans", "acres": 100, "expected_yield_bu_per_acre": 50, "cost_per_acre": 400}])
        signal = signal_for_profile_and_price(farm_profile=profile, price_row=_make_price())
        self.assertEqual(signal.signal, "insufficient_data")
        self.assertIn("Corn", signal.reasons[0])

    def test_profile_with_no_price_is_insufficient(self) -> None:
        signal = signal_for_profile_and_price(farm_profile=_make_profile(), price_row=None)
        self.assertEqual(signal.signal, "insufficient_data")

    def test_no_profile_is_insufficient(self) -> None:
        signal = signal_for_profile_and_price(farm_profile=None, price_row=_make_price())
        self.assertEqual(signal.signal, "insufficient_data")

    def test_profile_and_price_produce_sell(self) -> None:
        signal = signal_for_profile_and_price(farm_profile=_make_profile(), price_row=_make_price())
        self.assertEqual(signal.signal, "sell")
        self.assertAlmostEqual(signal.breakeven_per_bu, 4.00)
        self.assertAlmostEqual(signal.cash_price_bu, 5.00)


class AdvisorRouteTests(unittest.TestCase):
    def test_create_farm_profile(self) -> None:
        db = _FakeSession()
        client = _make_client(db)
        try:
            response = client.post(
                "/api/advisor/farm-profiles",
                json={
                    "farm_name": "Test Farm",
                    "crop_mix": [
                        {"commodity": "Corn", "acres": 500, "expected_yield_bu_per_acre": 200, "cost_per_acre": 800}
                    ],
                    "risk_tolerance": "moderate",
                },
            )
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["farm_name"], "Test Farm")
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].org_id, ORG_ID)
        self.assertEqual(db.commit_count, 1)

    def test_create_farm_profile_rejects_bad_risk_tolerance(self) -> None:
        db = _FakeSession()
        client = _make_client(db)
        try:
            response = client.post(
                "/api/advisor/farm-profiles",
                json={"farm_name": "Test Farm", "risk_tolerance": "reckless"},
            )
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 400)

    def test_list_farm_profiles(self) -> None:
        db = _FakeSession(rows=[_make_profile()])
        client = _make_client(db)
        try:
            response = client.get("/api/advisor/farm-profiles")
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["rows"]), 1)
        self.assertEqual(response.json()["rows"][0]["farm_name"], "Test Farm")

    def test_breakeven_endpoint(self) -> None:
        db = _FakeSession()
        client = _make_client(db)
        try:
            response = client.post(
                "/api/advisor/breakeven",
                json={"yield_bu_per_acre": 200, "cost_per_acre": 800, "cash_price_bu": 5.0, "acres": 500},
            )
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertAlmostEqual(body["breakeven_per_bu"], 4.0)
        self.assertAlmostEqual(body["profit_total"], 100000.0)

    def test_breakeven_endpoint_rejects_bad_input(self) -> None:
        db = _FakeSession()
        client = _make_client(db)
        try:
            response = client.post(
                "/api/advisor/breakeven",
                json={"yield_bu_per_acre": 0, "cost_per_acre": 800},
            )
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 422)  # pydantic gt=0 guard

    def test_scenarios_endpoint(self) -> None:
        db = _FakeSession()
        client = _make_client(db)
        try:
            response = client.post(
                "/api/advisor/scenarios",
                json={
                    "cash_price_now": 5.0,
                    "deferred_price": 5.2,
                    "storage_cost_per_bu_per_month": 0.05,
                    "months_held": 3,
                    "bushels": 10000,
                },
            )
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recommendation"], "hold")
        self.assertAlmostEqual(response.json()["hold_net"], 50500.0)

    def test_signal_endpoint_with_real_price(self) -> None:
        db = _FakeSession(scalar=_make_profile(), rows=[_make_price()])
        client = _make_client(db)
        try:
            response = client.get("/api/advisor/signal", params={"commodity_name": "Corn"})
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["signal"], "sell")
        self.assertAlmostEqual(body["breakeven_per_bu"], 4.0)
        self.assertAlmostEqual(body["cash_price_bu"], 5.0)

    def test_signal_endpoint_insufficient_without_price(self) -> None:
        db = _FakeSession(scalar=_make_profile(), rows=[])
        client = _make_client(db)
        try:
            response = client.get("/api/advisor/signal", params={"commodity_name": "Corn"})
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["signal"], "insufficient_data")

    def test_signal_endpoint_unknown_profile_is_404(self) -> None:
        db = _FakeSession(scalar=None, rows=[_make_price()])
        client = _make_client(db)
        try:
            response = client.get(
                "/api/advisor/signal",
                params={"commodity_name": "Corn", "farm_profile_id": str(uuid.uuid4())},
            )
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 404)

    def test_ask_returns_501_without_llm_key(self) -> None:
        db = _FakeSession()
        client = _make_client(db)
        env = {k: v for k, v in os.environ.items() if k not in {"GRAINHUB_LLM_API_KEY", "OPENAI_API_KEY"}}
        try:
            with mock.patch.dict(os.environ, env, clear=True):
                response = client.post("/api/advisor/ask", json={"question": "Should I sell my corn?"})
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 501)
        self.assertIn("not configured", response.json()["detail"])
        self.assertIn("GRAINHUB_LLM_API_KEY", response.json()["detail"])

    def test_ask_returns_501_even_with_llm_key_set(self) -> None:
        db = _FakeSession()
        client = _make_client(db)
        try:
            with mock.patch.dict(os.environ, {"GRAINHUB_LLM_API_KEY": "test-key-not-real"}):
                response = client.post("/api/advisor/ask", json={"question": "Should I sell my corn?"})
        finally:
            client.app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 501)
        self.assertIn("is wired up", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
