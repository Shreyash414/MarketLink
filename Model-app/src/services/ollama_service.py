"""
Ollama Service.
Wraps the existing OllamaClient with intent detection and structured LLM advice.
Enforces controlled error handling when Ollama daemon is offline or fails without fabricating answers.
"""
from typing import Any, Dict, Optional

from src.ai.intent_parser import FarmerIntentParser
from src.ai.ollama_client import OllamaClient
from src.core.config import settings
from src.core.exceptions import OllamaServiceException
from src.utils.logger import logger


class OllamaService:
    """Service providing natural language intent parsing and agricultural Q&A."""

    def __init__(self):
        self.client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )
        self.intent_parser = FarmerIntentParser(ollama_client=self.client)

    def process_query(self, query_text: str, language: str = "en") -> Dict[str, Any]:
        """
        Process farmer's natural-language query via Ollama.
        Raises controlled OllamaServiceException if Ollama daemon is offline or fails.
        Does NOT fabricate synthetic or heuristic fallback answers.
        """
        if not self.client.is_available():
            logger.warning("Ollama service query rejected: Ollama daemon is currently offline/unreachable.")
            raise OllamaServiceException(
                "Ollama LLM service is currently offline or unreachable.",
                status_code=503,
            )

        parsed_intent = self.intent_parser.parse(query_text)

        try:
            system_prompt = (
                "You are MarketLink AI, an expert agricultural market advisor for Indian farmers. "
                "Provide practical, concise, and actionable guidance on mandi prices, timing, and economics."
            )
            llm_response = self.client.generate(
                prompt=query_text,
                system_prompt=system_prompt,
                temperature=0.3,
            )
            if not llm_response:
                raise OllamaServiceException(
                    "Ollama returned an empty response.",
                    status_code=502,
                )
        except OllamaServiceException:
            raise
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise OllamaServiceException(
                "Ollama LLM generation encountered an upstream error.",
                status_code=502,
            )

        return {
            "query": query_text,
            "language": language,
            "intent": "RECOMMENDATION" if parsed_intent.quantity_quintals > 0 else "PRICE_CHECK",
            "detected_commodity": parsed_intent.commodity,
            "detected_location": parsed_intent.location_name,
            "response": llm_response,
            "source": "OLLAMA_LLM",
            "ollama_online": True,
        }


ollama_service = OllamaService()

