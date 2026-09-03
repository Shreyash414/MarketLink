"""
Current Mandi Data Fetcher Module.
Handles robust API ingestion from data.gov.in / AGMARKNET with retries,
pagination, caching, fallback mechanism, logging, and data validation.
"""
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

from src.config.config import (
    API_BASE_URL,
    API_CONNECT_TIMEOUT,
    API_MAX_RETRIES,
    API_PAGE_LIMIT,
    API_READ_TIMEOUT,
    API_RESOURCE_ID_CURRENT,
    CACHE_DIR,
    CURRENT_ONION_FILE,
    DATA_GOV_API_KEY,
    RAW_DATA_DIR,
    get_current_data_file,
)
from src.utils.logger import logger


class CurrentDataFetcher:
    """
    Production-grade current market price fetcher for data.gov.in AGMARKNET resources.
    Supports multi-commodity ingestion, per-commodity caching, and resilient fallbacks.
    """

    def __init__(
        self,
        resource_id: str = API_RESOURCE_ID_CURRENT,
        api_key: Optional[str] = DATA_GOV_API_KEY,
        cache_dir: Path = CACHE_DIR,
        output_file: Optional[Path] = None,
    ):
        self.resource_id = resource_id
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.output_file = Path(output_file) if output_file else None
        self.api_url = f"{API_BASE_URL}{self.resource_id}"
        self.cache_file = self.cache_dir / f"current_{resource_id}_cache.csv"


    def fetch_market_page(
        self,
        commodity: str = "Onion",
        market_name: Optional[str] = None,
        state_name: Optional[str] = None,
        limit: int = API_PAGE_LIMIT,
        offset: int = 0,
    ) -> List[Dict]:
        """
        Fetch a single page of data with retries and exponential backoff.
        """
        if not self.api_key:
            raise ValueError(
                "DATA_GOV_API_KEY not found in environment variables. "
                "Ensure .env file exists and contains DATA_GOV_API_KEY."
            )

        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
            "offset": offset,
            "filters[commodity]": commodity,
        }

        if market_name:
            params["filters[market]"] = market_name
        if state_name:
            params["filters[state]"] = state_name

        for attempt in range(1, API_MAX_RETRIES + 1):
            try:
                logger.info(
                    f"API request started (attempt {attempt}/{API_MAX_RETRIES}, "
                    f"limit={limit}, offset={offset}, commodity={commodity}, market={market_name or 'ALL'})"
                )
                response = requests.get(
                    self.api_url,
                    params=params,
                    timeout=(API_CONNECT_TIMEOUT, API_READ_TIMEOUT),
                )
                response.raise_for_status()
                data = response.json()
                records = data.get("records", [])
                logger.info(
                    f"API request succeeded (records fetched: {len(records)})"
                )
                return records

            except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                logger.warning(
                    f"API request failed on attempt {attempt}/{API_MAX_RETRIES}: {e}"
                )
                if attempt < API_MAX_RETRIES:
                    backoff_delay = 2 ** (attempt - 1)  # 1s, 2s, 4s, 8s
                    logger.info(f"Retrying in {backoff_delay} seconds...")
                    time.sleep(backoff_delay)

        logger.error(
            f"API request exhausted all {API_MAX_RETRIES} attempts for market={market_name}."
        )
        return []

    def fetch_all_current_data(
        self,
        commodity: str = "Onion",
        target_markets: Optional[List[str]] = None,
        state_name: Optional[str] = None,
        max_records_per_market: int = 200,
    ) -> Tuple[pd.DataFrame, bool, str]:
        """
        Fetch current market data for target markets or all markets with pagination.
        Falls back to local cache if live fetch fails.
        """
        all_records = []
        retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_live = False

        consecutive_failures = 0
        max_consecutive_failures = 1

        if not self.api_key:
            logger.warning(
                "DATA_GOV_API_KEY is not set. Skipping live API fetch and attempting local cache fallback."
            )
        elif target_markets:
            for market in target_markets:
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(
                        f"Skipping remaining live API queries after {consecutive_failures} consecutive API timeouts. "
                        f"Failing fast to local cache fallback."
                    )
                    break
                offset = 0
                market_records = []
                while offset < max_records_per_market:
                    records = self.fetch_market_page(
                        commodity=commodity,
                        market_name=market,
                        state_name=state_name,
                        limit=API_PAGE_LIMIT,
                        offset=offset,
                    )
                    if not records:
                        consecutive_failures += 1
                        break
                    else:
                        consecutive_failures = 0

                    market_records.extend(records)
                    if len(records) < API_PAGE_LIMIT:
                        break
                    offset += API_PAGE_LIMIT
                    time.sleep(0.1)  # Rate limiting
                all_records.extend(market_records)
        else:
            offset = 0
            while offset < max_records_per_market:
                records = self.fetch_market_page(
                    commodity=commodity,
                    state_name=state_name,
                    limit=API_PAGE_LIMIT,
                    offset=offset,
                )
                if not records:
                    break
                all_records.extend(records)
                if len(records) < API_PAGE_LIMIT:
                    break
                offset += API_PAGE_LIMIT
                time.sleep(0.1)


        if all_records:
            is_live = True
            source_tag = "LIVE"
            logger.info(
                f"Successfully retrieved {len(all_records)} live records from AGMARKNET API."
            )
            df_raw = pd.DataFrame(all_records)
            df_raw["retrieved_at"] = retrieved_at
            df_raw["source"] = source_tag
            df_raw["is_live"] = True
            
            # Save to cache
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            df_raw.to_csv(self.cache_file, index=False)
            logger.info(f"Updated local cache at {self.cache_file}")

        else:
            source_tag = "CACHE"
            logger.warning(
                "Live API fetch yielded no records or failed. Attempting to load from local cache..."
            )
            df_raw, retrieved_at = self._load_from_cache()

        if df_raw.empty:
            logger.error("No data available from either LIVE API or CACHE.")
            return pd.DataFrame(), False, "NONE"

        # Validate and clean data
        cleaned_df = self.validate_and_clean(df_raw, target_commodity=commodity)
        cleaned_df["source"] = source_tag
        cleaned_df["is_live"] = is_live
        cleaned_df["retrieved_at"] = retrieved_at

        # Save processed current data
        target_output = self.output_file if self.output_file is not None else get_current_data_file(commodity)
        target_output.parent.mkdir(parents=True, exist_ok=True)
        cleaned_df.to_csv(target_output, index=False)
        logger.info(f"Saved processed current data ({len(cleaned_df)} rows) to {target_output}")

        return cleaned_df, is_live, source_tag

    def _load_from_cache(self) -> Tuple[pd.DataFrame, str]:
        """
        Load records from local cache file if available.
        """
        if self.cache_file.exists():
            try:
                df = pd.read_csv(self.cache_file)
                retrieved_at = (
                    df["retrieved_at"].iloc[0]
                    if "retrieved_at" in df.columns
                    else "CACHE_HISTORICAL"
                )
                logger.info(
                    f"Successfully loaded {len(df)} cached records from {self.cache_file} (Retrieved: {retrieved_at})"
                )
                return df, str(retrieved_at)
            except Exception as e:
                logger.error(f"Failed to read cache file {self.cache_file}: {e}")

        # Check raw fallback file if exists
        fallback_raw = RAW_DATA_DIR / "mandi_current_raw.csv"
        if fallback_raw.exists():
            try:
                df = pd.read_csv(fallback_raw)
                logger.info(
                    f"Successfully loaded fallback raw data ({len(df)} rows) from {fallback_raw}"
                )
                return df, "CACHE_FALLBACK_RAW"
            except Exception as e:
                logger.error(f"Failed to read fallback raw file {fallback_raw}: {e}")

        return pd.DataFrame(), "NONE"

    def validate_and_clean(
        self, df: pd.DataFrame, target_commodity: str = "Onion"
    ) -> pd.DataFrame:
        """
        Validate schema, data types, commodity filter, and numeric integrity.
        """
        if df.empty:
            return df

        df = df.copy()

        # Standardize column names
        df.columns = [col.strip().lower() for col in df.columns]

        # Map common column name variations
        column_mapping = {
            "arrival_date": "date",
            "modal_price": "modal_price",
            "min_price": "min_price",
            "max_price": "max_price",
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Required columns check
        required_cols = ["state", "district", "market", "commodity", "modal_price"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            logger.warning(f"Data missing expected columns: {missing_cols}")

        # Clean text fields
        for col in ["state", "district", "market", "commodity", "variety", "grade"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        # Commodity filter
        if "commodity" in df.columns:
            initial_count = len(df)
            df = df[df["commodity"].str.lower() == target_commodity.lower()].copy()
            filtered_out = initial_count - len(df)
            if filtered_out > 0:
                logger.info(
                    f"Filtered out {filtered_out} non-{target_commodity} records."
                )

        # Date handling
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        elif "reported_date" in df.columns:
            df["date"] = pd.to_datetime(df["reported_date"], errors="coerce")
        else:
            df["date"] = pd.Timestamp.now()

        # Drop invalid dates
        invalid_dates = df["date"].isna().sum()
        if invalid_dates > 0:
            logger.warning(f"Removed {invalid_dates} records with malformed dates.")
            df = df.dropna(subset=["date"]).copy()

        # Price numeric conversion & positive price check
        price_cols = ["modal_price", "min_price", "max_price"]
        for p_col in price_cols:
            if p_col in df.columns:
                df[p_col] = pd.to_numeric(df[p_col], errors="coerce")

        initial_count = len(df)
        df = df[df["modal_price"] > 0].copy()
        removed_prices = initial_count - len(df)
        if removed_prices > 0:
            logger.warning(
                f"Removed {removed_prices} records with non-positive or null modal_price."
            )

        # Price logic check: min <= modal <= max
        if "min_price" in df.columns and "max_price" in df.columns:
            invalid_range = (
                (df["min_price"] > df["modal_price"])
                | (df["modal_price"] > df["max_price"])
            ).sum()
            if invalid_range > 0:
                logger.warning(
                    f"Reported {invalid_range} records where min_price > modal_price or modal_price > max_price."
                )

        # Deduplicate by market and date
        if "market" in df.columns and "date" in df.columns:
            initial_count = len(df)
            df = df.sort_values("date").drop_duplicates(
                subset=["market", "date"], keep="last"
            ).reset_index(drop=True)
            dups_removed = initial_count - len(df)
            if dups_removed > 0:
                logger.info(f"Removed {dups_removed} duplicate (market, date) records.")

        return df
