"""
Production CLI entry point and wrapper for Farmer Mandi Recommendation Engine.
Integrates live/current API data, V3 ML forecasting, transparent risk scoring, and economics.
"""
import pandas as pd
from src.recommendation.mandi_recommender import recommend_mandi as engine_recommend_mandi
from src.recommendation.schemas import RecommendationResult


def recommend_mandi(
    farmer_latitude: float,
    farmer_longitude: float,
    quantity_quintals: float,
    commodity: str = "Onion",
    max_distance_km: float = None,
    transport_rate: float = 3.0
) -> pd.DataFrame:
    """
    Recommend the best mandi for a farmer.

    Returns DataFrame representation of ranked recommendations.
    """
    result: RecommendationResult = engine_recommend_mandi(
        farmer_latitude=farmer_latitude,
        farmer_longitude=farmer_longitude,
        quantity_quintals=quantity_quintals,
        commodity=commodity,
        max_distance_km=max_distance_km,
        transport_rate=transport_rate
    )

    if not result.recommendations:
        return pd.DataFrame()

    df = pd.DataFrame([rec.to_dict() for rec in result.recommendations])
    return df


if __name__ == "__main__":
    # Example farmer input
    farmer_latitude = 28.6139
    farmer_longitude = 77.2090
    quantity = 10.0

    print("\n" + "=" * 70)
    print("FARMER MANDI RECOMMENDATION ENGINE (PRODUCTION)")
    print("=" * 70)
    print(f"\nFarmer Location : ({farmer_latitude}, {farmer_longitude})")
    print(f"Quantity        : {quantity} quintals")
    print(f"Commodity       : Onion")  # Default CLI demo uses Onion; pass --commodity to change

    recommendations_df = recommend_mandi(
        farmer_latitude=farmer_latitude,
        farmer_longitude=farmer_longitude,
        quantity_quintals=quantity
    )

    if recommendations_df.empty:
        print("\nNo recommendations could be generated.")
    else:
        print("\nMandi Ranking Summary:\n")
        display_columns = [
            "rank",
            "mandi",
            "distance_km",
            "current_price",
            "predicted_price",
            "expected_change_pct",
            "transport_cost",
            "net_return",
            "net_price_per_quintal",
            "risk_level",
            "confidence_score",
            "recommendation_label"
        ]
        available_cols = [c for c in display_columns if c in recommendations_df.columns]
        print(recommendations_df[available_cols].to_string(index=False))

        best = recommendations_df.iloc[0]
        print("\n" + "=" * 70)
        print("TOP MANDI RECOMMENDATION DETAILS")
        print("=" * 70)
        print(f"\nRecommended Mandi : {best['mandi']} ({best['state']}, {best['district']})")
        print(f"Distance          : {best['distance_km']:.2f} km")
        print(f"Current Price     : Rs.{best['current_price']:.2f}/quintal")
        print(f"Predicted Price   : Rs.{best['predicted_price']:.2f}/quintal ({best['expected_change_pct']:+.2f}%)")
        print(f"Transport Cost    : Rs.{best['transport_cost']:.2f}")
        print(f"Market Fee        : Rs.{best['market_fee']:.2f}")
        print(f"Expected Net      : Rs.{best['net_return']:.2f}")
        print(f"Net Price         : Rs.{best['net_price_per_quintal']:.2f}/quintal")
        print(f"Risk Level        : {best['risk_level']}")
        print(f"Confidence Score  : {best['confidence_score']:.1f} / 100")
        print(f"Recommendation    : {best['recommendation_label']}")
        print(f"Reason            : {best['reason']}")
        if best.get('warning'):
            print(f"Warning           : {best['warning']}")
        print("\n" + "=" * 70)
