"""Tests for the pure email-bid parser (no Outlook, no Tesseract, no DB).

All fixtures are synthetic and use a neutral test location/company
("Testville" / "Test Elevator Co."); no real sender's bid data is used.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.email_bid_parser import (  # noqa: E402
    bu_per_mt,
    convert_cash_price,
    convert_currency,
    detect_sender_company,
    month_to_key,
    normalize_commodity,
    normalize_delivery_month,
    normalize_futures_month,
    ocr_image_to_text,
    parse_email_bid_text,
    parse_ocr_bid_rows,
    usd_basis_from_cad_cash,
)


class DeliveryMonthTests(unittest.TestCase):
    def test_month_names_and_abbreviations(self) -> None:
        self.assertEqual(normalize_delivery_month("Nov 2026"), "Nov 2026")
        self.assertEqual(normalize_delivery_month("November 2026"), "Nov 2026")
        self.assertEqual(normalize_delivery_month("Nov-26"), "Nov 2026")
        self.assertEqual(normalize_delivery_month("Nov 26"), "Nov 2026")
        self.assertEqual(normalize_delivery_month("Dec26"), "Dec 2026")
        self.assertEqual(normalize_delivery_month("26-Nov"), "Nov 2026")

    def test_harvest_years(self) -> None:
        self.assertEqual(normalize_delivery_month("Harvest 2026"), "Harvest 2026")
        self.assertEqual(normalize_delivery_month("Harvest 2027"), "Harvest 2027")
        self.assertEqual(normalize_delivery_month("Harvest-26"), "Harvest 2026")
        self.assertEqual(normalize_delivery_month("Récoltes/Harvest 2026"), "Harvest 2026")

    def test_spot_and_ranges(self) -> None:
        self.assertEqual(normalize_delivery_month("Spot"), "Spot")
        self.assertEqual(normalize_delivery_month("Nov-Dec 2026"), "Nov-Dec 2026")

    def test_unparseable_returns_none(self) -> None:
        self.assertIsNone(normalize_delivery_month(""))
        self.assertIsNone(normalize_delivery_month("sometime soon"))

    def test_month_to_key(self) -> None:
        self.assertEqual(month_to_key("Nov 2026"), "2026-11")
        self.assertEqual(month_to_key("Harvest 2026"), "2026-harvest")
        self.assertEqual(month_to_key("Spot"), "spot")


class NormalizeHelperTests(unittest.TestCase):
    def test_commodity_aliases(self) -> None:
        self.assertEqual(normalize_commodity("corn"), "Corn")
        self.assertEqual(normalize_commodity("Soybeans"), "Soybeans")
        self.assertEqual(normalize_commodity("soy"), "Soybeans")
        self.assertEqual(normalize_commodity("Wheat - SRW"), "SRW Wheat")
        self.assertEqual(normalize_commodity("canola"), "Canola")
        self.assertIsNone(normalize_commodity("quinoa"))
        self.assertIsNone(normalize_commodity(""))

    def test_futures_month_codes(self) -> None:
        self.assertEqual(normalize_futures_month("CH27"), "March 2027")
        self.assertEqual(normalize_futures_month("SX26"), "November 2026")
        self.assertEqual(normalize_futures_month("WN26"), "July 2026")
        self.assertIsNone(normalize_futures_month("not-a-code"))

    def test_mt_vs_bu_conversion(self) -> None:
        # $250/MT corn -> $/bu using the legacy 39.3683 factor.
        self.assertAlmostEqual(convert_cash_price(250.00, "mt", "bu", "Corn"), 6.35, places=2)
        self.assertAlmostEqual(convert_cash_price(550.00, "mt", "bu", "Soybeans"), 14.97, places=2)
        self.assertAlmostEqual(convert_cash_price(6.35, "bu", "mt", "Corn"), 250.00, places=1)
        self.assertEqual(bu_per_mt("Corn"), 39.3683)
        self.assertEqual(bu_per_mt("Soybeans"), 36.7437)

    def test_cad_vs_usd_conversion_needs_fx_rate(self) -> None:
        # fx_rate is CAD per USD (Bank of Canada FXUSDCAD convention).
        self.assertAlmostEqual(convert_currency(10.00, "USD", "CAD", 1.40), 14.00)
        self.assertAlmostEqual(convert_currency(14.00, "CAD", "USD", 1.40), 10.00)
        # No rate supplied: never guess one.
        self.assertIsNone(convert_currency(10.00, "USD", "CAD", None))

    def test_usd_basis_from_cad_cash(self) -> None:
        self.assertAlmostEqual(
            usd_basis_from_cad_cash(6.45 * 1.40, 4.50, 1.40), 1.95, places=2
        )
        # Outside the trusted +/-2.00 USD/bu range: blank, not stored.
        self.assertIsNone(usd_basis_from_cad_cash(6.45 * 1.40, 1.00, 1.40))
        self.assertIsNone(usd_basis_from_cad_cash(6.45, 4.50, None))


class PlainTextTableTests(unittest.TestCase):
    def test_andersons_style_table_parse(self) -> None:
        body = """Andersons Producer Commodity Bid Sheet
