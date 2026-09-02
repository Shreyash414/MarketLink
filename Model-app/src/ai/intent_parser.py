"""
Farmer Query Intent Parser.
Extracts structured query parameters (commodity, quantity_quintals, location)
from raw natural language voice/text input.
Uses Ollama when available with regex/keyword deterministic fallback.
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.ai.ollama_client import OllamaClient
from src.config.commodity_registry import list_registered_commodities
from src.utils.logger import logger


@dataclass
class ParsedFarmerIntent:
    commodity: str
    quantity_quintals: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    extraction_method: str = "DETERMINISTIC_RULES"


KNOWN_LOCATION_COORDINATES: Dict[str, Tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "bareilly": (28.3670, 79.4304),
    "agra": (27.1767, 78.0081),
    "nagpur": (21.1458, 79.0882),
    "kolar": (13.1367, 78.1291),
    "khanna": (30.7055, 76.2216),
    "burdwan": (23.2324, 87.8615),
    "nashik": (19.9975, 73.7898),
    "bargarh": (21.3333, 83.6167),
}


class FarmerIntentParser:
    """
    Parses conversational farmer inputs into structured recommendation inputs.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()

    def parse(self, text: str) -> ParsedFarmerIntent:
        """
        Parse raw farmer text query into structured parameters.
        """
        text_clean = text.strip()

        # Try Ollama extraction if online
        if self.ollama.is_available():
            system_prompt = (
                "You are an agricultural intent parser. Extract the crop/commodity, quantity in quintals, "
                "and location from the user message. Output JSON ONLY with keys: commodity, quantity_quintals, location."
            )
            prompt = f"Extract parameters from this farmer query: '{text_clean}'"
            response = self.ollama.generate(prompt=prompt, system_prompt=system_prompt)
            if response:
                try:
                    import json
                    # Clean markdown codeblocks if present
                    clean_json = re.sub(r"```json|```", "", response).strip()
                    data = json.loads(clean_json)
                    comm = str(data.get("commodity", "Onion")).strip().capitalize()
                    qty = float(data.get("quantity_quintals", 10.0))
                    loc = str(data.get("location", "Delhi")).strip().lower()
                    
                    coords = KNOWN_LOCATION_COORDINATES.get(loc, (28.6139, 77.2090))
                    return ParsedFarmerIntent(
                        commodity=comm,
                        quantity_quintals=qty,
                        latitude=coords[0],
                        longitude=coords[1],
                        location_name=loc.capitalize(),
                        extraction_method="OLLAMA_LLM"
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse Ollama JSON response: {e}. Falling back to rules.")

        # Deterministic Regex Fallback
        return self._parse_deterministic(text_clean)

    def _parse_deterministic(self, text: str) -> ParsedFarmerIntent:
        text_lower = text.lower()

        # 1. Match Commodity
        registered = [c.lower() for c in list_registered_commodities()] + [
            "potato", "tomato", "wheat", "rice", "paddy", "brinjal", "bhindi", "garlic"
        ]
        matched_commodity = "Onion"
        for c in registered:
            if c in text_lower:
                matched_commodity = c.capitalize()
                break

        # 2. Match Quantity
        # Patterns: "10 quintals", "15 q", "5 quintal", "20 bags", "100 kg"
        qty = 10.0
        q_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:quintals?|quintal|qtl|q\b)", text_lower)
        if q_match:
            qty = float(q_match.group(1))
        else:
            kg_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilos?)\b", text_lower)
            if kg_match:
                qty = float(kg_match.group(1)) / 100.0  # Convert kg to quintals
            else:
                num_match = re.search(r"\b(\d+(?:\.\d+)?)\b", text_lower)
                if num_match:
                    qty = float(num_match.group(1))

        # 3. Match Location
        matched_loc = "Delhi"
        coords = (28.6139, 77.2090)
        for loc_name, loc_coords in KNOWN_LOCATION_COORDINATES.items():
            if loc_name in text_lower:
                matched_loc = loc_name.capitalize()
                coords = loc_coords
                break

        return ParsedFarmerIntent(
            commodity=matched_commodity,
            quantity_quintals=max(1.0, qty),
            latitude=coords[0],
            longitude=coords[1],
            location_name=matched_loc,
            extraction_method="DETERMINISTIC_RULES"
        )


if __name__ == "__main__":
    parser = FarmerIntentParser()
    queries = [
        "I have 15 quintals of Potato near Agra, where should I sell?",
        "Selling 20 quintal wheat in Khanna area",
        "Where to take 500 kg tomato from Kolar?",
        "Recommend mandi for Onion in Bareilly with 25 quintals"
    ]

    print("================================================================================")
    print("FARMER INTENT PARSING DEMONSTRATION (PHASE 15)")
    print("================================================================================")
    for q in queries:
        res = parser.parse(q)
        print(f"\nQuery: '{q}'")
        print(f" -> Commodity: {res.commodity} | Quantity: {res.quantity_quintals} q | Location: {res.location_name} {res.latitude, res.longitude} | Method: {res.extraction_method}")
