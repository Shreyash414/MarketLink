"""
Unit tests for Risk Assessment & Confidence Scoring.
"""
import unittest
import pandas as pd
from src.risk.risk_engine import RiskEngine


class TestRiskConfidenceEngine(unittest.TestCase):

    def setUp(self):
        self.risk_engine = RiskEngine(spike_threshold_pct=10.0)

    def test_normal_market_risk(self):
        # Stable prices with low volatility
        prices = pd.Series([2000, 2010, 2005, 2012, 2008, 2015, 2010])
        output = self.risk_engine.evaluate_risk_and_confidence(
            market="bareilly",
            current_price=2010.0,
            predicted_change=15.0,
            recent_series=prices
        )
        self.assertEqual(output.risk_level, "LOW")
        self.assertEqual(output.market_condition, "NORMAL")
        self.assertTrue(output.confidence_score >= 60.0)

    def test_spike_market_risk(self):
        # Sudden price jump > 10%
        prices = pd.Series([2000, 2010, 2005, 2008, 2010, 2015, 2400])  # ~19% jump
        output = self.risk_engine.evaluate_risk_and_confidence(
            market="bareilly",
            current_price=2400.0,
            predicted_change=50.0,
            recent_series=prices
        )
        self.assertEqual(output.risk_level, "HIGH")
        self.assertEqual(output.market_condition, "UNUSUAL_SPIKE")
        self.assertIn("volatility", output.warning_message.lower())

if __name__ == "__main__":
    unittest.main()
