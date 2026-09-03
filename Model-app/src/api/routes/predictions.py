"""
Single Market Prediction API Routes.
Directly executes price forecasting using the shared ModelPredictor.
"""
from fastapi import APIRouter

from src.api.schemas.prediction import (
    SinglePredictionRequest,
    SinglePredictionResponse,
)
from src.services.ml_service import ml_service

router = APIRouter(prefix="/api/v1", tags=["ML Predictions"])


@router.post(
    "/predict",
    response_model=SinglePredictionResponse,
    summary="Direct Single-Market Price Prediction",
    description="Forecasts next-day modal price for a specific mandi and commodity using the trained XGBoost model.",
    responses={
        200: {"description": "Next-day price prediction generated successfully"},
        400: {"description": "Invalid input features or non-positive price"},
        404: {"description": "Model or market not found"},
        422: {"description": "Validation error"},
        500: {"description": "Prediction failure or missing model artifacts"},
        503: {"description": "Model unavailable or blocked by quality gate"},
    },
)
def predict_single_mandi(req: SinglePredictionRequest):
    pred_dict = ml_service.predict_single(
        market=req.market,
        commodity=req.commodity,
        current_price=req.current_price,
        features=req.features,
        date=req.date,
        farmer_facing=req.farmer_facing,
    )
    return SinglePredictionResponse(**pred_dict)
