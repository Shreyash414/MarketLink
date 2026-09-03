"""
Centralized Application and Infrastructure Configuration for MarketLink AI Service.
Integrates FastAPI, Redis, RabbitMQ, Ollama, and filesystem paths.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from src.config.config import (
    API_BASE_URL,
    DATA_GOV_API_KEY,
    DEFAULT_COMMODITY,
    DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM,
    MARKET_METADATA_FILE,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    ROOT_DIR,
)
from src.config.model_registry import MODEL_REGISTRY_FILE


class ServiceSettings(BaseModel):
    # Server configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "MarketLink AI Service"
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    CORS_ORIGINS: list = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        ]
    )
    CORS_ORIGIN_REGEX: Optional[str] = Field(default=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")

    # Redis Job Storage Configuration (Phase 1B)
    REDIS_URL: Optional[str] = Field(default=None)
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_SOCKET_TIMEOUT: float = Field(default=3.0)
    REDIS_SOCKET_CONNECT_TIMEOUT: float = Field(default=3.0)
    REDIS_JOB_TTL_SECONDS: int = Field(default=86400)  # 24 hours retention for completed/failed jobs
    REDIS_KEY_PREFIX: str = Field(default="marketlink:job")

    # RabbitMQ configuration
    RABBITMQ_HOST: str = Field(default="localhost")
    RABBITMQ_PORT: int = Field(default=5672)
    RABBITMQ_USER: str = Field(default="guest")
    RABBITMQ_PASSWORD: str = Field(default="guest")
    RABBITMQ_VHOST: str = Field(default="/")
    RABBITMQ_EXCHANGE: str = Field(default="marketlink.ai.exchange")
    RABBITMQ_QUEUE: str = Field(default="marketlink.ai.jobs")
    RABBITMQ_ROUTING_KEY: str = Field(default="ai.job.request")
    RABBITMQ_DLQ_EXCHANGE: str = Field(default="marketlink.ai.dlx")
    RABBITMQ_DLQ_QUEUE: str = Field(default="marketlink.ai.jobs.dlq")
    RABBITMQ_DLQ_ROUTING_KEY: str = Field(default="ai.job.dlq")
    RABBITMQ_MAX_RETRIES: int = Field(default=3)
    RABBITMQ_PREFETCH_COUNT: int = Field(default=1)

    # Ollama integration
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama3")
    OLLAMA_CONNECT_TIMEOUT: float = Field(default=3.0)
    OLLAMA_READ_TIMEOUT: float = Field(default=30.0)

    # Re-exported domain constants
    ROOT_DIR: Path = ROOT_DIR
    DATA_DIR: Path = ROOT_DIR / "data"
    PROCESSED_DATA_DIR: Path = PROCESSED_DATA_DIR
    RAW_DATA_DIR: Path = RAW_DATA_DIR
    MARKET_METADATA_FILE: Path = MARKET_METADATA_FILE
    MODEL_REGISTRY_FILE: Path = MODEL_REGISTRY_FILE
    DATA_GOV_API_KEY: Optional[str] = DATA_GOV_API_KEY
    API_BASE_URL: str = API_BASE_URL
    DEFAULT_COMMODITY: str = DEFAULT_COMMODITY
    DEFAULT_TRANSPORT_RATE: float = DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        """Load configuration dynamically from environment variables with sensible defaults."""
        return cls(
            DEBUG=os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
            HOST=os.getenv("HOST", "0.0.0.0"),
            PORT=int(os.getenv("PORT", "8000")),
            CORS_ORIGINS=[o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()] or [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8080",
            ],
            CORS_ORIGIN_REGEX=os.getenv("CORS_ORIGIN_REGEX", r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"),
            # Redis
            REDIS_URL=os.getenv("REDIS_URL"),
            REDIS_HOST=os.getenv("REDIS_HOST", "localhost"),
            REDIS_PORT=int(os.getenv("REDIS_PORT", "6379")),
            REDIS_DB=int(os.getenv("REDIS_DB", "0")),
            REDIS_PASSWORD=os.getenv("REDIS_PASSWORD"),
            REDIS_JOB_TTL_SECONDS=int(os.getenv("REDIS_JOB_TTL_SECONDS", "86400")),
            REDIS_KEY_PREFIX=os.getenv("REDIS_KEY_PREFIX", "marketlink:job"),
            # RabbitMQ
            RABBITMQ_HOST=os.getenv("RABBITMQ_HOST", "localhost"),
            RABBITMQ_PORT=int(os.getenv("RABBITMQ_PORT", "5672")),
            RABBITMQ_USER=os.getenv("RABBITMQ_USER", "guest"),
            RABBITMQ_PASSWORD=os.getenv("RABBITMQ_PASSWORD", "guest"),
            RABBITMQ_VHOST=os.getenv("RABBITMQ_VHOST", "/"),
            RABBITMQ_EXCHANGE=os.getenv("RABBITMQ_EXCHANGE", "marketlink.ai.exchange"),
            RABBITMQ_QUEUE=os.getenv("RABBITMQ_QUEUE", "marketlink.ai.jobs"),
            RABBITMQ_ROUTING_KEY=os.getenv("RABBITMQ_ROUTING_KEY", "ai.job.request"),
            RABBITMQ_DLQ_EXCHANGE=os.getenv("RABBITMQ_DLQ_EXCHANGE", "marketlink.ai.dlx"),
            RABBITMQ_DLQ_QUEUE=os.getenv("RABBITMQ_DLQ_QUEUE", "marketlink.ai.jobs.dlq"),
            RABBITMQ_DLQ_ROUTING_KEY=os.getenv("RABBITMQ_DLQ_ROUTING_KEY", "ai.job.dlq"),
            RABBITMQ_MAX_RETRIES=int(os.getenv("RABBITMQ_MAX_RETRIES", "3")),
            RABBITMQ_PREFETCH_COUNT=int(os.getenv("RABBITMQ_PREFETCH_COUNT", "1")),
            # Ollama
            OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            OLLAMA_MODEL=os.getenv("OLLAMA_MODEL", "llama3"),
        )


settings = ServiceSettings.from_env()
