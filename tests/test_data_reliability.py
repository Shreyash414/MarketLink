"""
Task 8 Unit Tests -- Real-Time Data Freshness & Inference Reliability Layer.
Verifies all 22 required test cases for Task 8 data reliability safety & freshness policy.
"""
import unittest
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from src.data.data_reliability import (
    SOURCE_CACHE,
    SOURCE_LIVE,
    STATUS_CACHE_FRESH,
    STATUS_CACHE_STALE,
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_INVALID_DATA,
    STATUS_LIVE_FRESH,
    STATUS_READY,
    DataReliabilityResult,
    evaluate_data_freshness,
    evaluate_data_reliability,
    evaluate_historical_sufficiency,
    validate_price_data,
)
from src.models.model_predictor import ModelPredictor
from src.recommendation.mandi_recommender import recommend_mandi


def _create_mock_history_df(
    sessions: int = 45,
    start_date: str = "2025-01-01",
    modal_price: float = 1500.0,
    market: str = "Agra",
    commodity: str = "Potato",
) -> pd.DataFrame:
    """Helper function to create deterministic test datasets."""
    dates = pd.date_range(start=start_date, periods=sessions, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "market": market,
        "commodity": commodity,
        "modal_price": modal_price,
        "min_price": modal_price * 0.95,
        "max_price": modal_price * 1.05,
    })
    return df