Corn
Testville
Nov 26 CH27 4.5025 -0.25 6.45 253.90
Dec 26 CH27 4.5500 -0.20 6.50 255.90
Soybeans
Testville
Nov 26 SX26 10.2500 -0.60 14.20 521.80
"""
        result = parse_email_bid_text(
            "bids@andersons.com", "Producer Commodity Bid Sheet", body
        )
        self.assertEqual(result.company, "Andersons")
        self.assertEqual(len(result.valid_rows), 3)
        self.assertEqual(len(result.rejected_rows), 0)
        corn = result.valid_rows[0]
        self.assertEqual(corn.commodity, "Corn")
        self.assertEqual(corn.delivery_month, "Nov 2026")
        self.assertEqual(corn.futures_month, "March 2027")
        self.assertAlmostEqual(corn.cash_price, 6.45)
        self.assertEqual(corn.cash_price_unit, "bu")
        self.assertEqual(corn.currency, "CAD")
        self.assertAlmostEqual(corn.basis, -0.25)
        self.assertEqual(corn.location, "Testville")
        soy = result.valid_rows[2]
        self.assertEqual(soy.commodity, "Soybeans")
        self.assertAlmostEqual(soy.cash_price, 14.20)

    def test_generic_text_table_with_unit_hints(self) -> None:
        body = """Test Elevator Co. Daily Bids
Corn Nov 2026 $6.45/bu
Soybeans Harvest 2026 $14.20/bu
Wheat Dec 2026 $7.10/bu
"""
        result = parse_email_bid_text("", "Daily bids", body)
        self.assertEqual(len(result.valid_rows), 3)
        self.assertEqual(result.valid_rows[1].delivery_month, "Harvest 2026")
        self.assertEqual(result.valid_rows[1].commodity, "Soybeans")

    def test_incomplete_row_rejected_not_invented(self) -> None:
        body = """Test Elevator Co. Daily Bids
Corn Nov 2026 $6.45/bu
Soybeans Dec 2026
Wheat Jan 2027 $7.10/bu
"""
        result = parse_email_bid_text("", "Daily bids", body)
        self.assertEqual(len(result.valid_rows), 2)
        self.assertEqual(len(result.rejected_rows), 1)
        rejected = result.rejected_rows[0]
        self.assertEqual(rejected.status, "incomplete")
        self.assertIn("price", rejected.reason)
        self.assertIn("Soybeans", rejected.raw_text)

    def test_unknown_commodity_rejected(self) -> None:
        body = """Test Elevator Co. Daily Bids
Quinoa Nov 2026 $5.00/bu
Corn Nov 2026 $6.45/bu
"""
        result = parse_email_bid_text("", "Daily bids", body)
        self.assertEqual(len(result.valid_rows), 1)
        self.assertEqual(len(result.rejected_rows), 1)
        self.assertEqual(result.rejected_rows[0].reason, "unknown commodity")

    def test_empty_body(self) -> None:
        for body in ("", "   \n\n  ", "No bids today, check back tomorrow."):
            result = parse_email_bid_text("", "Daily bids", body)
            self.assertEqual(result.valid_rows, [])
            self.assertEqual(result.rejected_rows, [])

    def test_html_body_is_flattened(self) -> None:
        body = (
            "<html><body><table><tr><td>Corn</td><td>Nov 2026</td>"
            "<td>$6.45/bu</td></tr></table></body></html>"
        )
        result = parse_email_bid_text("", "Daily bids", body)
        self.assertEqual(len(result.valid_rows), 1)
        self.assertEqual(result.valid_rows[0].commodity, "Corn")


class SenderQuirkTests(unittest.TestCase):
    def test_sender_detection(self) -> None:
        self.assertEqual(
            detect_sender_company("jose.borunda@bunge.com", "Bunge BIDS MTL/BCC"), "Bunge"
        )
        self.assertEqual(
            detect_sender_company("Dylan Stewart", "BroadGrain bid sheet"), "BroadGrain"
        )
        self.assertEqual(
            detect_sender_company("Andrea Baron Mancera", "Richardson prices"), "Richardson"
        )
        self.assertEqual(
            detect_sender_company("Richard Kricsfalusy", "P&H bids"), "P&H"
        )
        self.assertEqual(
            detect_sender_company("", "MacEwen Morning Report"), "MacEwen"
        )
        self.assertEqual(detect_sender_company("", "Random newsletter"), "Unknown")

    def test_bunge_basis_only_rows_are_valid(self) -> None:
        body = """Soybeans BCC
