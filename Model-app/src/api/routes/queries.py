"""
General Natural Language Query API Routes.
Exposes Ollama LLM queries, intent parsing, and natural language advice.
"""
from fastapi import APIRouter

from src.api.schemas.query import GeneralQueryRequest, GeneralQueryResponse
from src.services.ollama_service import ollama_service

router = APIRouter(prefix="/api/v1", tags=["General LLM Queries"])


@router.post(
    "/query",
    response_model=GeneralQueryResponse,
    summary="Natural Language Agricultural Query",
    description="Processes raw farmer natural-language text to extract trade intent and provide LLM/deterministic guidance.",
    responses={
        200: {"description": "Natural language query processed successfully"},
        400: {"description": "Invalid input query"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
        502: {"description": "Upstream Ollama LLM generation error"},
        503: {"description": "Ollama LLM daemon offline or unreachable"},
    },
)
def process_general_query(req: GeneralQueryRequest):
    result = ollama_service.process_query(
        query_text=req.query,
        language=req.language,
    )
    return GeneralQueryResponse(**result)
