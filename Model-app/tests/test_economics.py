"""
Unit tests for economic calculations (transport, market fee, gross revenue, net return).
"""
import unittest
from src.economics.economics_engine import (
    calculate_economics,
    calculate_market_fee,
    calculate_transport_cost,
)


class TestEconomicsEngine(unittest.TestCase):

    def test_transport_cost(self):
        # 100 km, 10 quintals, tariff ₹3 / quintal / km -> 100 * 10 * 3 = ₹3000
        cost = calculate_transport_cost(100.0, 10.0, 3.0)
        self.assertEqual(cost, 3000.0)

    def test_market_fee(self):
        # 10 quintals, ₹20 / quintal fee -> 10 * 20 = ₹200
        fee = calculate_market_fee(10.0, 20.0)
        self.assertEqual(fee, 200.0)

    def test_full_economics(self):
        # distance=100km, quantity=10q, predicted_price=2500/q, transport_rate=3, fee_rate=20
        # gross = 2500 * 10 = 25,000
        # transport = 100 * 10 * 3 = 3,000
        # fee = 10 * 20 = 200
        # total_cost = 3200
        # net_return = 25,000 - 3200 = 21,800
        # net_price_per_quintal = 21,800 / 10 = 2180
        econ = calculate_economics(
            distance_km=100.0,
            quantity_quintals=10.0,
            predicted_price=2500.0,
            transport_rate=3.0,
            market_fee_rate=20.0
        )
        self.assertEqual(econ.gross_revenue, 25000.0)
        self.assertEqual(econ.transport_cost, 3000.0)
        self.assertEqual(econ.market_fee, 200.0)
        self.assertEqual(econ.total_cost, 3200.0)
        self.assertEqual(econ.net_return, 21800.0)
        self.assertEqual(econ.net_price_per_quintal, 2180.0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_transport_cost(-10.0, 10.0, 3.0)
        with self.assertRaises(ValueError):
            calculate_market_fee(0.0, 20.0)

if __name__ == "__main__":
    unittest.main()
