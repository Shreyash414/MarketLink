"""
Integration tests for multi-commodity recommendation and graceful handling of untrained commodities.
"""
import unittest
from src.recommendation.mandi_recommender import MandiRecommender, recommend_mandi


class TestMultiCommodityInference(unittest.TestCase):

    def setUp(self):
        self.recommender = MandiRecommender()

    def test_onion_pipeline_preserved(self):
        # Must produce exact same validated recommendation for Onion
        result = self.recommender.recommend(
            farmer_latitude=28.6139,
            farmer_longitude=77.2090,
            quantity_quintals=10.0,
            commodity="Onion"
        )
        self.assertEqual(result.commodity, "Onion")
        self.assertTrue(result.total_mandis_evaluated > 0)
        self.assertEqual(result.recommended_mandi, "Bareilly")
        top_rec = result.recommendations[0]
        self.assertEqual(top_rec.rank, 1)
        self.assertEqual(top_rec.recommendation_label, "RECOMMENDED")
        self.assertTrue(top_rec.net_return > 0)

    def test_untrained_commodity_graceful_handling(self):
        # Querying an untrained commodity like Garlic should return empty recommendations without crashing
        result = self.recommender.recommend(
            farmer_latitude=28.6139,
            farmer_longitude=77.2090,
            quantity_quintals=10.0,
            commodity="Dragonfruit"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.commodity, "Dragonfruit")
        self.assertEqual(result.recommended_mandi, "NONE")
        self.assertEqual(len(result.recommendations), 0)

    def test_metadata_filtering_by_commodity(self):
        meta_onion = self.recommender.load_market_metadata(commodity="Onion")
        self.assertTrue(all(meta_onion["commodity"].str.lower() == "onion"))
        self.assertIn("Bareilly", meta_onion["market"].tolist())

        meta_potato = self.recommender.load_market_metadata(commodity="Potato")
        self.assertTrue(all(meta_potato["commodity"].str.lower() == "potato"))
        self.assertIn("Agra", meta_potato["market"].tolist())


if __name__ == "__main__":
    unittest.main()
