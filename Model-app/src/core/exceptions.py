"""
Centralized domain exceptions and safe error payload formatting for MarketLink AI Service.
Prevents leaking internal stack traces, paths, or secrets to external callers.
"""
import re
from typing import Any, Dict, Optional


class ModelServiceException(Exception):
    """Base exception for all AI/ML service domain errors."""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


class InvalidInputException(ModelServiceException):
    """Raised when client input data violates validation constraints."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, error_code="INVALID_INPUT", status_code=400, details=details)


class ArtifactNotFoundException(ModelServiceException):
    """Raised when an expected model or metadata artifact is missing on disk."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, error_code="ARTIFACT_NOT_FOUND", status_code=500, details=details)


class ModelUnavailableException(ModelServiceException):
    """Raised when a model is disabled, missing, or blocked by quality gate."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, error_code="MODEL_UNAVAILABLE", status_code=503, details=details)


class MessagingException(ModelServiceException):
    """Raised when RabbitMQ operations fail."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, error_code="MESSAGING_ERROR", status_code=503, details=details)


class RedisStorageException(ModelServiceException):
    """Raised when Redis job storage operations fail."""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, error_code="REDIS_STORAGE_ERROR", status_code=503, details=details)


class JobNotFoundException(ModelServiceException):
    """Raised when a requested async job_id is not found in the storage layer."""
    def __init__(self, job_id: str):
        super().__init__(f"Job with ID '{job_id}' not found.", error_code="JOB_NOT_FOUND", status_code=404)
        self.job_id = job_id


class OllamaServiceException(ModelServiceException):
    """Raised when Ollama LLM queries fail or time out."""
    def __init__(self, message: str, status_code: int = 502, details: Optional[Any] = None):
        super().__init__(message, error_code="OLLAMA_SERVICE_ERROR", status_code=status_code, details=details)


def _sanitize_message(text: str) -> str:
    """Sanitize server filesystem paths and sensitive credentials from error messages."""
    if not isinstance(text, str):
        return str(text)
    # Mask absolute filesystem paths
    sanitized = re.sub(r"/(?:[\w.-]+/)+[\w.-]+", "[SANITIZED_PATH]", text)
    return sanitized


def format_error_response(exc: ModelServiceException) -> Dict[str, Any]:
    """Format standardized, safe error dictionary for JSON responses."""
    safe_message = _sanitize_message(exc.message)
    resp: Dict[str, Any] = {
        "error": {
            "code": exc.error_code,
            "message": safe_message,
        }
    }
    if exc.details is not None:
        if isinstance(exc.details, str):
            resp["error"]["details"] = _sanitize_message(exc.details)
        else:
            resp["error"]["details"] = exc.details
    return resp

