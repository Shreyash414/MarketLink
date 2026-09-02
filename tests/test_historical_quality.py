"""Tests for historical acquisition helpers, variety/grade fallback, and quality gates."""
import unittest

import pandas as pd

from src.config.config import MIN_VARIETY_GRADE_OBSERVATIONS
from src.data.ingestion.historical_data_fetcher import HistoricalDataFetcher
from src.data.preprocessing.quality_gate import evaluate_series_quality
from src.data.preprocessing.variety_grade import select_variety_grade
from src.recommendation.mandi_recommender import MandiRecommender


class TestHistoricalFetcherParams(unittest.TestCase):
    def test_pascal_case_filters(self):
        fetcher = HistoricalDataFetcher(api_key="dummy")
        params = fetcher.build_params(
            commodity="Potato",
            market="Agra",
            state="Uttar Pradesh",
            variety="Jyoti",
            grade="FAQ",
            offset=500,
        )
        self.assertEqual(params["filters[Commodity]"], "Potato")
        self.assertEqual(params["filters[Market]"], "Agra")
        self.assertEqual(params["filters[State]"], "Uttar Pradesh")
        self.assertEqual(params["filters[Variety]"], "Jyoti")
        self.assertEqual(params["filters[Grade]"], "FAQ")
        self.assertEqual(params["offset"], 500)
        self.assertNotIn("filters[commodity]", params)


class TestVarietyGradeFallback(unittest.TestCase):
    def test_skips_short_mode_and_selects_next(self):
        rows = []
        for i in range(55):
            rows.append({
                "date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=i),
                "modal_price": 100,
                "variety": "RareHighRank",
                "grade": "A",
            })
        for i in range(80):
            rows.append({
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i % 40),
                "modal_price": 110 + i,
                "variety": "Common",
                "grade": "FAQ",
            })
        df = pd.DataFrame(rows)
        selected, report = select_variety_grade(df, min_observations=60)
        self.assertEqual(report["status"], "SELECTED")
        self.assertEqual(report["selected_variety"], "Common")
        self.assertEqual(report["selected_grade"], "FAQ")
        self.assertGreaterEqual(len(selected), MIN_VARIETY_GRADE_OBSERVATIONS)
        self.assertTrue(any(not a["accepted"] for a in report["attempts"]))

    def test_insufficient_when_all_short(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=20),
            "modal_price": range(20),
            "variety": ["X"] * 20,
            "grade": ["G"] * 20,
        })
        selected, report = select_variety_grade(df, min_observations=60)
        self.assertTrue(selected.empty)
        self.assertEqual(report["status"], "INSUFFICIENT_DATA")


class TestQualityGate(unittest.TestCase):
    def test_insufficient_sessions(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "modal_price": [100] * 30,
        })
        result = evaluate_series_quality(df, min_sessions=200)
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")

    def test_invalid_prices(self):
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=220),
            "modal_price": [0] * 220,
        })
        result = evaluate_series_quality(df, min_sessions=200)
        self.assertEqual(result["status"], "POOR_DATA_QUALITY")


class TestGpsSkip(unittest.TestCase):
    def test_missing_coordinates_are_dropped(self):
        rec = MandiRecommender()
        meta = rec.load_market_metadata(commodity="Onion")
        self.assertFalse(meta["latitude"].isna().any())
        self.assertFalse(meta["longitude"].isna().any())
        self.assertIn("Bareilly", meta["market"].tolist())


if __name__ == "__main__":
    unittest.main()
