"""
End-to-End Integration Tests for Production Recommendation Pipeline.
"""
import unittest
import pandas as pd
from src.recommendation.mandi_recommender import recommend_mandi


class TestInferencePipeline(unittest.TestCase):

    def test_end_to_end_recommendation(self):
        # Farmer near Delhi selling 10 quintals of Onion
        result = recommend_mandi(
            farmer_latitude=28.6139,
            farmer_longitude=77.2090,
            quantity_quintals=10.0,
            commodity="Onion"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.commodity, "Onion")
        self.assertTrue(result.total_mandis_evaluated > 0)
        self.assertIn(result.data_source, ["LIVE", "CACHE"])
        self.assertTrue(len(result.recommendations) > 0)

        # Check ranking integrity
        top_rec = result.recommendations[0]
        self.assertEqual(top_rec.rank, 1)
        self.assertEqual(top_rec.recommendation_label, "RECOMMENDED")
        self.assertEqual(top_rec.mandi, result.recommended_mandi)
        self.assertTrue(top_rec.net_return > 0)

        # Check sorting by net return
        if len(result.recommendations) > 1:
            second_rec = result.recommendations[1]
            self.assertTrue(top_rec.net_return >= second_rec.net_return)

if __name__ == "__main__":
    unittest.main()
