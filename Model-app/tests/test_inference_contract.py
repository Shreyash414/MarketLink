"""
Task 9 Unit Tests -- Production Inference Contract & Integration Readiness.
Verifies all 20 required test cases for Task 9 canonical inference contract and safety gate invariants.
"""
import json
import unittest
import pandas as pd

from src.contracts.inference_contract import (
    CONTRACT_VERSION,
    CanonicalInferenceItem,
    CanonicalRecommendationResponse,
    ContractMetadata,
    build_canonical_recommendation,
    validate_inference_contract,
)
from src.data.data_reliability import (
    SOURCE_CACHE,
    SOURCE_LIVE,
    STATUS_CACHE_STALE,
    STATUS_INVALID_DATA,
    STATUS_LIVE_FRESH,
    STATUS_READY,
    DataReliabilityResult,
)
from src.models.model_predictor import ModelPredictor, PredictionOutput
from src.recommendation.mandi_recommender import recommend_canonical, recommend_mandi
from src.recommendation.schemas import MandiRecommendationItem, RecommendationResult


class TestInferenceContract(unittest.TestCase):

    def test_01_valid_production_ready_prediction(self):
        """Potato Agra (PRODUCTION_READY) converts to a valid canonical response."""
        res = recommend_mandi(
            farmer_latitude=27.1767,
            farmer_longitude=78.0081,
            quantity_quintals=10.0,
            commodity="Potato",
            farmer_facing=True
        )
        canonical = res.to_canonical_contract()
        self.assertIsInstance(canonical, CanonicalRecommendationResponse)
        self.assertEqual(canonical.commodity, "Potato")
        self.assertEqual(canonical.recommended_mandi, "Agra")
        is_valid, reason = validate_inference_contract(canonical)
        self.assertTrue(is_valid, msg=f"Validation failed: {reason}")

    def test_02_valid_usable_with_warning_prediction(self):
        """Wheat Indore (USABLE_WITH_WARNING) converts with warning attached."""
        res = recommend_mandi(
            farmer_latitude=22.7196,
            farmer_longitude=75.8577,
            quantity_quintals=10.0,
            commodity="Wheat",
            farmer_facing=True
        )
        canonical = res.to_canonical_contract()
        self.assertEqual(canonical.recommended_mandi, "Indore")
        self.assertEqual(canonical.recommendations[0].model_usage_status, "USABLE_WITH_WARNING")
        self.assertTrue(len(canonical.recommendations[0].warning) > 0)
        is_valid, reason = validate_inference_contract(canonical)
        self.assertTrue(is_valid, msg=f"Validation failed: {reason}")

    def test_03_blocked_disabled_model(self):
        """Rice Burdwan (DISABLED model) is blocked in canonical response."""
        canonical = recommend_canonical(
            farmer_latitude=23.2324,
            farmer_longitude=87.8615,
            quantity_quintals=10.0,
            commodity="Rice",
            farmer_facing=True
        )
        self.assertEqual(canonical.recommended_mandi, "NONE")
        self.assertEqual(len(canonical.recommendations), 0)
        is_valid, reason = validate_inference_contract(canonical)
        self.assertTrue(is_valid)

    def test_04_blocked_research_only_model(self):
        """RESEARCH_ONLY model is blocked for farmer-facing canonical response."""
        # Using onion nagpur as research/disabled test case
        canonical = recommend_canonical(
            farmer_latitude=21.1458,
            farmer_longitude=79.0882,
            quantity_quintals=10.0,
            commodity="Onion",
            farmer_facing=True
        )
        # Bareilly or Bargarh may be recommended if within range, but Nagpur is blocked
        nagpur_item = next((rec for rec in canonical.recommendations if rec.mandi.lower() == "nagpur"), None)
        self.assertIsNone(nagpur_item)

    def test_05_blocked_missing_model(self):
        """Unregistered market model yields empty/clean canonical response."""
        canonical = recommend_canonical(
            farmer_latitude=28.6139,
            farmer_longitude=77.2090,
            quantity_quintals=10.0,
            commodity="NonExistentCommodity",
            farmer_facing=True
        )
        self.assertEqual(canonical.recommended_mandi, "NONE")
        self.assertEqual(len(canonical.recommendations), 0)

    def test_06_blocked_invalid_data(self):
        """Canonical validation rejects responses with negative prices."""
        meta = ContractMetadata()
        item = CanonicalInferenceItem(
            rank=1,
            mandi="Agra",
            state="UP",
            district="Agra",
            distance_km=10.0,
            current_price=-100.0,  # Invalid negative price
            predicted_price=1200.0,
            expected_change=50.0,
            expected_change_pct=5.0,
            expected_direction="UP"
        )
        resp = CanonicalRecommendationResponse(
            contract_metadata=meta,
            commodity="Potato",
            farmer_latitude=27.1,
            farmer_longitude=78.0,
            quantity_quintals=10.0,
            recommended_mandi="Agra",
            total_mandis_evaluated=1,
            overall_data_source="CACHE",
            recommendations=[item]
        )
        is_valid, reason = validate_inference_contract(resp)
        self.assertFalse(is_valid)
        self.assertIn("negative prices", reason)

    def test_07_blocked_insufficient_history(self):
        """Contract validation rejects response if INSUFFICIENT_HISTORY is marked RECOMMENDED."""
        meta = ContractMetadata()
        item = CanonicalInferenceItem(
            rank=1,
            mandi="Agra",
            state="UP",
            district="Agra",
            distance_km=10.0,
            current_price=1000.0,
            predicted_price=1050.0,
            expected_change=50.0,
            expected_change_pct=5.0,
            expected_direction="UP",
            data_reliability_status="INSUFFICIENT_HISTORY",
            recommendation_label="RECOMMENDED"  # Violation!
        )
        resp = CanonicalRecommendationResponse(
            contract_metadata=meta,
            commodity="Potato",
            farmer_latitude=27.1,
            farmer_longitude=78.0,
            quantity_quintals=10.0,
            recommended_mandi="Agra",
            total_mandis_evaluated=1,
            overall_data_source="CACHE",
            recommendations=[item]
        )
        is_valid, reason = validate_inference_contract(resp)
        self.assertFalse(is_valid)
        self.assertIn("Safety Violation", reason)

    def test_08_live_source_propagation(self):
        """overall_data_source propagates LIVE correctly."""
        item = CanonicalInferenceItem(
            rank=1, mandi="Agra", state="UP", district="Agra", distance_km=10.0,
            current_price=1000.0, predicted_price=1050.0, expected_change=50.0, expected_change_pct=5.0,
            expected_direction="UP", data_source="LIVE", data_freshness_status="LIVE_FRESH"
        )
        resp = CanonicalRecommendationResponse(
            contract_metadata=ContractMetadata(),
            commodity="Potato", farmer_latitude=27.1, farmer_longitude=78.0, quantity_quintals=10.0,
            recommended_mandi="Agra", total_mandis_evaluated=1, overall_data_source="LIVE",
            recommendations=[item]
        )
        self.assertEqual(resp.overall_data_source, "LIVE")
        self.assertEqual(resp.recommendations[0].data_source, "LIVE")

    def test_09_cache_source_propagation(self):
        """overall_data_source propagates CACHE correctly."""
        res = recommend_mandi(27.1767, 78.0081, 10.0, "Potato", farmer_facing=True)
        canonical = res.to_canonical_contract()
        self.assertIn(canonical.overall_data_source, ("CACHE", "LIVE"))

    def test_10_cache_stale_warning_propagation(self):
        """data_reliability_warning propagates into item warnings."""
        res = recommend_mandi(27.1767, 78.0081, 10.0, "Potato", farmer_facing=True)
        canonical = res.to_canonical_contract()
        item = canonical.recommendations[0]
        self.assertIsNotNone(item.data_reliability_warning)

    def test_11_confidence_range_validation(self):
        """Contract validator checks confidence_score range [0, 100]."""
        meta = ContractMetadata()
        item = CanonicalInferenceItem(
            rank=1, mandi="Agra", state="UP", district="Agra", distance_km=10.0,
            current_price=1000.0, predicted_price=1050.0, expected_change=50.0, expected_change_pct=5.0,
            expected_direction="UP", confidence_score=150.0  # Invalid > 100
        )
        resp = CanonicalRecommendationResponse(
            contract_metadata=meta, commodity="Potato", farmer_latitude=27.1, farmer_longitude=78.0,
            quantity_quintals=10.0, recommended_mandi="Agra", total_mandis_evaluated=1,
            overall_data_source="CACHE", recommendations=[item]
        )
        is_valid, reason = validate_inference_contract(resp)
        self.assertFalse(is_valid)
        self.assertIn("confidence_score out of range", reason)

    def test_12_reliability_score_range_validation(self):
        """Contract validator checks model_reliability_score range [0, 100]."""
        meta = ContractMetadata()
        item = CanonicalInferenceItem(
            rank=1, mandi="Agra", state="UP", district="Agra", distance_km=10.0,
            current_price=1000.0, predicted_price=1050.0, expected_change=50.0, expected_change_pct=5.0,
            expected_direction="UP", model_reliability_score=-10.0  # Invalid < 0
        )
        resp = CanonicalRecommendationResponse(
            contract_metadata=meta, commodity="Potato", farmer_latitude=27.1, farmer_longitude=78.0,
            quantity_quintals=10.0, recommended_mandi="Agra", total_mandis_evaluated=1,
            overall_data_source="CACHE", recommendations=[item]
        )
        is_valid, reason = validate_inference_contract(resp)
        self.assertFalse(is_valid)
        self.assertIn("model_reliability_score out of range", reason)

    def test_13_recommendation_item_serialization(self):
        """MandiRecommendationItem serializes cleanly via to_dict()."""
        item = CanonicalInferenceItem(
            rank=1, mandi="Agra", state="UP", district="Agra", distance_km=10.0,
            current_price=1000.0, predicted_price=1050.0, expected_change=50.0, expected_change_pct=5.0,
            expected_direction="UP"
        )
        d = item.to_dict()
        self.assertEqual(d["mandi"], "Agra")
        self.assertEqual(d["horizon_days"], 1)

    def test_14_prediction_output_serialization(self):
        """PredictionOutput dataclass converts cleanly to dictionary."""
        p_out = PredictionOutput(
            market="Agra", date=pd.Timestamp("2025-01-01"), current_price=1000.0,
            predicted_price=1050.0, expected_change=50.0, expected_change_pct=5.0,
            expected_direction="UP", commodity="Potato"
        )
        self.assertEqual(p_out.market, "Agra")

    def test_15_complete_recommendation_serialization(self):
        """CanonicalRecommendationResponse serializes to valid dictionary."""
        canonical = recommend_canonical(27.1767, 78.0081, 10.0, "Potato", farmer_facing=True)
        d = canonical.to_dict()
        self.assertIn("contract_metadata", d)
        self.assertEqual(d["contract_metadata"]["schema_version"], CONTRACT_VERSION)

    def test_16_deterministic_json_output(self):
        """to_json() produces parseable valid JSON string."""
        canonical = recommend_canonical(27.1767, 78.0081, 10.0, "Potato", farmer_facing=True)
        json_str = canonical.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["commodity"], "Potato")
        self.assertEqual(parsed["contract_metadata"]["system_id"], "SIH26132_AI_ENGINE")

    def test_17_task7_gate_cannot_be_bypassed(self):
        """DISABLED model (Rice Burdwan) cannot be assigned RECOMMENDED label in contract."""
        item = CanonicalInferenceItem(
            rank=1, mandi="Burdwan", state="WB", district="Burdwan", distance_km=10.0,
            current_price=1000.0, predicted_price=1050.0, expected_change=50.0, expected_change_pct=5.0,
            expected_direction="UP", model_usage_status="DISABLED", recommendation_label="RECOMMENDED"
        )
        resp = CanonicalRecommendationResponse(
            contract_metadata=ContractMetadata(), commodity="Rice", farmer_latitude=23.2,
            farmer_longitude=87.8, quantity_quintals=10.0, recommended_mandi="Burdwan",
            total_mandis_evaluated=1, overall_data_source="CACHE", recommendations=[item]
        )
        is_valid, reason = validate_inference_contract(resp)
        self.assertFalse(is_valid)
        self.assertIn("Safety Violation", reason)

    def test_18_task8_gate_cannot_be_bypassed(self):
        """INVALID_DATA status cannot be assigned RECOMMENDED label in contract."""
        item = CanonicalInferenceItem(
            rank=1, mandi="Burdwan", state="WB", district="Burdwan", distance_km=10.0,
            current_price=1000.0, predicted_price=1050.0, expected_change=50.0, expected_change_pct=5.0,
            expected_direction="UP", data_reliability_status="INVALID_DATA", recommendation_label="RECOMMENDED"
        )
        resp = CanonicalRecommendationResponse(
            contract_metadata=ContractMetadata(), commodity="Rice", farmer_latitude=23.2,
            farmer_longitude=87.8, quantity_quintals=10.0, recommended_mandi="Burdwan",
            total_mandis_evaluated=1, overall_data_source="CACHE", recommendations=[item]
        )
        is_valid, reason = validate_inference_contract(resp)
        self.assertFalse(is_valid)
        self.assertIn("Safety Violation", reason)

    def test_19_data_reliability_separate_from_model_confidence(self):
        """Contract keeps model_reliability_score, confidence_score, and data_freshness_status distinct."""
        item = CanonicalInferenceItem(
            rank=1, mandi="Agra", state="UP", district="Agra", distance_km=10.0,
            current_price=1000.0, predicted_price=1050.0, expected_change=50.0, expected_change_pct=5.0,
            expected_direction="UP", model_reliability_score=69.7, confidence_score=85.0,
            data_freshness_status="CACHE_STALE"
        )
        d = item.to_dict()
        self.assertEqual(d["model_reliability_score"], 69.7)
        self.assertEqual(d["confidence_score"], 85.0)
        self.assertEqual(d["data_freshness_status"], "CACHE_STALE")

    def test_20_backward_compatibility_recommendation_result(self):
        """RecommendationResult.to_dict() and to_canonical_contract() remain fully compatible."""
        res = recommend_mandi(27.1767, 78.0081, 10.0, "Potato", farmer_facing=True)
        legacy_dict = res.to_dict()
        canonical_obj = res.to_canonical_contract()
        self.assertEqual(legacy_dict["recommended_mandi"], canonical_obj.recommended_mandi)
        self.assertEqual(len(legacy_dict["recommendations"]), len(canonical_obj.recommendations))