Nov-26: +0.45 CH27
Dec-26: -0.12 CZ26
Soybeans MTL
Nov-26: +0.30 SX26
Corn MTL
Dec-26: +0.15 CZ26
"""
        result = parse_email_bid_text(
            "jose.borunda@bunge.com", "Bunge BIDS MTL/BCC", body
        )
        self.assertEqual(result.company, "Bunge")
        self.assertEqual(len(result.valid_rows), 4)
        self.assertEqual(len(result.rejected_rows), 0)
        first = result.valid_rows[0]
        self.assertEqual(first.commodity, "Soybeans")
        self.assertEqual(first.delivery_month, "Nov 2026")
        self.assertIsNone(first.cash_price)  # Bunge quotes basis, not cash.
        self.assertAlmostEqual(first.basis, 0.45)
        self.assertEqual(first.basis_currency, "USD")
        self.assertAlmostEqual(first.us_basis_usd_per_bu, 0.45)
        self.assertEqual(first.location, "Bunge BCC")

    def test_bunge_us_basis_out_of_range_rejected(self) -> None:
        body = "Soybeans BCC\nNov-26: +2.50 CH27\nDec-26: +0.40 CZ26\n"
        result = parse_email_bid_text("jose.borunda@bunge.com", "Bunge bids", body)
        self.assertEqual(len(result.valid_rows), 1)
        self.assertEqual(len(result.rejected_rows), 1)
        self.assertIn("2.00", result.rejected_rows[0].reason)

    def test_macewen_mt_only_prices(self) -> None:
        body = """MacEwen Morning Report
Corn
Maxville Cobden
Nov 2026 245.00 248.00
Harvest 2026 230.00 232.00
"""
        result = parse_email_bid_text("", "MacEwen Morning Report", body)
        self.assertEqual(result.company, "MacEwen")
        self.assertEqual(len(result.valid_rows), 4)
        first = result.valid_rows[0]
        self.assertEqual(first.commodity, "Corn")
        self.assertEqual(first.cash_price_unit, "mt")
        self.assertAlmostEqual(first.cash_price, 245.00)
        self.assertAlmostEqual(first.cash_price_cad_per_bu, 6.22, places=2)
        self.assertIsNone(first.futures_price)  # MacEwen supplies no futures.
        self.assertIsNone(first.us_basis_usd_per_bu)
        self.assertEqual(first.location, "MacEwen Maxville")


class OcrTests(unittest.TestCase):
    def test_ocr_noisy_text_parse(self) -> None:
        ocr = """BroadGrain Bid Sheet   Del Testville
