"""Basis-alert wiring tests (Cycle 7).

Tests for the integration between :mod:`app.services.basis_alerts` and
:mod:`app.services.alert_evaluator`: a rule's optional
``basis_threshold`` fires a basis alert from the snapshot rows, while
rules without one behave exactly as price-only rules.

No DB, no network, no sending. The evaluator runs against a stub
session that answers its four queries from in-memory model instances.
All locations are synthetic (Testville / Exampletown); no real
elevator is used.
"""

from __future__ import annotations

import sys
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.alert_rule import AlertRule  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.services.alert_evaluator import (  # noqa: E402
    _evaluate_rule_basis_threshold,
    evaluate_alert_rules_for_snapshot,
)
from app.services.basis_alerts import evaluate_rule_basis_threshold  # noqa: E402

ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SOURCE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
SNAPSHOT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
COMMODITY_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _tracker_row(location: str, basis, **extra):
    row = {"location": location, "commodity_name": "Corn", "basis": basis}
    row.update(extra)
    return row


def _rule(**overrides):
    values = {
        "org_id": ORG_ID,
        "rule_type": "cash_price_bu",
        "threshold_value": Decimal("5.00"),
        "comparison_operator": ">",
        "basis_threshold": None,
        "basis_threshold_operator": None,
        "location": None,
        "delivery_months_json": None,
        "saved_search_id": None,
        "commodity_id": None,
        "is_active": True,
    }
    values.update(overrides)
    return AlertRule(**values)


def _snapshot_row(**overrides):
    values = {
        "snapshot_id": SNAPSHOT_ID,
        "location": "Testville",
        "commodity_name": "Corn",
        "source_name": "Test Source",
        "delivery_label": "Nov 2026",
        "futures_month": "Dec 2026",
        "basis": Decimal("0.42"),
        "cash_price_bu": Decimal("4.10"),
        "composite_key": "test-1",
    }
    values.update(overrides)
    return NormalizedPrice(**values)


class _FakeResult:
    def __init__(self, first=None, scalars=None):
        self._first = first
        self._scalars = list(scalars or [])

    def first(self):
        return self._first

    def scalars(self):
        return self

    def all(self):
        return list(self._scalars)


class _FakeSession:
    """Stub for the evaluator's db calls; answers from canned rows."""

    def __init__(self, *, snapshot, source, rules, rows):
        self._snapshot = snapshot
        self._source = source
        self._rules = rules
        self._rows = rows
        self.added = []
        self.commits = 0

    def execute(self, stmt):
        text = str(stmt)
        if "price_snapshots" in text:
            return _FakeResult(first=(self._snapshot, self._source))
        if "alert_rules" in text:
            return _FakeResult(scalars=self._rules)
        if "normalized_prices" in text:
            return _FakeResult(scalars=self._rows)
        if "alerts" in text:
            # Dedup probe: an identical open alert exists once one was
            # added for this (single-rule, single-message) scenario.
            return _FakeResult(first=("existing",) if self.added else None)
        raise AssertionError(f"unexpected query: {text[:120]}")

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


def _run(rules, rows):
    snapshot = PriceSnapshot(
        id=SNAPSHOT_ID, source_id=SOURCE_ID, commodity_id=COMMODITY_ID
    )
    source = Source(id=SOURCE_ID, org_id=ORG_ID, name="Test Source")
    session = _FakeSession(
        snapshot=snapshot, source=source, rules=rules, rows=rows
    )
    result = evaluate_alert_rules_for_snapshot(session, snapshot_id=SNAPSHOT_ID)
    return result, session


class EvaluateRuleBasisThresholdTests(unittest.TestCase):
    def test_rule_with_basis_threshold_triggers(self) -> None:
        rule = SimpleNamespace(basis_threshold=Decimal("0.25"), basis_threshold_operator=">")
        evaluation = evaluate_rule_basis_threshold(
            rule, [_tracker_row("Testville", Decimal("0.42"))]
        )
        assert evaluation is not None
        self.assertEqual(len(evaluation.crossings), 1)
        self.assertEqual(evaluation.crossings[0].location, "Testville")
        self.assertEqual(evaluation.crossings[0].direction, "up")
        self.assertEqual(evaluation.evaluated, 1)
        self.assertEqual(evaluation.skipped_missing, 0)

    def test_rule_without_basis_threshold_returns_none(self) -> None:
        rule = SimpleNamespace(basis_threshold=None, basis_threshold_operator=None)
        self.assertIsNone(
            evaluate_rule_basis_threshold(rule, [_tracker_row("Testville", Decimal("0.42"))])
        )

    def test_rule_missing_threshold_attribute_returns_none(self) -> None:
        # Rules created before the Cycle 7 columns existed have no
        # attribute at all; getattr must not raise.
        rule = SimpleNamespace()
        self.assertIsNone(
            evaluate_rule_basis_threshold(rule, [_tracker_row("Testville", Decimal("0.42"))])
        )

    def test_no_cross(self) -> None:
        rule = SimpleNamespace(basis_threshold=Decimal("0.25"), basis_threshold_operator=">")
        evaluation = evaluate_rule_basis_threshold(
            rule, [_tracker_row("Testville", Decimal("0.10"))]
        )
        assert evaluation is not None
        self.assertEqual(evaluation.crossings, [])
        self.assertEqual(evaluation.evaluated, 1)

    def test_missing_basis_skipped(self) -> None:
        rule = SimpleNamespace(basis_threshold=Decimal("0.25"), basis_threshold_operator=">")
        evaluation = evaluate_rule_basis_threshold(
            rule,
            [
                _tracker_row("Testville", None),
                _tracker_row("Exampletown", Decimal("0.42")),
            ],
        )
        assert evaluation is not None
        self.assertEqual(evaluation.crossed_locations, ["Exampletown"])
        self.assertEqual(evaluation.evaluated, 1)
        self.assertEqual(evaluation.skipped_missing, 1)

    def test_invalid_threshold_raises(self) -> None:
        rule = SimpleNamespace(basis_threshold="not-a-number", basis_threshold_operator=">")
        with self.assertRaises(ValueError):
            evaluate_rule_basis_threshold(rule, [_tracker_row("Testville", Decimal("0.42"))])

    def test_invalid_operator_raises(self) -> None:
        rule = SimpleNamespace(basis_threshold=Decimal("0.25"), basis_threshold_operator="!=")
        with self.assertRaises(ValueError):
            evaluate_rule_basis_threshold(rule, [_tracker_row("Testville", Decimal("0.42"))])


