"""
Mandi Recommendation API Routes.
Exposes direct synchronous evaluation, asynchronous RabbitMQ+Redis job execution,
and Redis-backed job status polling.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status

from src.api.schemas.jobs import AsyncJobSubmitResponse, JobStatusResponse
from src.api.schemas.recommendation import (
    MandiRecommendationRequest,
    MandiRecommendationResponse,
)
from src.core.exceptions import JobNotFoundException
from src.services.job_service import job_service
from src.services.ml_service import ml_service

router = APIRouter(prefix="/api/v1", tags=["Mandi Recommendations"])


@router.post(
    "/recommend",
    response_model=MandiRecommendationResponse,
    summary="Synchronous Mandi Recommendation",
    description="Directly runs the ML recommendation pipeline using in-memory pre-loaded models.",
    responses={
        200: {"description": "Mandi recommendations successfully generated"},
        400: {"description": "Invalid input parameters (e.g. non-positive quantity)"},
        422: {"description": "Validation error (e.g. invalid latitude/longitude range)"},
        500: {"description": "Inference failure or missing artifact"},
        503: {"description": "ML model service unavailable"},
    },
)
def get_synchronous_recommendation(req: MandiRecommendationRequest):
    canonical = ml_service.get_recommendation(
        farmer_latitude=req.farmer_latitude,
        farmer_longitude=req.farmer_longitude,
        quantity_quintals=req.quantity_quintals,
        commodity=req.commodity,
        max_distance_km=req.max_distance_km,
        transport_rate=req.transport_rate,
        farmer_facing=req.farmer_facing,
    )
    return canonical.to_dict()


@router.post(
    "/recommend/async",
    response_model=AsyncJobSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronous Mandi Recommendation",
    description=(
        "Accepts and enqueues an ML recommendation job to RabbitMQ with Redis tracking. "
        "Returns HTTP 202 Accepted with a unique job_id for polling. Does not imply completion."
    ),
    responses={
        202: {"description": "Job successfully accepted and enqueued for asynchronous execution"},
        400: {"description": "Invalid input parameters"},
        422: {"description": "Request validation error"},
        503: {"description": "Asynchronous job broker or storage unavailable"},
    },
)
def submit_asynchronous_recommendation(req: MandiRecommendationRequest):
    payload = req.model_dump()
    job_id = job_service.submit_job(
        operation="RECOMMEND_MANDI",
        payload=payload,
    )
    return AsyncJobSubmitResponse(
        job_id=job_id,
        status="QUEUED",
        operation="RECOMMEND_MANDI",
        created_at=datetime.now(timezone.utc).isoformat(),
        message="Job successfully enqueued for processing.",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll Asynchronous Job Status",
    description="Retrieves the current execution lifecycle state and result of an async job directly from Redis.",
    responses={
        200: {"description": "Job state and result retrieved successfully"},
        404: {"description": "Job ID not found in storage"},
        503: {"description": "Redis job storage unavailable"},
    },
)
def get_job_status(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise JobNotFoundException(job_id)
    return JobStatusResponse(**job)

