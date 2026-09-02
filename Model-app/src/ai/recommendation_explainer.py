"""
Recommendation Explainer Module.
Generates farmer-friendly, transparent, multilingual natural language explanations
for recommendations based strictly on deterministic calculation results.
Implements strict anti-hallucination guardrails: the LLM or template can only present
the exact pre-calculated prices, distances, and net returns.
"""
from typing import Dict, List, Optional

from src.ai.ollama_client import OllamaClient
from src.recommendation.schemas import MandiRecommendationItem, RecommendationResult
from src.utils.logger import logger


class RecommendationExplainer:
    """
    Produces plain-language explanations for farmer decision-making.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()

    def explain(
        self,
        result: RecommendationResult,
        language: str = "English"
    ) -> str:
        """
        Generate decision summary. Uses Ollama when available; otherwise uses deterministic templates.
        """
        if not result.recommendations:
            return (
                f"No suitable mandi recommendations could be found for {result.commodity}. "
                "Please verify market coverage or try increasing your search distance."
            )

        top = result.recommendations[0]
        alternatives = result.recommendations[1:3]

        # Guardrails payload: deterministic numbers only
        facts = {
            "commodity": result.commodity,
            "quantity_quintals": result.quantity_quintals,
            "recommended_mandi": top.mandi,
            "state": top.state,
            "district": top.district,
            "distance_km": top.distance_km,
            "current_price": top.current_price,
            "predicted_price": top.predicted_price,
            "expected_change_pct": top.expected_change_pct,
            "expected_direction": top.expected_direction,
            "transport_cost": top.transport_cost,
            "market_fee": top.market_fee,
            "net_return": top.net_return,
            "net_price_per_quintal": top.net_price_per_quintal,
            "risk_level": top.risk_level,
            "confidence_score": top.confidence_score,
            "warning": top.warning or "None",
            "interval_80": f"Rs.{top.lower_bound_80} - Rs.{top.upper_bound_80}" if top.lower_bound_80 > 0 else "N/A"
        }

        # Try Ollama if available
        if self.ollama.is_available():
            system_prompt = (
                f"You are an empathetic agricultural advisor for Indian farmers. "
                f"Explain the mandi recommendation clearly in {language}. "
                f"CRITICAL RULE: You MUST use ONLY the exact numerical facts provided below. "
                f"DO NOT invent or alter prices, distances, costs, or returns. "
                f"Keep your explanation concise (3-4 bullet points)."
            )
            prompt = f"Explain this recommendation to the farmer using these exact verified facts:\n{facts}"
            llm_text = self.ollama.generate(prompt=prompt, system_prompt=system_prompt)
            if llm_text:
                return llm_text

        # Deterministic Template Fallback (Guaranteed zero-hallucination)
        return self._generate_template_explanation(facts, alternatives, language=language)

    def _generate_template_explanation(
        self,
        facts: Dict,
        alternatives: List[MandiRecommendationItem],
        language: str = "English"
    ) -> str:
        """
        Deterministic, rule-based multilingual explanation.
        """
        if language.lower() == "hindi":
            explanation = (
                f"🌾 **सर्वश्रेष्ठ मंडी सिफारिश: {facts['recommended_mandi']} ({facts['district']}, {facts['state']})**\n\n"
                f"• **अनुमानित शुद्ध लाभ:** ₹{facts['net_return']:,.2f} (₹{facts['net_price_per_quintal']:.2f}/क्विंटल)\n"
                f"• **अनुमानित मूल्य:** ₹{facts['predicted_price']:.2f}/क्विंटल (दिशा: {facts['expected_direction']}, बदलाव: {facts['expected_change_pct']:+.2f}%)\n"
                f"• **परिवहन लागत:** ₹{facts['transport_cost']:.2f} ({facts['distance_km']:.1f} किमी दूरी के लिए)\n"
                f"• **जोखिम स्तर:** {facts['risk_level']} (विश्वास स्कोर: {facts['confidence_score']:.1f}/100)\n"
            )
            if facts["interval_80"] != "N/A":
                explanation += f"• **80% मूल्य सीमा:** {facts['interval_80']}/क्विंटल\n"
            if facts["warning"] != "None":
                explanation += f"⚠️ **सावधानी:** {facts['warning']}\n"
            return explanation

        # Default English Template
        explanation = (
            f"🌾 **Top Mandi Recommendation: {facts['recommended_mandi']} ({facts['district']}, {facts['state']})**\n\n"
            f"• **Expected Net Profit:** Rs.{facts['net_return']:,.2f} (Rs.{facts['net_price_per_quintal']:.2f}/quintal) for your {facts['quantity_quintals']:.1f} quintals.\n"
            f"• **Forecast Price:** Rs.{facts['predicted_price']:.2f}/quintal ({facts['expected_direction']}, {facts['expected_change_pct']:+.2f}% vs today's Rs.{facts['current_price']:.2f}).\n"
            f"• **Transportation:** Rs.{facts['transport_cost']:.2f} total cost over {facts['distance_km']:.1f} km.\n"
            f"• **Risk & Confidence:** {facts['risk_level']} risk level with a confidence score of {facts['confidence_score']:.1f}/100.\n"
        )

        if facts["interval_80"] != "N/A":
            explanation += f"• **Statistical Price Band (80% confidence):** {facts['interval_80']}/quintal.\n"

        if facts["warning"] != "None":
            explanation += f"⚠️ **Risk Advisory:** {facts['warning']}\n"

        if alternatives:
            explanation += "\n**Alternative Markets:**\n"
            for alt in alternatives:
                explanation += f" - {alt.mandi}: Net Return Rs.{alt.net_return:,.2f} at {alt.distance_km:.1f} km (Risk: {alt.risk_level})\n"

        return explanation


if __name__ == "__main__":
    from src.recommendation.mandi_recommender import recommend_mandi
    
    recommender_res = recommend_mandi(
        farmer_latitude=28.6139,
        farmer_longitude=77.2090,
        quantity_quintals=10.0,
        commodity="Onion"
    )

    explainer = RecommendationExplainer()
    print("================================================================================")
    print("RECOMMENDATION EXPLAINER DEMONSTRATION (PHASE 15)")
    print("================================================================================")
    print("\n--- ENGLISH EXPLANATION ---")
    print(explainer.explain(recommender_res, language="English"))
    print("\n--- HINDI EXPLANATION ---")
    print(explainer.explain(recommender_res, language="Hindi"))
