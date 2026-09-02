"""
Ollama Client & Natural Language Intelligence Wrapper.
Provides robust connection to local Ollama LLM with timeout handling,
deterministic numerical guardrails, and graceful offline fallback.
"""
import json
import os
import requests
from typing import Any, Dict, List, Optional

from src.utils.logger import logger

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


class OllamaClient:
    """
    Client for interacting with local Ollama service.
    Designed with fast timeouts and graceful fallbacks when Ollama is offline.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        timeout_seconds: int = 5
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout_seconds

    def is_available(self) -> bool:
        """Check if local Ollama service is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Optional[str]:
        """
        Generate completion from Ollama. Returns None if unreachable.
        """
        if not self.is_available():
            logger.warning("Ollama daemon is currently offline. Engaging deterministic fallback.")
            return None

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return None
        except Exception as e:
            logger.warning(f"Ollama request failed: {e}. Falling back to deterministic templates.")
            return None
