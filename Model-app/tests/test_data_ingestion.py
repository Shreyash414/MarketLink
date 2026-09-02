"""
Unit tests for data ingestion, validation, and cache fallback.
"""
import unittest
from pathlib import Path
import pandas as pd
from src.data.ingestion.current_data_fetcher import CurrentDataFetcher


class TestDataIngestion(unittest.TestCase):

    def setUp(self):
        self.fetcher = CurrentDataFetcher()

    def test_validation_and_clean_onion_only(self):
        df_dummy = pd.DataFrame([
            {"market": "Bareilly", "commodity": "Onion", "modal_price": 2000, "arrival_date": "2026-09-01", "state": "UP", "district": "Bareilly"},
            {"market": "Bareilly", "commodity": "Potato", "modal_price": 1500, "arrival_date": "2026-09-01", "state": "UP", "district": "Bareilly"},
            {"market": "Bargarh", "commodity": "Onion", "modal_price": -50, "arrival_date": "2026-09-01", "state": "Odisha", "district": "Bargarh"},  # Invalid negative price
        ])

        cleaned = self.fetcher.validate_and_clean(df_dummy, target_commodity="Onion")
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned["commodity"].iloc[0].lower(), "onion")
        self.assertEqual(cleaned["market"].iloc[0], "Bareilly")

    def test_cache_fallback(self):
        # Fetcher should gracefully return data from cache/fallback if API fails or when requested
        df_cached, is_live, source_tag = self.fetcher.fetch_all_current_data(
            commodity="Onion",
            target_markets=["Bareilly"]
        )
        self.assertFalse(df_cached.empty)
        self.assertIn(source_tag, ["LIVE", "CACHE"])
        self.assertIn("modal_price", df_cached.columns)

if __name__ == "__main__":
    unittest.main()