Corn
Nov-26   -0.25   4.5025   CH27   $6.45   $253.90
Dec-26   -0.20   4.5500   CH27   $6.50   $255.90
Soybeans
Nov-26   -0.60   10.2500   SX26   $14.20   $521.80
"""
        result = parse_ocr_bid_rows(ocr, company="BroadGrain")
        self.assertEqual(len(result.valid_rows), 3)
        self.assertEqual(len(result.rejected_rows), 0)
        self.assertEqual(result.valid_rows[0].source, "ocr")
        self.assertEqual(result.valid_rows[0].delivery_month, "Nov 2026")
        self.assertAlmostEqual(result.valid_rows[0].cash_price_cad_per_mt, 253.90)

    def test_ocr_misread_digit_flagged_not_corrected(self) -> None:
        ocr = "Corn\nNov-26 -0.25 4.5025 CH27 $6.45 $253.9O\n"
        result = parse_ocr_bid_rows(ocr, company="BroadGrain")
        self.assertEqual(len(result.valid_rows), 1)
        row = result.valid_rows[0]
        self.assertLess(row.confidence, 1.0)
        self.assertTrue(any("misread" in note for note in row.notes))
        self.assertIn("253.9O", row.notes[0])

    def test_ocr_extra_spaces_and_artefacts(self) -> None:
        ocr = "Corn\nNov-26  |  -0.25   4.5025   CH27   $6.45   $253.90\n"
        result = parse_ocr_bid_rows(ocr, company="BroadGrain")
        self.assertEqual(len(result.valid_rows), 1)
        self.assertLess(result.valid_rows[0].confidence, 1.0)

    def test_malformed_ocr_text(self) -> None:
        ocr = "asdf qwer zxcv\n!@#$ %^&*\nTABLE TABLE TABLE\n"
        result = parse_ocr_bid_rows(ocr, company="BroadGrain")
        self.assertEqual(result.valid_rows, [])
        self.assertEqual(result.rejected_rows, [])

    def test_broadgrain_wheat_srw_inferred_from_contract(self) -> None:
        # Legacy quirk: OCR can miss the "Wheat - SRW" heading; a W-series
        # contract is enough to retain the row as SRW Wheat.
        ocr = "Nov-26 -0.10 5.7500 WN26 $6.10 $224.15\n"
        result = parse_ocr_bid_rows(ocr, company="BroadGrain")
        self.assertEqual(len(result.valid_rows), 1)
        self.assertEqual(result.valid_rows[0].commodity, "SRW Wheat")

    def test_pandh_value_error_rows_skipped(self) -> None:
        ocr = (
            "Prescott\n"
            "26-Nov 10.2500 SX26 -20.50 1.4000 CAZ26 -0.60 14.20 521.80 +0.45\n"
            "26-Dec #VALUE! SX26 -20.50 1.4000 CAZ26 -0.60 14.20 521.80 +0.45\n"
        )
        result = parse_ocr_bid_rows(ocr, company="P&H")
        self.assertEqual(len(result.valid_rows), 1)
        self.assertEqual(result.valid_rows[0].delivery_month, "Nov 2026")

    def test_ocr_image_helper_fails_clearly_without_tesseract(self) -> None:
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            with self.assertRaises(RuntimeError) as ctx:
                ocr_image_to_text("/tmp/does-not-exist.png")
            self.assertIn("Tesseract", str(ctx.exception))
        else:
            self.skipTest("pytesseract is installed in this environment")


class CurrencyAndFxTests(unittest.TestCase):
    def test_usd_price_converted_with_fx_rate(self) -> None:
        body = "Corn Nov 2026 $6.45/bu USD\n"
        result = parse_email_bid_text("", "Daily bids", body, fx_rate=1.40)
        self.assertEqual(len(result.valid_rows), 1)
        row = result.valid_rows[0]
        self.assertEqual(row.currency, "USD")
        self.assertAlmostEqual(row.cash_price_cad_per_bu, 9.03)
        self.assertAlmostEqual(row.cash_price_usd_per_bu, 6.45)

    def test_usd_price_without_fx_rate_leaves_conversions_blank(self) -> None:
        body = "Corn Nov 2026 $6.45/bu USD\n"
        result = parse_email_bid_text("", "Daily bids", body)
        row = result.valid_rows[0]
        self.assertEqual(row.currency, "USD")
        self.assertIsNone(row.cash_price_cad_per_bu)
        self.assertIsNone(row.cash_price_usd_per_bu)

    def test_mt_price_with_fx_rate(self) -> None:
        body = "Soybeans Harvest 2026 $521.80/MT USD\n"
        result = parse_email_bid_text("", "Daily bids", body, fx_rate=1.40)
        row = result.valid_rows[0]
        self.assertEqual(row.cash_price_unit, "mt")
        self.assertAlmostEqual(row.cash_price_cad_per_mt, 730.52)
        self.assertAlmostEqual(row.cash_price_cad_per_bu, 19.88, places=2)


class ParseResultTests(unittest.TestCase):
    def test_parse_success_rate(self) -> None:
        body = "Corn Nov 2026 $6.45/bu\nSoybeans Dec 2026\n"
        result = parse_email_bid_text("", "Daily bids", body)
        self.assertEqual(result.total_rows, 2)
        self.assertAlmostEqual(result.parse_success_rate, 0.5)

    def test_row_dict_round_trip(self) -> None:
        body = "Corn Nov 2026 $6.45/bu\n"
        row = parse_email_bid_text("", "Daily bids", body).valid_rows[0]
        data = row.to_dict()
        self.assertEqual(data["commodity"], "Corn")
        self.assertEqual(data["delivery_key"], "2026-11")
        self.assertEqual(data["source"], "text")


if __name__ == "__main__":
    unittest.main()
