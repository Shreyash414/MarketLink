"""
Ollama Service Automated Test Suite.
Tests LLM generation, intent extraction, and graceful offline fallback.
"""
from unittest.mock import MagicMock
import unittest

from src.ai.intent_parser import ParsedFarmerIntent
from src.ai.ollama_client import OllamaClient
from src.services.ollama_service import OllamaService


class TestOllamaService(unittest.TestCase):

    def test_01_ollama_online_generation(self):
        """Verify OllamaService queries local LLM when online."""
        service = OllamaService()
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.is_available.return_value = True
        mock_client.generate.return_value = "Onion modal price in Bareilly is currently around 1850 Rs/quintal."
        service.client = mock_client
        service.intent_parser = MagicMock()
        service.intent_parser.parse.return_value = ParsedFarmerIntent(
            commodity="Onion",
            quantity_quintals=0.0,
            location_name="Bareilly",
        )

        result = service.process_query("What is onion price in Bareilly?")
        self.assertEqual(result["source"], "OLLAMA_LLM")
        self.assertTrue(result["ollama_online"])
        self.assertEqual(result["detected_commodity"], "Onion")
        self.assertIn("1850", result["response"])

    def test_02_ollama_offline_controlled_failure(self):
        """Verify OllamaService raises OllamaServiceException (503) when LLM daemon is offline."""
        from src.core.exceptions import OllamaServiceException

        service = OllamaService()
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.is_available.return_value = False
        service.client = mock_client
        service.intent_parser = MagicMock()
        service.intent_parser.parse.return_value = ParsedFarmerIntent(
            commodity="Onion",
            quantity_quintals=0.0,
            location_name="Bareilly",
        )

        with self.assertRaises(OllamaServiceException) as ctx:
            service.process_query("What is onion price in Bareilly?")
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.error_code, "OLLAMA_SERVICE_ERROR")


if __name__ == "__main__":
    unittest.main()