class EvaluatorBasisWiringTests(unittest.TestCase):
    def test_evaluator_integration_basis_alert_created(self) -> None:
        """Rule with a basis threshold fires a basis alert; the price
        path (cash 4.10 vs threshold 5.00) does not fire."""
        rule = _rule(basis_threshold=Decimal("0.25"), basis_threshold_operator=">")
        result, session = _run([rule], [_snapshot_row()])
        self.assertEqual(result.created_alerts, 1)
        self.assertEqual(result.deduped_alerts, 0)
        self.assertEqual(result.evaluated_rules, 1)
        self.assertEqual(len(session.added), 1)
        message = session.added[0].message
        self.assertIn("basis > 0.25", message)
        self.assertIn("actual=0.42", message)
        self.assertIn("Testville", message)
        self.assertEqual(session.commits, 1)

    def test_evaluator_integration_price_only_rule_unaffected(self) -> None:
        """A rule with no basis threshold creates only its price alert
        — and creates nothing at all when the price does not trigger."""
        price_rule = _rule(threshold_value=Decimal("4.00"))
        result, session = _run([price_rule], [_snapshot_row()])
        self.assertEqual(result.created_alerts, 1)
        self.assertIn("cash_price_bu", session.added[0].message)
        self.assertNotIn("basis >", session.added[0].message)

        quiet_rule = _rule(threshold_value=Decimal("5.00"))
        result, session = _run([quiet_rule], [_snapshot_row()])
        self.assertEqual(result.created_alerts, 0)
        self.assertEqual(session.added, [])

    def test_evaluator_integration_no_cross_no_alert(self) -> None:
        rule = _rule(basis_threshold=Decimal("0.25"), basis_threshold_operator=">")
        result, session = _run([rule], [_snapshot_row(basis=Decimal("0.10"))])
        self.assertEqual(result.created_alerts, 0)
        self.assertEqual(session.added, [])

    def test_evaluator_integration_invalid_basis_threshold_skipped(self) -> None:
        """An invalid basis threshold must not fail the run, and the
        price path still fires."""
        rule = _rule(
            threshold_value=Decimal("4.00"),
            basis_threshold="not-a-number",
            basis_threshold_operator=">",
        )
        result, session = _run([rule], [_snapshot_row()])
        self.assertEqual(result.created_alerts, 1)
        self.assertIn("cash_price_bu", session.added[0].message)

    def test_evaluator_integration_basis_alert_deduped_on_second_run(self) -> None:
        rule = _rule(basis_threshold=Decimal("0.25"), basis_threshold_operator=">")
        snapshot = PriceSnapshot(
            id=SNAPSHOT_ID, source_id=SOURCE_ID, commodity_id=COMMODITY_ID
        )
        source = Source(id=SOURCE_ID, org_id=ORG_ID, name="Test Source")
        session = _FakeSession(
            snapshot=snapshot, source=source, rules=[rule], rows=[_snapshot_row()]
        )
        first = evaluate_alert_rules_for_snapshot(session, snapshot_id=SNAPSHOT_ID)
        self.assertEqual(first.created_alerts, 1)
        second = evaluate_alert_rules_for_snapshot(session, snapshot_id=SNAPSHOT_ID)
        self.assertEqual(second.created_alerts, 0)
        self.assertEqual(second.deduped_alerts, 1)
        self.assertEqual(len(session.added), 1)

    def test_evaluator_integration_basis_threshold_respects_location_scope(self) -> None:
        rule = _rule(
            location="Exampletown",
            basis_threshold=Decimal("0.25"),
            basis_threshold_operator=">",
        )
        result, session = _run([rule], [_snapshot_row(location="Testville")])
        self.assertEqual(result.created_alerts, 0)
        self.assertEqual(session.added, [])

    def test_evaluate_rule_basis_threshold_scopes_rows(self) -> None:
        """The evaluator-side helper applies location scope before the
        tracker conversion, and returns None for a threshold-less rule."""
        rule = _rule(basis_threshold=Decimal("0.25"), basis_threshold_operator=">")
        evaluation = _evaluate_rule_basis_threshold(
            rule,
            [_snapshot_row(location="Testville"), _snapshot_row(location="Exampletown")],
            None,
        )
        assert evaluation is not None
        self.assertEqual(evaluation.crossed_locations, ["Testville", "Exampletown"])

        scoped = _evaluate_rule_basis_threshold(
            _rule(location="Testville", basis_threshold=Decimal("0.25")),
            [_snapshot_row(location="Testville"), _snapshot_row(location="Exampletown")],
            None,
        )
        assert scoped is not None
        self.assertEqual(scoped.crossed_locations, ["Testville"])

        self.assertIsNone(_evaluate_rule_basis_threshold(_rule(), [_snapshot_row()], None))


if __name__ == "__main__":
    unittest.main()
