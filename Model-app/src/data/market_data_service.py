"""
Government Mandi Market Data Explorer Service.
Provides independent current & historical market data retrieval and market discovery
from official government sources (data.gov.in / AGMARKNET) without ML model dependencies.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.config.commodity_registry import (
    get_commodity_config,
    list_registered_commodities,
)
from src.config.config import (
    CACHE_DIR,
    DATA_DIR,
    MAX_DATA_AGE_DAYS,
    MARKET_METADATA_FILE,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
)
from src.data.data_reliability import (
    SOURCE_CACHE,
    SOURCE_LIVE,
    STATUS_CACHE_FRESH,
    STATUS_CACHE_STALE,
    STATUS_LIVE_FRESH,
    evaluate_data_freshness,
)
from src.data.ingestion.current_data_fetcher import CurrentDataFetcher
from src.utils.logger import logger


@dataclass
class CurrentMarketDataRecord:
    commodity: str
    market: str
    state: str
    district: str
    date: str
    min_price: float
    max_price: float
    modal_price: float
    arrival: Optional[float] = None
    unit: str = "Rs/quintal"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CurrentMarketDataResponse:
    status: str
    commodity: str
    market: str
    location: Dict[str, str]
    data: Optional[CurrentMarketDataRecord]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "commodity": self.commodity,
            "market": self.market,
            "location": self.location,
            "data": self.data.to_dict() if self.data else None,
            "metadata": self.metadata,
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class HistoricalPricePoint:
    date: str
    min_price: float
    max_price: float
    modal_price: float
    arrival: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HistoricalMarketDataResponse:
    status: str
    commodity: str
    market: str
    location: Dict[str, str]
    date_range: Dict[str, str]
    records: List[HistoricalPricePoint]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "commodity": self.commodity,
            "market": self.market,
            "location": self.location,
            "date_range": self.date_range,
            "records": [rec.to_dict() for rec in self.records],
            "metadata": self.metadata,
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


@dataclass
class MarketOptionsResponse:
    status: str
    commodities: List[str]
    markets: List[str]
    states: List[str]
    districts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def _get_market_location(commodity: str, market: str) -> Tuple[str, str]:
    """Helper to lookup state and district for a market from metadata."""
    state = "Unknown"
    district = "Unknown"
    if os.path.exists(MARKET_METADATA_FILE):
        try:
            df = pd.read_csv(MARKET_METADATA_FILE)
            match = df[df["market"].str.lower() == market.lower()]
            if not match.empty:
                state = str(match.iloc[0].get("state", "Unknown"))
                district = str(match.iloc[0].get("district", "Unknown"))
        except Exception as e:
            logger.warning(f"Failed to read market metadata: {e}")
    return state, district


def get_current_market_data(commodity: str, market: str) -> CurrentMarketDataResponse:
    """
    Retrieve validated current government mandi record for any commodity and market.
    Does NOT depend on ML prediction models.
    """
    if not commodity or not isinstance(commodity, str) or not market or not isinstance(market, str):
        return CurrentMarketDataResponse(
            status="ERROR",
            commodity=str(commodity),
            market=str(market),
            location={"state": "Unknown", "district": "Unknown"},
            data=None,
            metadata={"source": "NONE", "freshness_status": "NONE", "record_count": 0, "error": "Invalid commodity or market string."}
        )

    state, district = _get_market_location(commodity, market)
    fetcher = CurrentDataFetcher()
    try:
        raw_df, is_live, source_tag = fetcher.fetch_all_current_data(commodity=commodity)
        source = SOURCE_LIVE if is_live else SOURCE_CACHE
    except Exception as e:
        logger.error(f"Error fetching current data: {e}")
        raw_df = pd.DataFrame()
        source = SOURCE_CACHE

    if raw_df.empty:
        return CurrentMarketDataResponse(
            status="SUCCESS",
            commodity=commodity,
            market=market,
            location={"state": state, "district": district},
            data=None,
            metadata={"source": source, "freshness_status": "NONE", "record_count": 0, "warning": f"No current data found for {commodity} in market {market}."}
        )

    # Filter for commodity and market (case-insensitive)
    commodity_col = next((c for c in ["commodity", "Commodity"] if c in raw_df.columns), None)
    market_col = next((m for m in ["market", "Market"] if m in raw_df.columns), None)

    filtered_df = raw_df.copy()
    if commodity_col:
        filtered_df = filtered_df[filtered_df[commodity_col].astype(str).str.lower() == commodity.lower()]
    if market_col:
        filtered_df = filtered_df[filtered_df[market_col].astype(str).str.lower() == market.lower()]

    if filtered_df.empty:
        return CurrentMarketDataResponse(
            status="SUCCESS",
            commodity=commodity,
            market=market,
            location={"state": state, "district": district},
            data=None,
            metadata={"source": source, "freshness_status": "NONE", "record_count": 0, "warning": f"No records found for commodity '{commodity}' in market '{market}'."}
        )

    row = filtered_df.iloc[0]

    # Extract price fields
    modal_price = float(row.get("modal_price", row.get("Modal_Price", 0.0)))
    min_price = float(row.get("min_price", row.get("Min_Price", modal_price)))
    max_price = float(row.get("max_price", row.get("Max_Price", modal_price)))

    arrival_val = row.get("arrival", row.get("Arrival", None))
    arrival = float(arrival_val) if arrival_val is not None and pd.notna(arrival_val) else None

    state_val = str(row.get("state", row.get("State", state)))
    district_val = str(row.get("district", row.get("District", district)))
    date_val = str(row.get("date", row.get("Arrival_Date", datetime.now().strftime("%Y-%m-%d"))))

    # Evaluate data freshness
    obs_date = pd.to_datetime(date_val, errors="coerce")
    is_fresh, freshness_status, age_days = evaluate_data_freshness(obs_date, source)

    warning_msg = ""
    if freshness_status == STATUS_CACHE_STALE:
        warning_msg = f"Current market data for {commodity} {market} is from cached data ({age_days} days old)."

    record = CurrentMarketDataRecord(
        commodity=commodity,
        market=market,
        state=state_val,
        district=district_val,
        date=date_val,
        min_price=min_price,
        max_price=max_price,
        modal_price=modal_price,
        arrival=arrival,
        unit="Rs/quintal"
    )

    return CurrentMarketDataResponse(
        status="SUCCESS",
        commodity=commodity,
        market=market,
        location={"state": state_val, "district": district_val},
        data=record,
        metadata={
            "source": source,
            "freshness_status": freshness_status,
            "data_age_days": age_days,
            "record_count": 1,
            "warning": warning_msg,
        }
    )


def get_historical_market_data(
    commodity: str,
    market: str,
    start_date: str,
    end_date: str
) -> HistoricalMarketDataResponse:
    """
    Retrieve chronologically sorted historical market records between start_date and end_date.
    Format-ready for frontend price charts. Does NOT depend on ML prediction models.
    """
    state, district = _get_market_location(commodity, market)

    # Validate date inputs
    try:
        dt_start = pd.to_datetime(start_date, format="%Y-%m-%d")
        dt_end = pd.to_datetime(end_date, format="%Y-%m-%d")
    except Exception:
        return HistoricalMarketDataResponse(
            status="ERROR",
            commodity=commodity,
            market=market,
            location={"state": state, "district": district},
            date_range={"from": start_date, "to": end_date},
            records=[],
            metadata={"source": "NONE", "record_count": 0, "error": "Invalid date format. Expected YYYY-MM-DD."}
        )

    if dt_start > dt_end:
        return HistoricalMarketDataResponse(
            status="ERROR",
            commodity=commodity,
            market=market,
            location={"state": state, "district": district},
            date_range={"from": start_date, "to": end_date},
            records=[],
            metadata={"source": "NONE", "record_count": 0, "error": "start_date cannot be after end_date."}
        )

    # Search historical data files
    hist_file = PROCESSED_DATA_DIR / f"{commodity.lower()}_{market.lower()}_model.csv"
    raw_hist_file = RAW_DATA_DIR / f"{commodity.lower()}_historical_raw.csv"

    df = pd.DataFrame()
    source = SOURCE_CACHE

    if hist_file.exists():
        try:
            df = pd.read_csv(hist_file)
        except Exception as e:
            logger.warning(f"Could not read {hist_file}: {e}")

    if df.empty and raw_hist_file.exists():
        try:
            df = pd.read_csv(raw_hist_file)
        except Exception as e:
            logger.warning(f"Could not read {raw_hist_file}: {e}")

    if df.empty:
        # Fallback to general mandi_current_raw.csv or current cache files
        fallback_file = RAW_DATA_DIR / "mandi_current_raw.csv"
        if fallback_file.exists():
            try:
                df = pd.read_csv(fallback_file)
            except Exception:
                pass

    if df.empty:
        return HistoricalMarketDataResponse(
            status="SUCCESS",
            commodity=commodity,
            market=market,
            location={"state": state, "district": district},
            date_range={"from": start_date, "to": end_date},
            records=[],
            metadata={"source": source, "record_count": 0, "warning": f"No historical dataset found for {commodity} in market {market}."}
        )

    # Normalize column names case-insensitively
    date_col = next((c for c in df.columns if c.lower() in {"date", "arrival_date", "reported_date"}), None)
    modal_col = next((c for c in df.columns if c.lower() in {"modal_price", "modal"}), None)
    min_col = next((c for c in df.columns if c.lower() in {"min_price", "min"}), None)
    max_col = next((c for c in df.columns if c.lower() in {"max_price", "max"}), None)
    arr_col = next((c for c in df.columns if c.lower() in {"arrival", "arrivals"}), None)
    comm_col = next((c for c in df.columns if c.lower() in {"commodity", "crop"}), None)
    mkt_col = next((c for c in df.columns if c.lower() in {"market", "mandi"}), None)

    if not date_col or not modal_col:
        return HistoricalMarketDataResponse(
            status="ERROR",
            commodity=commodity,
            market=market,
            location={"state": state, "district": district},
            date_range={"from": start_date, "to": end_date},
            records=[],
            metadata={"source": source, "record_count": 0, "error": "Historical file missing required date or modal_price columns."}
        )

    df["dt"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["dt"])

    if comm_col:
        df = df[df[comm_col].astype(str).str.lower() == commodity.lower()]
    if mkt_col:
        df = df[df[mkt_col].astype(str).str.lower() == market.lower()]

    # Filter date range
    df = df[(df["dt"] >= dt_start) & (df["dt"] <= dt_end)]

    if df.empty:
        return HistoricalMarketDataResponse(
            status="SUCCESS",
            commodity=commodity,
            market=market,
            location={"state": state, "district": district},
            date_range={"from": start_date, "to": end_date},
            records=[],
            metadata={"source": source, "record_count": 0, "warning": f"No records found for {commodity} in market {market} between {start_date} and {end_date}."}
        )

    # Sort chronologically and deduplicate by date
    df = df.sort_values(by="dt").drop_duplicates(subset=["dt"], keep="last")

    price_points: List[HistoricalPricePoint] = []
    for _, row in df.iterrows():
        d_str = row["dt"].strftime("%Y-%m-%d")
        modal = float(row[modal_col])
        min_p = float(row[min_col]) if min_col and pd.notna(row[min_col]) else modal
        max_p = float(row[max_col]) if max_col and pd.notna(row[max_col]) else modal

        arr_val = row[arr_col] if arr_col and pd.notna(row[arr_col]) else None
        arr = float(arr_val) if arr_val is not None else None

        price_points.append(HistoricalPricePoint(
            date=d_str,
            min_price=min_p,
            max_price=max_p,
            modal_price=modal,
            arrival=arr
        ))

    return HistoricalMarketDataResponse(
        status="SUCCESS",
        commodity=commodity,
        market=market,
        location={"state": state, "district": district},
        date_range={"from": start_date, "to": end_date},
        records=price_points,
        metadata={
            "source": source,
            "record_count": len(price_points)
        }
    )


def get_available_market_options() -> MarketOptionsResponse:
    """
    Discovery function scanning market metadata and data registries to list all
    available commodities, markets, states, and districts in government data.
    Does NOT restrict results to ML-supported markets.
    """
    commodities = set()
    markets = set()
    states = set()
    districts = set()

    # 1. Read market metadata file if present
    if os.path.exists(MARKET_METADATA_FILE):
        try:
            df = pd.read_csv(MARKET_METADATA_FILE)
            if "commodity" in df.columns:
                commodities.update(df["commodity"].dropna().astype(str).unique())
            if "market" in df.columns:
                markets.update(df["market"].dropna().astype(str).unique())
            if "state" in df.columns:
                states.update(df["state"].dropna().astype(str).unique())
            if "district" in df.columns:
                districts.update(df["district"].dropna().astype(str).unique())
        except Exception as e:
            logger.warning(f"Error reading market_metadata.csv: {e}")

    # 2. Add commodities from CommodityRegistry
    commodities.update(list_registered_commodities())

    # 3. Read raw current dataset if present
    raw_file = RAW_DATA_DIR / "mandi_current_raw.csv"
    if raw_file.exists():
        try:
            df_raw = pd.read_csv(raw_file, nrows=1000)
            if "commodity" in df_raw.columns:
                commodities.update(df_raw["commodity"].dropna().astype(str).unique())
            if "market" in df_raw.columns:
                markets.update(df_raw["market"].dropna().astype(str).unique())
            if "state" in df_raw.columns:
                states.update(df_raw["state"].dropna().astype(str).unique())
            if "district" in df_raw.columns:
                districts.update(df_raw["district"].dropna().astype(str).unique())
        except Exception:
            pass

    return MarketOptionsResponse(
        status="SUCCESS",
        commodities=sorted(list(commodities)),
        markets=sorted(list(markets)),
        states=sorted(list(states)),
        districts=sorted(list(districts))
    )
