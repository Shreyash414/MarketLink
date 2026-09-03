"""API Routes package."""
from src.api.routes.health import router as health_router
from src.api.routes.recommendations import router as recommendations_router
from src.api.routes.predictions import router as predictions_router
from src.api.routes.market_data import router as market_data_router
from src.api.routes.queries import router as queries_router

__all__ = [
    "health_router",
    "recommendations_router",
    "predictions_router",
    "market_data_router",
    "queries_router",
]
