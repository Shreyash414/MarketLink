"""
Unit tests for statistical prediction intervals in Risk Engine.
"""
import unittest
import pandas as pd
from src.risk.risk_engine import RiskEngine


class TestConfidenceIntervals(unittest.TestCase):

    def setUp(self):
        self.risk_engine = RiskEngine()

    def test_interval_ordering(self):
        series = pd.Series([1300, 1310, 1305, 1320, 1315, 1330, 1330])
        out = self.risk_engine.evaluate_risk_and_confidence(
            market="Bareilly",
            current_price=1330.0,
            predicted_change=10.0,
            recent_series=series,
            commodity="Onion"
        )
        pred_price = 1330.0 + 10.0
        # Check lower <= pred <= upper
        self.assertLessEqual(out.lower_bound_80, pred_price)
        self.assertGreaterEqual(out.upper_bound_80, pred_price)
        self.assertLessEqual(out.lower_bound_95, out.lower_bound_80)
        self.assertGreaterEqual(out.upper_bound_95, out.upper_bound_80)

    def test_higher_volatility_widens_intervals(self):
        stable_series = pd.Series([1330, 1330, 1330, 1330, 1330, 1330, 1330])
        volatile_series = pd.Series([1100, 1500, 1200, 1600, 1150, 1550, 1330])

        out_stable = self.risk_engine.evaluate_risk_and_confidence(
            market="Bareilly", current_price=1330.0, predicted_change=0.0, recent_series=stable_series
        )
        out_volatile = self.risk_engine.evaluate_risk_and_confidence(
            market="Bareilly", current_price=1330.0, predicted_change=0.0, recent_series=volatile_series
        )

        margin_stable = out_stable.upper_bound_80 - out_stable.lower_bound_80
        margin_volatile = out_volatile.upper_bound_80 - out_volatile.lower_bound_80
        self.assertGreater(margin_volatile, margin_stable)


if __name__ == "__main__":
    unittest.main()