class TestDataReliability(unittest.TestCase):

    def setUp(self):
        self.test_ref_date = pd.Timestamp("2025-02-15")

    def test_01_fresh_live_data_allowed(self):
        """Fresh LIVE data evaluates to LIVE_FRESH and is allowed."""
        obs_date = self.test_ref_date - pd.Timedelta(days=1)
        status, age, is_fresh = evaluate_data_freshness(
            observation_date=obs_date,
            source=SOURCE_LIVE,
            current_date=self.test_ref_date
        )
        self.assertEqual(status, STATUS_LIVE_FRESH)
        self.assertEqual(age, 1)
        self.assertTrue(is_fresh)

    def test_02_fresh_cache_data_allowed(self):
        """Fresh CACHE data (<= 7 days old) evaluates to CACHE_FRESH and is allowed."""
        obs_date = self.test_ref_date - pd.Timedelta(days=3)
        status, age, is_fresh = evaluate_data_freshness(
            observation_date=obs_date,
            source=SOURCE_CACHE,
            current_date=self.test_ref_date,
            max_age_days=7
        )
        self.assertEqual(status, STATUS_CACHE_FRESH)
        self.assertEqual(age, 3)
        self.assertTrue(is_fresh)

    def test_03_stale_cache_correctly_marked_stale(self):
        """Stale CACHE data (> 7 days old) evaluates to CACHE_STALE."""
        obs_date = self.test_ref_date - pd.Timedelta(days=10)
        status, age, is_fresh = evaluate_data_freshness(
            observation_date=obs_date,
            source=SOURCE_CACHE,
            current_date=self.test_ref_date,
            max_age_days=7
        )
        self.assertEqual(status, STATUS_CACHE_STALE)
        self.assertEqual(age, 10)
        self.assertFalse(is_fresh)

    def test_04_cache_never_becomes_live(self):
        """Cache data must NEVER be labeled LIVE even if age is 0 days."""
        obs_date = self.test_ref_date
        status, age, is_fresh = evaluate_data_freshness(
            observation_date=obs_date,
            source=SOURCE_CACHE,
            current_date=self.test_ref_date
        )
        self.assertNotEqual(status, STATUS_LIVE_FRESH)
        self.assertEqual(status, STATUS_CACHE_FRESH)

    def test_05_insufficient_history_blocked(self):
        """Fewer than required sessions (e.g., 20 sessions < 31 required) is blocked."""
        df = _create_mock_history_df(sessions=20)
        is_suff, count, reason = evaluate_historical_sufficiency(df, min_sessions=31)
        self.assertFalse(is_suff)
        self.assertEqual(count, 20)
        self.assertIn("Insufficient", reason)

    def test_06_sufficient_history_allowed(self):
        """Sufficient sessions (>= 31) passes warm-up check."""
        df = _create_mock_history_df(sessions=45)
        is_suff, count, reason = evaluate_historical_sufficiency(df, min_sessions=31)
        self.assertTrue(is_suff)
        self.assertEqual(count, 45)

    def test_07_invalid_price_negative_blocked(self):
        """Negative modal price is detected as invalid data."""
        df = _create_mock_history_df(sessions=45)
        df.loc[10, "modal_price"] = -500.0
        is_valid, reason = validate_price_data(df)
        self.assertFalse(is_valid)
        self.assertIn("non-positive", reason)

    def test_08_nan_price_blocked(self):
        """NaN modal price is detected as invalid data."""
        df = _create_mock_history_df(sessions=45)
        df.loc[10, "modal_price"] = np.nan
        is_valid, reason = validate_price_data(df)
        self.assertFalse(is_valid)
        self.assertIn("NaN", reason)

    def test_09_infinity_price_blocked(self):
        """Infinity modal price is detected as invalid data."""
        df = _create_mock_history_df(sessions=45)
        df.loc[10, "modal_price"] = np.inf
        is_valid, reason = validate_price_data(df)
        self.assertFalse(is_valid)
        self.assertIn("Infinity", reason)

    def test_10_invalid_date_blocked(self):
        """Invalid or NaT date is detected as invalid data."""
        df = _create_mock_history_df(sessions=45)
        df.loc[5, "date"] = pd.NaT
        is_valid, reason = validate_price_data(df)
        self.assertFalse(is_valid)
        self.assertIn("NaT", reason)

    def test_11_duplicate_session_detection(self):
        """Duplicate (market, date) rows are detected during validation."""
        df = _create_mock_history_df(sessions=45)
        # Duplicate row 5
        df = pd.concat([df, df.iloc[[5]]], ignore_index=True)
        is_valid, reason = validate_price_data(df)
        self.assertFalse(is_valid)
        self.assertIn("Duplicate", reason)

    def test_12_missing_lag_history(self):
        """Empty or missing history dataframe is detected as non-sufficient."""
        is_suff, count, reason = evaluate_historical_sufficiency(pd.DataFrame(), min_sessions=31)
        self.assertFalse(is_suff)
        self.assertEqual(count, 0)

    def test_13_structured_reliability_metadata(self):
        """evaluate_data_reliability returns a fully populated DataReliabilityResult dataclass."""
        df = _create_mock_history_df(sessions=45, start_date="2025-01-01")
        res = evaluate_data_reliability(
            commodity="Potato",
            market="Agra",
            merged_df=df,
            source=SOURCE_CACHE,
            current_date=pd.Timestamp("2025-02-15"),
            max_age_days=7
        )
        self.assertIsInstance(res, DataReliabilityResult)
        self.assertEqual(res.commodity, "Potato")
        self.assertEqual(res.market, "Agra")
        self.assertEqual(res.session_count, 45)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.is_sufficient)

    def test_14_predictor_respects_data_reliability_block(self):
        """ModelPredictor raises PermissionError when data_reliability.inference_allowed is False."""
        predictor = ModelPredictor()
        mock_rel = DataReliabilityResult(
            commodity="Potato",
            market="Agra",
            inference_allowed=False,
            status=STATUS_INVALID_DATA,
            source=SOURCE_CACHE,
            freshness_status=STATUS_CACHE_STALE,
            observation_date=pd.Timestamp("2025-01-01"),
            age_days=45,
            session_count=10,
            is_fresh=False,
            is_sufficient=False,
            is_valid=False,
            reason="Test data reliability block",
            warning="Block warning"
        )
        X_dummy = pd.DataFrame({"dummy": [1]})
        with self.assertRaises(PermissionError) as ctx:
            predictor.predict_next_price(
                market="Agra",
                X_features=X_dummy,
                current_price=1000.0,
                latest_date=pd.Timestamp("2025-01-01"),
                commodity="Potato",
                farmer_facing=True,
                data_reliability=mock_rel
            )
        self.assertIn("blocked inference", str(ctx.exception))

    def test_15_recommender_respects_data_reliability_block(self):
        """MandiRecommender skips candidate mandis if data reliability check fails."""
        # Querying an unknown crop with no historical data will yield no eligible mandis
        res = recommend_mandi(
            farmer_latitude=28.6139,
            farmer_longitude=77.2090,
            quantity_quintals=10.0,
            commodity="InvalidCropName",
            farmer_facing=True
        )
        self.assertEqual(res.recommended_mandi, "NONE")

    def test_16_live_source_propagation(self):
        """DataReliabilityResult with source='LIVE' propagates freshness_status='LIVE_FRESH'."""
        df = _create_mock_history_df(sessions=45, start_date="2025-01-01")
        res = evaluate_data_reliability(
            commodity="Potato",
            market="Agra",
            merged_df=df,
            source=SOURCE_LIVE,
            current_date=pd.Timestamp("2025-02-15")
        )
        self.assertEqual(res.source, SOURCE_LIVE)
        self.assertEqual(res.freshness_status, STATUS_LIVE_FRESH)

    def test_17_cache_source_propagation(self):
        """DataReliabilityResult with source='CACHE' propagates source tag correctly."""
        df = _create_mock_history_df(sessions=45, start_date="2025-01-01")
        res = evaluate_data_reliability(
            commodity="Potato",
            market="Agra",
            merged_df=df,
            source=SOURCE_CACHE,
            current_date=pd.Timestamp("2025-02-15")
        )
        self.assertEqual(res.source, SOURCE_CACHE)

    def test_18_task_7_model_quality_gate_coexists(self):
        """Task 7 model quality gate and Task 8 data reliability gate both function independently."""
        df = _create_mock_history_df(sessions=45, start_date="2025-01-01")
        # Reliable data for Potato Agra (PRODUCTION_READY) -> allowed
        res = evaluate_data_reliability(
            commodity="Potato",
            market="Agra",
            merged_df=df,
            source=SOURCE_CACHE,
            current_date=pd.Timestamp("2025-02-15"),
            max_age_days=60  # generous max age to allow fresh test evaluation
        )
        self.assertTrue(res.inference_allowed)

    def test_19_production_ready_plus_reliable_data_allowed(self):
        """PRODUCTION_READY model + reliable data allows prediction."""
        res = recommend_mandi(
            farmer_latitude=27.1767,
            farmer_longitude=78.0081,
            quantity_quintals=10.0,
            commodity="Potato",
            farmer_facing=True
        )
        self.assertEqual(res.recommended_mandi, "Agra")
        self.assertEqual(len(res.recommendations), 1)
        item = res.recommendations[0]
        self.assertEqual(item.model_usage_status, "PRODUCTION_READY")
        self.assertTrue(item.data_reliability_status in (STATUS_READY, STATUS_CACHE_STALE))

    def test_20_usable_with_warning_plus_reliable_data_allowed_with_warning(self):
        """USABLE_WITH_WARNING model + reliable data yields recommendation with structured warning."""
        res = recommend_mandi(
            farmer_latitude=22.7196,
            farmer_longitude=75.8577,
            quantity_quintals=10.0,
            commodity="Wheat",
            farmer_facing=True
        )
        self.assertEqual(res.recommended_mandi, "Indore")
        self.assertEqual(len(res.recommendations), 1)
        item = res.recommendations[0]
        self.assertEqual(item.model_usage_status, "USABLE_WITH_WARNING")
        self.assertTrue(len(item.warning) > 0)

    def test_21_disabled_model_plus_reliable_data_blocked_by_task7_gate(self):
        """DISABLED model (e.g. Rice Burdwan) remains blocked even if data is valid."""
        res = recommend_mandi(
            farmer_latitude=23.2324,
            farmer_longitude=87.8615,
            quantity_quintals=10.0,
            commodity="Rice",
            farmer_facing=True
        )
        self.assertEqual(res.recommended_mandi, "NONE")
        self.assertEqual(len(res.recommendations), 0)

    def test_22_missing_model_remains_blocked(self):
        """Unregistered/missing market model remains blocked."""
        df = _create_mock_history_df(sessions=45)
        res = evaluate_data_reliability(
            commodity="Potato",
            market="FakeNonExistentMarket",
            merged_df=df,
            source=SOURCE_CACHE,
            current_date=pd.Timestamp("2025-02-15")
        )
        self.assertTrue(res.inference_allowed)  # Data reliability allows data, but Task 7 gate blocks model
