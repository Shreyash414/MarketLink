"""
Pydantic schemas for asynchronous ML jobs and polling.
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AsyncJobSubmitResponse(BaseModel):
    job_id: str = Field(..., description="Unique correlation identifier for the async job")
    status: str = Field(default="QUEUED", description="Current lifecycle state of job")
    operation: str = Field(..., description="Target operation type", examples=["RECOMMEND_MANDI"])
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    message: str = "Job accepted and enqueued for processing."


class JobStatusResponse(BaseModel):
    job_id: str = Field(..., description="Unique correlation identifier")
    status: str = Field(..., description="Current status: QUEUED | PROCESSING | COMPLETED | FAILED")
    operation: str = Field(..., description="Target operation type")
    created_at: str = Field(..., description="Job creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    completed_at: Optional[str] = Field(default=None, description="Completion timestamp if terminal")
    result: Optional[Dict[str, Any]] = Field(default=None, description="ML output payload if status is COMPLETED")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error details if status is FAILED")
