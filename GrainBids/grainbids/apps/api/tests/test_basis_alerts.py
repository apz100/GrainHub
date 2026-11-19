"""Basis alert tests (Cycle 6).

Tests for :mod:`app.services.basis_alerts` — pure helpers that let an
alert rule trigger on basis moves, given a basis tracker response
shape (``GET /api/basis/tracker`` / ``rank_basis``) and a threshold.

No DB, no network, no sending. All locations are synthetic
(Testville / Exampletown / Sampleville); no real elevator is used.
"""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.basis_alerts import (  # noqa: E402
    detect_basis_crossing,
    find_basis_crossings,
)


def _row(location: str, basis, **extra):
    row = {"location": location, "commodity_name": "Corn", "basis": basis}
    row.update(extra)
    return row


class FindBasisCrossingsTests(unittest.TestCase):
    def test_threshold_cross_up(self) -> None:
        """Basis above the threshold with '>' crosses up."""
        result = find_basis_crossings(
            [_row("Testville", 0.42)],
            threshold=Decimal("0.25"),
            operator=">",
        )
        self.assertEqual(len(result.crossings), 1)
        crossing = result.crossings[0]
        self.assertEqual(crossing.location, "Testville")
        self.assertEqual(crossing.basis, Decimal("0.42"))
        self.assertEqual(crossing.direction, "up")
        self.assertEqual(crossing.operator, ">")
        self.assertEqual(result.evaluated, 1)
        self.assertEqual(result.skipped_missing, 0)
        self.assertEqual(result.crossed_locations, ["Testville"])

    def test_threshold_cross_down(self) -> None:
        """Basis below the threshold with '<' crosses down."""
        result = find_basis_crossings(
            [_row("Testville", -0.60)],
            threshold=Decimal("-0.25"),
            operator="<",
        )
        self.assertEqual(len(result.crossings), 1)
        self.assertEqual(result.crossings[0].direction, "down")
        self.assertEqual(result.crossings[0].basis, Decimal("-0.60"))

    def test_no_cross(self) -> None:
        """Basis on the non-triggering side produces no crossing."""
        above_rule = find_basis_crossings(
            [_row("Testville", 0.10)],
            threshold=Decimal("0.25"),
            operator=">",
        )
        self.assertEqual(above_rule.crossings, [])
        self.assertEqual(above_rule.evaluated, 1)
        self.assertEqual(above_rule.skipped_missing, 0)

        below_rule = find_basis_crossings(
            [_row("Testville", 0.10)],
            threshold=Decimal("-0.25"),
            operator="<",
        )
        self.assertEqual(below_rule.crossings, [])

    def test_missing_basis_skipped(self) -> None:
        """Rows with no computable basis never trigger; they are counted."""
        rows = [
            _row("Testville", None, missing_reason="missing_futures_price"),
            {"location": "Exampletown", "commodity_name": "Corn"},
            _row("Sampleville", "not-a-number"),
            _row("Testville", 0.50),
        ]
        result = find_basis_crossings(rows, threshold=Decimal("0.25"), operator=">")
        self.assertEqual(result.evaluated, 1)
        self.assertEqual(result.skipped_missing, 3)
        self.assertEqual(result.crossed_locations, ["Testville"])

    def test_empty_input(self) -> None:
        """Empty list, empty dict, and None all evaluate to zero crossings."""
        for empty in ([], {}, None, {"ranked": [], "unranked": []}):
            result = find_basis_crossings(empty, threshold=Decimal("0.25"))
            self.assertEqual(result.crossings, [])
            self.assertEqual(result.evaluated, 0)
            self.assertEqual(result.skipped_missing, 0)

    def test_multi_location(self) -> None:
        """Only the locations that cross are returned, in input order."""
        rows = [
            _row("Testville", 0.42, futures_month="Jul 2026"),
            _row("Exampletown", 0.10),
            _row("Sampleville", 0.55, source_status="healthy"),
            _row("Testville", -0.30),  # same town, other delivery: no cross
        ]
        result = find_basis_crossings(rows, threshold=Decimal("0.25"), operator=">")
        self.assertEqual(result.crossed_locations, ["Testville", "Sampleville"])
        self.assertEqual(result.evaluated, 4)
        self.assertEqual(result.crossings[0].futures_month, "Jul 2026")
        self.assertEqual(result.crossings[1].source_status, "healthy")

    def test_tracker_response_shape(self) -> None:
        """A rank_basis-style dict works; 'unranked' rows count as skipped."""
        response = {
            "ranked": [_row("Testville", 0.42), _row("Exampletown", 0.10)],
            "unranked": [
                _row("Sampleville", None, missing_reason="missing_cash_price")
            ],
            "row_count": 2,
            "unranked_count": 1,
        }
        result = find_basis_crossings(response, threshold=Decimal("0.25"))
        self.assertEqual(result.crossed_locations, ["Testville"])
        self.assertEqual(result.evaluated, 2)
        self.assertEqual(result.skipped_missing, 1)

    def test_inclusive_operators(self) -> None:
        """'>=' and '<=' trigger exactly at the threshold; '>' and '<' do not."""
        row = [_row("Testville", 0.25)]
        self.assertEqual(
            len(find_basis_crossings(row, threshold=Decimal("0.25"), operator=">=").crossings), 1
        )
        self.assertEqual(
            len(find_basis_crossings(row, threshold=Decimal("0.25"), operator=">").crossings), 0
        )
        self.assertEqual(
            len(find_basis_crossings(row, threshold=Decimal("0.25"), operator="<=").crossings), 1
        )
        self.assertEqual(
            len(find_basis_crossings(row, threshold=Decimal("0.25"), operator="<").crossings), 0
        )

    def test_invalid_operator_raises(self) -> None:
        with self.assertRaises(ValueError):
            find_basis_crossings([_row("Testville", 0.42)], threshold=0.25, operator="!=")
        with self.assertRaises(ValueError):
            find_basis_crossings([_row("Testville", 0.42)], threshold=0.25, operator="=")

    def test_location_falls_back_to_location_id(self) -> None:
        row = {"location": None, "location_id": "11111111-1111-1111-1111-111111111111", "basis": 0.50}
        result = find_basis_crossings([row], threshold=Decimal("0.25"))
        self.assertEqual(
            result.crossed_locations,
            ["location:11111111-1111-1111-1111-111111111111"],
        )


class DetectBasisCrossingTests(unittest.TestCase):
    def test_cross_up_between_readings(self) -> None:
        self.assertEqual(detect_basis_crossing(0.10, 0.40, Decimal("0.25")), "up")

    def test_cross_down_between_readings(self) -> None:
        self.assertEqual(detect_basis_crossing(0.10, -0.40, Decimal("-0.25")), "down")

    def test_no_cross_between_readings(self) -> None:
        self.assertIsNone(detect_basis_crossing(0.10, 0.20, Decimal("0.25")))
        self.assertIsNone(detect_basis_crossing(0.40, 0.50, Decimal("0.25")))
        self.assertIsNone(detect_basis_crossing(0.25, 0.25, Decimal("0.25")))

    def test_missing_reading_is_not_a_cross(self) -> None:
        self.assertIsNone(detect_basis_crossing(None, 0.40, Decimal("0.25")))
        self.assertIsNone(detect_basis_crossing(0.10, None, Decimal("0.25")))


if __name__ == "__main__":
    unittest.main()
