"""
Unit tests for Ollama Client, Intent Parser, and Recommendation Explainer.
"""
import unittest
from src.ai.intent_parser import FarmerIntentParser
from src.ai.recommendation_explainer import RecommendationExplainer
from src.recommendation.schemas import MandiRecommendationItem, RecommendationResult


class TestOllamaAndExplainer(unittest.TestCase):

    def setUp(self):
        self.parser = FarmerIntentParser()
        self.explainer = RecommendationExplainer()

    def test_intent_parser_potato_extraction(self):
        query = "I want to sell 15 quintal potato in Agra"
        parsed = self.parser.parse(query)
        self.assertEqual(parsed.commodity, "Potato")
        self.assertEqual(parsed.quantity_quintals, 15.0)
        self.assertEqual(parsed.location_name, "Agra")

    def test_intent_parser_wheat_extraction(self):
        query = "Selling 500 kg wheat in Khanna"
        parsed = self.parser.parse(query)
        self.assertEqual(parsed.commodity, "Wheat")
        self.assertEqual(parsed.quantity_quintals, 5.0)
        self.assertEqual(parsed.location_name, "Khanna")

    def test_explainer_contains_exact_numbers(self):
        top_item = MandiRecommendationItem(
            rank=1, mandi="Bareilly", state="Uttar Pradesh", district="Bareilly",
            distance_km=219.4, current_price=1330.0, predicted_price=1331.0,
            expected_change=1.0, expected_change_pct=0.08, expected_direction="STABLE",
            transport_cost=6583.2, market_fee=200.0, gross_revenue=13310.0,
            total_cost=6783.2, net_return=6526.8, net_price_per_quintal=652.68,
            risk_level="LOW", confidence_score=85.0, market_condition="NORMAL",
            recommendation_label="RECOMMENDED", reason="Top return", warning="",
            lower_bound_80=1280.0, upper_bound_80=1380.0
        )
        rec_result = RecommendationResult(
            commodity="Onion", farmer_latitude=28.6139, farmer_longitude=77.2090,
            quantity_quintals=10.0, recommended_mandi="Bareilly", total_mandis_evaluated=1,
            data_source="CACHE", recommendations=[top_item]
        )

        explanation = self.explainer.explain(rec_result, language="English")
        self.assertIn("Bareilly", explanation)
        self.assertIn("6,526.80", explanation)
        self.assertIn("1331.00", explanation)
        self.assertIn("85.0", explanation)

    def test_explainer_hindi_output(self):
        top_item = MandiRecommendationItem(
            rank=1, mandi="Bareilly", state="UP", district="Bareilly",
            distance_km=200.0, current_price=1300.0, predicted_price=1320.0,
            expected_change=20.0, expected_change_pct=1.54, expected_direction="UP",
            transport_cost=6000.0, market_fee=200.0, gross_revenue=13200.0,
            total_cost=6200.0, net_return=7000.0, net_price_per_quintal=700.0,
            risk_level="LOW", confidence_score=90.0, market_condition="NORMAL",
            recommendation_label="RECOMMENDED", reason="Top return", warning="",
            lower_bound_80=1270.0, upper_bound_80=1370.0
        )
        rec_result = RecommendationResult(
            commodity="Potato", farmer_latitude=27.18, farmer_longitude=78.02,
            quantity_quintals=10.0, recommended_mandi="Bareilly", total_mandis_evaluated=1,
            data_source="CACHE", recommendations=[top_item]
        )

        hindi_text = self.explainer.explain(rec_result, language="Hindi")
        self.assertIn("सर्वश्रेष्ठ मंडी", hindi_text)
        self.assertIn("₹7,000.00", hindi_text)


if __name__ == "__main__":
    unittest.main()
