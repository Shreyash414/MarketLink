"""
Market Data Service.
Retrieves and normalizes live and cached AGMARKNET mandi price data decoupled from ML inference.
"""
from typing import Any, Dict, List, Optional
import pandas as pd

from src.data.ingestion.current_data_fetcher import CurrentDataFetcher
from src.utils.logger import logger


class MarketDataService:
    """Service providing current market price data across mandis."""

    def __init__(self, fetcher: Optional[CurrentDataFetcher] = None):
        self.fetcher = fetcher or CurrentDataFetcher()

    def get_market_data(
        self,
        commodity: str = "Onion",
        target_markets: Optional[List[str]] = None,
        state_name: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Fetch current prices for requested commodity and markets."""
        try:
            df, is_live, source = self.fetcher.fetch_all_current_data(
                commodity=commodity,
                target_markets=target_markets,
                state_name=state_name,
                max_records_per_market=limit,
            )

            records = []
            if not df.empty:
                # Clean and serialize records
                for _, row in df.iterrows():
                    rec = {
                        "state": str(row.get("state", "N/A")),
                        "district": str(row.get("district", "N/A")),
                        "market": str(row.get("market", "N/A")),
                        "commodity": str(row.get("commodity", commodity)),
                        "modal_price": float(row.get("modal_price", 0.0)),
                        "min_price": float(row.get("min_price", row.get("modal_price", 0.0))),
                        "max_price": float(row.get("max_price", row.get("modal_price", 0.0))),
                        "date": str(row.get("date", "N/A")),
                    }
                    records.append(rec)

            return {
                "commodity": commodity,
                "data_source": source,
                "is_live": is_live,
                "record_count": len(records),
                "records": records,
            }
        except Exception as e:
            logger.error(f"Error fetching market data for {commodity}: {e}")
            return {
                "commodity": commodity,
                "data_source": "ERROR",
                "is_live": False,
                "record_count": 0,
                "records": [],
            }


market_data_service = MarketDataService()
