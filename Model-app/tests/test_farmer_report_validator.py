"""
Unit tests for Farmer Report Validator & Anomaly Detection.
"""
import unittest
from pathlib import Path

from src.intelligence.farmer_report_validator import FarmerReport, FarmerReportValidator


class TestFarmerReportValidator(unittest.TestCase):

    def setUp(self):
        self.validator = FarmerReportValidator(
            max_allowed_deviation_pct=50.0,
            max_report_age_days=7,
            min_plausible_price=100.0,
            max_plausible_price=20000.0
        )

    def test_clean_report_accepted(self):
        rep = FarmerReport("R1", "F1", "Onion", "Bareilly", 1350.0, "2026-09-01", 10.0)
        res = self.validator.validate_report(rep)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.status, "ACCEPTED")
        self.assertGreaterEqual(res.trust_score, 70.0)

    def test_negative_price_rejected(self):
        rep = FarmerReport("R2", "F2", "Onion", "Bareilly", -100.0, "2026-09-01")
        res = self.validator.validate_report(rep)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "REJECTED")

    def test_stale_report_rejected(self):
        rep = FarmerReport("R3", "F3", "Onion", "Bareilly", 1350.0, "2020-01-01")
        res = self.validator.validate_report(rep)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "REJECTED")
        self.assertIn("stale", res.rejection_reason.lower())

    def test_extreme_price_spike_flagged(self):
        rep = FarmerReport("R4", "F4", "Onion", "Bareilly", 6000.0, "2026-09-01")
        res = self.validator.validate_report(rep)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "FLAGGED_SUSPICIOUS")
        self.assertLess(res.trust_score, 50.0)


if __name__ == "__main__":
    unittest.main()
