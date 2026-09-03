"""
Unit tests for Government Mandi Market Data Explorer Service.
Verifies current data, historical chart data, options discovery, reliability, error handling,
JSON serialization, and strict separation from ML prediction.
"""
import json
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

from src.data.market_data_service import (
    CurrentMarketDataRecord,
    CurrentMarketDataResponse,
    HistoricalMarketDataResponse,
    HistoricalPricePoint,
    MarketOptionsResponse,
    get_available_market_options,
    get_current_market_data,
    get_historical_market_data,
)


class TestMarketDataService(unittest.TestCase):

    @patch("src.data.market_data_service.CurrentDataFetcher")
    def test_01_current_data_retrieval_valid(self, mock_fetcher_cls):
        """Current market data returns valid structure for Potato Agra."""
        mock_df = pd.DataFrame([{
            "commodity": "Potato",
            "market": "Agra",
            "state": "Uttar Pradesh",
            "district": "Agra",
            "date": "2026-09-03",
            "min_price": 1100.0,
            "max_price": 1300.0,
            "modal_price": 1200.0,
            "arrival": 150.0
        }])
        mock_instance = MagicMock()
        mock_instance.fetch_all_current_data.return_value = (mock_df, True, "LIVE")
        mock_fetcher_cls.return_value = mock_instance

        res = get_current_market_data("Potato", "Agra")
        self.assertIsInstance(res, CurrentMarketDataResponse)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.commodity, "Potato")
        self.assertEqual(res.market, "Agra")
        self.assertIsNotNone(res.data)
        self.assertEqual(res.data.modal_price, 1200.0)
        self.assertEqual(res.metadata["source"], "LIVE")

    def test_02_current_data_invalid_input(self):
        """Invalid or empty commodity/market strings return structured error response."""
        res = get_current_market_data("", "")
        self.assertEqual(res.status, "ERROR")
        self.assertIn("Invalid", res.metadata.get("error", ""))

    def test_03_current_data_missing_arrival_handling(self):
        """Record with missing/None arrival field serializes safely without crashing."""
        rec = CurrentMarketDataRecord(
            commodity="Potato",
            market="Agra",
            state="UP",
            district="Agra",
            date="2026-09-03",
            min_price=1100.0,
            max_price=1300.0,
            modal_price=1200.0,
            arrival=None,
            unit="Rs/quintal"
        )
        d = rec.to_dict()
        self.assertIsNone(d["arrival"])
        self.assertEqual(d["modal_price"], 1200.0)

    def test_04_historical_data_retrieval_valid(self):
        """Historical data returns chronologically sorted price points."""
        res = get_historical_market_data("Potato", "Agra", "2024-01-01", "2024-06-30")
        self.assertIsInstance(res, HistoricalMarketDataResponse)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.commodity, "Potato")
        self.assertEqual(res.market, "Agra")
        if len(res.records) > 1:
            self.assertLessEqual(res.records[0].date, res.records[1].date)

    def test_05_historical_data_sorting_and_deduplication(self):
        """Verify historical price points are chronologically sorted and deduplicated."""
        p1 = HistoricalPricePoint("2024-01-01", 1000.0, 1200.0, 1100.0, 50.0)
        p2 = HistoricalPricePoint("2024-01-02", 1050.0, 1250.0, 1150.0, 60.0)
        resp = HistoricalMarketDataResponse(
            status="SUCCESS",
            commodity="Potato",
            market="Agra",
            location={"state": "UP", "district": "Agra"},
            date_range={"from": "2024-01-01", "to": "2024-01-02"},
            records=[p1, p2],
            metadata={"source": "CACHE", "record_count": 2}
        )
        self.assertEqual(len(resp.records), 2)
        self.assertEqual(resp.records[0].date, "2024-01-01")

    def test_06_date_range_filtering(self):
        """Records outside requested date range are excluded."""
        res = get_historical_market_data("Potato", "Agra", "2024-01-01", "2024-01-31")
        for rec in res.records:
            self.assertTrue("2024-01-01" <= rec.date <= "2024-01-31")

    def test_07_invalid_date_range_error(self):
        """start_date > end_date returns structured error response."""
        res = get_historical_market_data("Potato", "Agra", "2026-09-10", "2026-09-01")
        self.assertEqual(res.status, "ERROR")
        self.assertIn("start_date cannot be after end_date", res.metadata.get("error", ""))

    def test_08_empty_result_handling(self):
        """Non-existent commodity/market returns clean empty response without crashing."""
        res = get_historical_market_data("NonExistentCrop", "NonExistentMarket", "2024-01-01", "2024-06-30")
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(len(res.records), 0)
        self.assertEqual(res.metadata["record_count"], 0)

    def test_09_live_source_labeling(self):
        """Metadata correctly reflects LIVE source when live API data is returned."""
        rec = CurrentMarketDataRecord("Potato", "Agra", "UP", "Agra", "2026-09-03", 1100, 1300, 1200)
        resp = CurrentMarketDataResponse(
            status="SUCCESS", commodity="Potato", market="Agra",
            location={"state": "UP", "district": "Agra"}, data=rec,
            metadata={"source": "LIVE", "freshness_status": "LIVE_FRESH", "data_age_days": 0, "record_count": 1}
        )
        self.assertEqual(resp.metadata["source"], "LIVE")
        self.assertEqual(resp.metadata["freshness_status"], "LIVE_FRESH")

    @patch("src.data.market_data_service.CurrentDataFetcher")
    def test_10_cache_source_labeling(self, mock_fetcher_cls):
        """Cached data is labeled CACHE and NEVER labeled LIVE."""
        mock_df = pd.DataFrame([{
            "commodity": "Potato",
            "market": "Agra",
            "state": "UP",
            "district": "Agra",
            "date": "2026-01-01",
            "min_price": 1100.0,
            "max_price": 1300.0,
            "modal_price": 1200.0,
            "arrival": 100.0
        }])
        mock_instance = MagicMock()
        mock_instance.fetch_all_current_data.return_value = (mock_df, False, "CACHE")
        mock_fetcher_cls.return_value = mock_instance

        res = get_current_market_data("Potato", "Agra")
        self.assertEqual(res.metadata["source"], "CACHE")
        self.assertNotEqual(res.metadata["source"], "LIVE")

    def test_11_cache_stale_warning_propagation(self):
        """Stale cache generates explicit freshness status and warning string."""
        rec = CurrentMarketDataRecord("Potato", "Agra", "UP", "Agra", "2024-01-01", 1100, 1300, 1200)
        resp = CurrentMarketDataResponse(
            status="SUCCESS", commodity="Potato", market="Agra",
            location={"state": "UP", "district": "Agra"}, data=rec,
            metadata={"source": "CACHE", "freshness_status": "CACHE_STALE", "data_age_days": 300, "record_count": 1, "warning": "Cache data is 300 days old."}
        )
        self.assertEqual(resp.metadata["freshness_status"], "CACHE_STALE")
        self.assertTrue(len(resp.metadata["warning"]) > 0)

    def test_12_available_market_options_discovery(self):
        """get_available_market_options returns lists of commodities, markets, states, and districts."""
        opts = get_available_market_options()
        self.assertIsInstance(opts, MarketOptionsResponse)
        self.assertEqual(opts.status, "SUCCESS")
        self.assertTrue(len(opts.commodities) > 0)
        self.assertTrue(len(opts.markets) > 0)
        self.assertIn("Potato", opts.commodities)
        self.assertIn("Agra", opts.markets)

    @patch("src.data.market_data_service.CurrentDataFetcher")
    def test_13_current_response_json_serialization(self, mock_fetcher_cls):
        """CurrentMarketDataResponse converts cleanly to valid JSON string."""
        mock_df = pd.DataFrame([{
            "commodity": "Potato",
            "market": "Agra",
            "state": "UP",
            "district": "Agra",
            "date": "2026-09-03",
            "min_price": 1100.0,
            "max_price": 1300.0,
            "modal_price": 1200.0,
            "arrival": 150.0
        }])
        mock_instance = MagicMock()
        mock_instance.fetch_all_current_data.return_value = (mock_df, True, "LIVE")
        mock_fetcher_cls.return_value = mock_instance

        res = get_current_market_data("Potato", "Agra")
        json_str = res.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["status"], "SUCCESS")
        self.assertEqual(parsed["commodity"], "Potato")

    def test_14_historical_response_json_serialization(self):
        """HistoricalMarketDataResponse converts cleanly to valid JSON string."""
        res = get_historical_market_data("Potato", "Agra", "2024-01-01", "2024-06-30")
        json_str = res.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["status"], "SUCCESS")
        self.assertIn("records", parsed)

    def test_15_options_response_json_serialization(self):
        """MarketOptionsResponse converts cleanly to valid JSON string."""
        opts = get_available_market_options()
        json_str = opts.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["status"], "SUCCESS")
        self.assertIsInstance(parsed["commodities"], list)

    def test_16_strict_separation_no_ml_invocation(self):
        """Market Data functions execute without calling ModelPredictor or MandiRecommender."""
        with patch("src.models.model_predictor.ModelPredictor.predict_next_price") as mock_predict:
            get_current_market_data("Potato", "Agra")
            get_historical_market_data("Potato", "Agra", "2024-01-01", "2024-06-30")
            get_available_market_options()
            mock_predict.assert_not_called()

    @patch("src.data.ingestion.current_data_fetcher.CurrentDataFetcher.fetch_market_page")
    def test_17_backward_compatibility(self, mock_page):
        """Importing market_data_service does not break core recommendation engine."""
        mock_page.return_value = []
        from src.recommendation.mandi_recommender import recommend_canonical
        res = recommend_canonical(27.1767, 78.0081, 10.0, "Potato", farmer_facing=True)
        self.assertEqual(res.recommended_mandi, "Agra")
