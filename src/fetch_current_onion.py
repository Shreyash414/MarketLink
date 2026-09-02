"""
Production entry point for fetching current Onion market data.
Uses CurrentDataFetcher with pagination, exponential backoff retries, local caching,
and fallback logic.
"""
import sys
from pathlib import Path

from src.data.ingestion.current_data_fetcher import CurrentDataFetcher
from src.utils.logger import logger

TARGET_MARKETS = ["Bareilly", "Bargarh", "Nagpur"]

def main():
    print("\n" + "=" * 70)
    print("CURRENT ONION MARKET DATA INGESTION")
    print("=" * 70)

    fetcher = CurrentDataFetcher()

    df, is_live, source_tag = fetcher.fetch_all_current_data(
        commodity="Onion",
        target_markets=TARGET_MARKETS
    )

    print("\n" + "=" * 70)
    print(f"INGESTION SUMMARY — Source: {source_tag} (Live: {is_live})")
    print("=" * 70)

    if df.empty:
        print("\nERROR: No data available from LIVE API or local cache.")
        sys.exit(1)

    print(f"\nTotal records processed: {len(df)}")
    print("\nSample records:")
    display_cols = [c for c in ["market", "state", "date", "modal_price", "source", "retrieved_at"] if c in df.columns]
    print(df[display_cols].head(10).to_string(index=False))

    print("\n" + "=" * 70)
    print(f"Data saved to: {fetcher.output_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()