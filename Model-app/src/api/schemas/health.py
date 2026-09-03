"""
Pydantic schemas for health and readiness probes.
"""
from typing import Any, Dict
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="HEALTHY", examples=["HEALTHY"])
    service: str = Field(default="marketlink-ai")
    version: str = Field(default="1.0.0")
    timestamp: str


class ReadinessResponse(BaseModel):
    ready: bool
    status: str = Field(examples=["READY"])
    dependencies: Dict[str, Any]
    timestamp: str
