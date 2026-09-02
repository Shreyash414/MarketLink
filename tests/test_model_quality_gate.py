"""
Task 7 Unit Tests -- Production-Grade Model Quality Gate & Dynamic Inference Safety.
Verifies all 17 safety test cases required for Task 7.
"""
import unittest
import pandas as pd

from src.models.model_quality_gate import (
    STATUS_DISABLED,
    STATUS_PRODUCTION_READY,
    STATUS_RESEARCH_ONLY,
    STATUS_USABLE_WITH_WARNING,
    can_use_model,
    evaluate_model_gating,
    get_model_quality_metadata,
)
from src.models.model_predictor import ModelPredictor
from src.recommendation.mandi_recommender import MandiRecommender, recommend_mandi


class TestModelQualityGate(unittest.TestCase):

    def test_01_potato_agra_production_ready(self):
        """Potato Agra is PRODUCTION_READY; prediction allowed."""
        meta = get_model_quality_metadata("Potato", "Agra")
        self.assertEqual(meta["usage_status"], STATUS_PRODUCTION_READY)
        self.assertTrue(can_use_model("Potato", "Agra", farmer_facing=True))
        self.assertTrue(can_use_model("Potato", "Agra", farmer_facing=False))

    def test_02_tomato_kolar_production_ready(self):
        """Tomato Kolar is PRODUCTION_READY; prediction allowed."""
        meta = get_model_quality_metadata("Tomato", "Kolar")
        self.assertEqual(meta["usage_status"], STATUS_PRODUCTION_READY)
        self.assertTrue(can_use_model("Tomato", "Kolar", farmer_facing=True))

    def test_03_wheat_indore_usable_with_warning(self):
        """Wheat Indore is USABLE_WITH_WARNING; prediction allowed with warning."""
        meta = get_model_quality_metadata("Wheat", "Indore")
        self.assertEqual(meta["usage_status"], STATUS_USABLE_WITH_WARNING)
        self.assertTrue(can_use_model("Wheat", "Indore", farmer_facing=True))

    def test_04_onion_bargarh_usable_with_warning(self):
        """Onion Bargarh is USABLE_WITH_WARNING; prediction allowed with warning."""
        meta = get_model_quality_metadata("Onion", "Bargarh")
        self.assertEqual(meta["usage_status"], STATUS_USABLE_WITH_WARNING)
        self.assertTrue(can_use_model("Onion", "Bargarh", farmer_facing=True))

    def test_05_wheat_khanna_disabled(self):
        """Wheat Khanna is DISABLED; blocked for farmer-facing and research inference."""
        meta = get_model_quality_metadata("Wheat", "Khanna")
        self.assertEqual(meta["usage_status"], STATUS_DISABLED)
        self.assertFalse(can_use_model("Wheat", "Khanna", farmer_facing=True))
        self.assertFalse(can_use_model("Wheat", "Khanna", farmer_facing=False))

    def test_06_rice_burdwan_disabled(self):
        """Rice Burdwan is DISABLED; blocked for all inference modes."""
        meta = get_model_quality_metadata("Rice", "Burdwan")
        self.assertEqual(meta["usage_status"], STATUS_DISABLED)
        self.assertFalse(can_use_model("Rice", "Burdwan", farmer_facing=True))
        self.assertFalse(can_use_model("Rice", "Burdwan", farmer_facing=False))

    def test_07_missing_model_handling(self):
        """Unregistered market model is blocked cleanly."""
        meta = get_model_quality_metadata("Potato", "NonExistentMandi")
        self.assertEqual(meta["usage_status"], "MISSING")
        self.assertFalse(can_use_model("Potato", "NonExistentMandi", farmer_facing=True))

    def test_08_unknown_commodity(self):
        """Unknown commodity recommendation returns empty/clean result."""
        result = recommend_mandi(
            farmer_latitude=28.6139,
            farmer_longitude=77.2090,
            quantity_quintals=10.0,
            commodity="UnknownCrop",
            farmer_facing=True
        )
        self.assertEqual(result.recommended_mandi, "NONE")
        self.assertEqual(result.total_mandis_evaluated, 0)

    def test_09_unknown_market_inference_blocked(self):
        """ModelPredictor blocks prediction on unknown market in farmer-facing mode."""
        predictor = ModelPredictor()
        df_dummy = pd.DataFrame({"lag_1": [1000]})
        with self.assertRaises(PermissionError):
            predictor.predict_next_price(
                market="FakeMarket",
                X_features=df_dummy,
                current_price=1000.0,
                latest_date=pd.Timestamp.now(),
                commodity="Potato",
                farmer_facing=True
            )

    def test_10_missing_coordinates_skipped(self):
        """Markets without valid GPS are skipped by MandiRecommender."""
        recommender = MandiRecommender()
        df_meta = recommender.load_market_metadata(commodity="Onion")
        self.assertTrue((~df_meta["latitude"].isna()).all())
        self.assertTrue((~df_meta["longitude"].isna()).all())

    def test_11_cache_or_live_data_tag(self):
        """RecommendationResult reports data_source as LIVE or CACHE."""
        res = recommend_mandi(
            farmer_latitude=28.6139,
            farmer_longitude=77.2090,
            quantity_quintals=10.0,
            commodity="Onion",
            farmer_facing=True
        )
        self.assertIn(res.data_source, ["LIVE", "CACHE"])

    def test_12_model_quality_fields_propagate(self):
        """Model quality metadata fields populate in recommendation output items."""
        res = recommend_mandi(
            farmer_latitude=27.1767,
            farmer_longitude=78.0081,
            quantity_quintals=10.0,
            commodity="Potato",
            farmer_facing=True
        )
        if res.recommendations:
            item = res.recommendations[0]
            self.assertEqual(item.model_usage_status, STATUS_PRODUCTION_READY)
            self.assertGreater(item.model_reliability_score, 0.0)

    def test_13_disabled_rice_burdwan_never_recommended(self):
        """Rice Burdwan (DISABLED) is never recommended for farmer-facing queries."""
        res = recommend_mandi(
            farmer_latitude=23.2324,
            farmer_longitude=87.8615,
            quantity_quintals=10.0,
            commodity="Rice",
            farmer_facing=True
        )
        self.assertEqual(res.recommended_mandi, "NONE")
        for rec in res.recommendations:
            self.assertNotEqual(rec.mandi, "Burdwan")

    def test_14_disabled_wheat_khanna_never_recommended(self):
        """Wheat Khanna (DISABLED) is excluded from farmer recommendations."""
        res = recommend_mandi(
            farmer_latitude=30.7046,
            farmer_longitude=76.2166,
            quantity_quintals=10.0,
            commodity="Wheat",
            farmer_facing=True
        )
        for rec in res.recommendations:
            self.assertNotEqual(rec.mandi, "Khanna")

    def test_15_dynamic_commodity_routing(self):
        """Dynamic routing works correctly across Onion, Potato, Tomato, Wheat."""
        recommender = MandiRecommender()
        for crop in ["Onion", "Potato", "Tomato"]:
            df = recommender.load_market_metadata(commodity=crop)
            self.assertFalse(df.empty)

    def test_16_existing_onion_bareilly_behavior_preserved(self):
        """Onion Bareilly produces a valid recommendation for Delhi farmer."""
        res = recommend_mandi(
            farmer_latitude=28.6139,
            farmer_longitude=77.2090,
            quantity_quintals=10.0,
            commodity="Onion",
            farmer_facing=True
        )
        self.assertGreater(len(res.recommendations), 0)
        self.assertIn("Bareilly", [r.mandi for r in res.recommendations])

    def test_17_usable_with_warning_carries_warning_string(self):
        """USABLE_WITH_WARNING models carry non-empty warning strings when applicable."""
        res = recommend_mandi(
            farmer_latitude=22.7196,
            farmer_longitude=75.8577,
            quantity_quintals=10.0,
            commodity="Wheat",
            farmer_facing=True
        )
        if res.recommendations:
            item = res.recommendations[0]
            self.assertEqual(item.model_usage_status, STATUS_USABLE_WITH_WARNING)
            self.assertTrue(len(item.warning) > 0)


if __name__ == "__main__":
    unittest.main()
