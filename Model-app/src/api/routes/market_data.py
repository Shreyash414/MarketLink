"""
Market Data API Routes.
Exposes daily AGMARKNET mandi price data (Live or Cached).
Decoupled from ML inference.
"""
from typing import List, Optional
from fastapi import APIRouter, Query

from src.api.schemas.market_data import MarketDataResponse
from src.services.market_data_service import market_data_service

router = APIRouter(prefix="/api/v1", tags=["Market Data"])


@router.get(
    "/market-data",
    response_model=MarketDataResponse,
    summary="Retrieve Mandi Prices",
    description="Query current daily modal prices and arrivals for a commodity across mandis from live API or cache.",
    responses={
        200: {"description": "Daily mandi prices retrieved successfully"},
        400: {"description": "Invalid query filter parameters"},
        422: {"description": "Request validation error"},
        500: {"description": "Internal server error"},
        502: {"description": "External data.gov.in API unavailable"},
    },
)
def get_market_data(
    commodity: str = Query(default="Onion", description="Commodity name (e.g. Onion, Potato, Tomato, Wheat, Rice)"),
    markets: Optional[List[str]] = Query(default=None, description="Optional target market names filter"),
    state: Optional[str] = Query(default=None, description="Optional state name filter"),
    limit: int = Query(default=50, ge=1, le=500, description="Max records to retrieve"),
):
    result = market_data_service.get_market_data(
        commodity=commodity,
        target_markets=markets,
        state_name=state,
        limit=limit,
    )
    return MarketDataResponse(**result)
