"""
MarketLink AI Service — FastAPI Main Application.
High-throughput inference, asynchronous AMQP worker coordination, Redis job storage, and health probes.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import time
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import (
    health_router,
    market_data_router,
    predictions_router,
    queries_router,
    recommendations_router,
)
from src.core.config import settings
from src.core.exceptions import ModelServiceException, format_error_response
from src.core.redis import redis_client
from src.messaging.connection import rabbitmq_connection
from src.models.model_predictor import get_shared_predictor
from src.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager handling startup initialization and clean shutdown."""
    logger.info("Initializing MarketLink AI Application...")
    start_time = time.time()

    # 1. Warm-up pre-trained ML models into shared process memory
    try:
        predictor = get_shared_predictor()
        load_summary = predictor.preload_models()
        logger.info(f"Pre-loaded models into memory: {load_summary}")
    except Exception as e:
        logger.warning(f"Non-fatal error during model pre-load: {e}")

    # 2. Check Redis connectivity (non-fatal on startup)
    if redis_client.ping():
        logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    else:
        logger.warning(
            f"Redis is not currently reachable at {settings.REDIS_HOST}:{settings.REDIS_PORT}. "
            f"Async job persistence will attempt connection on first request."
        )

    # 3. Check RabbitMQ connectivity (non-fatal on startup)
    if rabbitmq_connection.is_healthy():
        logger.info(f"Connected to RabbitMQ at {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")
    else:
        logger.warning(
            f"RabbitMQ is not currently reachable at {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}. "
            f"Async jobs will fail with 503 until broker is online."
        )

    logger.info(f"Application startup complete in {(time.time() - start_time):.2f}s")
    yield

    # Clean shutdown
    logger.info("Shutting down MarketLink AI Application...")
    try:
        redis_client.close()
    except Exception as e:
        logger.warning(f"Error disconnecting Redis: {e}")

    try:
        rabbitmq_connection.close()
    except Exception as e:
        logger.warning(f"Error disconnecting RabbitMQ: {e}")
    logger.info("Application teardown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade AI/ML Mandi Recommendation, XGBoost Price Forecasting, and Redis Job Storage.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware with explicit allowed origins / regex for security & usability
cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.CORS_ORIGINS:
    cors_kwargs["allow_origins"] = settings.CORS_ORIGINS
if settings.CORS_ORIGIN_REGEX:
    cors_kwargs["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX

app.add_middleware(CORSMiddleware, **cors_kwargs)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request timing and correlation headers."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    return response


# Centralized domain exception handler
@app.exception_handler(ModelServiceException)
async def domain_exception_handler(request: Request, exc: ModelServiceException):
    logger.warning(f"Domain exception on {request.url.path}: [{exc.error_code}] {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc),
    )


# Request validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request payload failed schema validation.",
                "details": exc.errors(),
            }
        },
    )


# Generic HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP exception on {request.url.path}: [{exc.status_code}] {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
            }
        },
    )


# Unhandled internal server error handler (prevents leaking stack traces or internal secrets)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
            }
        },
    )



# Include API Routers
app.include_router(health_router)
app.include_router(recommendations_router)
app.include_router(predictions_router)
app.include_router(market_data_router)
app.include_router(queries_router)
