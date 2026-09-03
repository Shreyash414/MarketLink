"""
Health and Readiness Probes.
Distinguishes process liveness (/health) from infrastructure readiness (/ready) including Redis and RabbitMQ.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Response, status

from src.api.schemas.health import HealthResponse, ReadinessResponse
from src.core.redis import redis_client
from src.messaging.connection import rabbitmq_connection
from src.models.model_predictor import get_shared_predictor

router = APIRouter(tags=["Health & Monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness Probe",
    description="Confirms that the FastAPI application process is up and responding.",
    responses={
        200: {"description": "FastAPI application process is alive and responding"},
    },
)
def get_liveness():
    return HealthResponse(
        status="HEALTHY",
        service="marketlink-ai",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Validates that required external infrastructure (Redis, RabbitMQ, ML Predictor) is connected and operational.",
    responses={
        200: {"description": "All required dependencies are operational to accept workloads"},
        503: {"description": "One or more required dependencies are down, preventing workload processing"},
    },
)
def get_readiness(response: Response):
    redis_ok = redis_client.ping()
    rabbitmq_ok = rabbitmq_connection.is_healthy()
    predictor_ok = get_shared_predictor() is not None

    all_ready = redis_ok and rabbitmq_ok and predictor_ok

    dep_status = {
        "redis": {
            "available": redis_ok,
            "status": "UP" if redis_ok else "DOWN",
        },
        "rabbitmq": {
            "available": rabbitmq_ok,
            "status": "UP" if rabbitmq_ok else "DOWN",
        },
        "ml_predictor": {
            "available": predictor_ok,
            "status": "UP" if predictor_ok else "DOWN",
        },
    }

    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        ready=all_ready,
        status="READY" if all_ready else "NOT_READY",
        dependencies=dep_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
