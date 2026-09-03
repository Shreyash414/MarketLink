"""
Job Tracking Service for Asynchronous ML Jobs.
Coordinates job lifecycle operations using an injected JobRepository.
Redis is the sole authoritative persistence layer. No competing in-memory store is used.
Follows Dependency Inversion Principle (DIP) and Single Responsibility Principle (SRP).
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.core.exceptions import JobNotFoundException
from src.repositories.job_repository import JobRepository
from src.repositories.redis_job_repository import RedisJobRepository
from src.utils.logger import logger


class JobService:
    """Business service orchestrating async job state transitions and queries."""

    def __init__(self, repository: Optional[JobRepository] = None):
        self._repository = repository or RedisJobRepository()

    @property
    def repository(self) -> JobRepository:
        """Access the underlying persistence repository."""
        return self._repository

    def create_job(self, job_id: str, operation: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Register a newly submitted asynchronous job as QUEUED."""
        now = datetime.now(timezone.utc).isoformat()
        job_record = {
            "job_id": job_id,
            "status": "QUEUED",
            "operation": operation,
            "payload": payload or {},
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "result": None,
            "error": None,
        }
        self._repository.create_job(job_record)
        logger.info(f"Registered async job '{job_id}' (operation={operation}) in Redis [QUEUED]")
        return job_record

    def set_processing(self, job_id: str) -> None:
        """Mark job as currently being processed by a worker."""
        now = datetime.now(timezone.utc).isoformat()
        updated = self._repository.update_job(
            job_id,
            {
                "status": "PROCESSING",
                "updated_at": now,
            },
        )
        if not updated:
            logger.warning(f"Attempted to set status to PROCESSING for non-existent job '{job_id}'")
        else:
            logger.info(f"Job '{job_id}' transitioned to [PROCESSING] in Redis")

    def set_completed(self, job_id: str, result: Dict[str, Any]) -> None:
        """Mark job as successfully completed with payload."""
        now = datetime.now(timezone.utc).isoformat()
        updated = self._repository.update_job(
            job_id,
            {
                "status": "COMPLETED",
                "result": result,
                "updated_at": now,
                "completed_at": now,
            },
        )
        if not updated:
            logger.warning(f"Attempted to set status to COMPLETED for non-existent job '{job_id}'")
        else:
            logger.info(f"Job '{job_id}' transitioned to [COMPLETED] in Redis")

    def set_failed(self, job_id: str, error_message: str, error_details: Optional[Any] = None) -> None:
        """Mark job as failed with error details."""
        now = datetime.now(timezone.utc).isoformat()
        error_payload = {
            "message": error_message,
            "details": error_details,
            "failed_at": now,
        }
        updated = self._repository.update_job(
            job_id,
            {
                "status": "FAILED",
                "error": error_payload,
                "updated_at": now,
                "completed_at": now,
            },
        )
        if not updated:
            logger.warning(f"Attempted to set status to FAILED for non-existent job '{job_id}'")
        else:
            logger.warning(f"Job '{job_id}' transitioned to [FAILED] in Redis: {error_message}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job data by ID."""
        return self._repository.get_job(job_id)

    def get_job_or_raise(self, job_id: str) -> Dict[str, Any]:
        """Retrieve job data or raise JobNotFoundException."""
        job = self.get_job(job_id)
        if not job:
            raise JobNotFoundException(job_id)
        return job

    def job_exists(self, job_id: str) -> bool:
        """Check if job exists in Redis."""
        return self._repository.job_exists(job_id)

    def submit_job(
        self,
        operation: str,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Orchestrate submission of an asynchronous task:
        Generates unique correlation ID, registers initial QUEUED state,
        and delegates persistent enqueueing to RabbitMQ.
        Returns the unique job_id.
        """
        from src.messaging.producer.publisher import producer
        return producer.publish_job(
            operation=operation,
            payload=payload or {},
            correlation_id=correlation_id,
        )


# Singleton job service instance using default RedisJobRepository
job_service = JobService()
