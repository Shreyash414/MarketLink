"""
Pydantic schemas for natural language queries and Ollama Q&A.
"""
from typing import Optional
from pydantic import BaseModel, Field


class GeneralQueryRequest(BaseModel):
    query: str = Field(..., description="Farmer natural language query", examples=["What is onion price in Bareilly?"])
    language: str = Field(default="en", description="Language code (en, hi, etc.)", examples=["en"])


class GeneralQueryResponse(BaseModel):
    query: str
    language: str
    intent: str
    detected_commodity: Optional[str] = None
    detected_location: Optional[str] = None
    response: str
    source: str
    ollama_online: bool
