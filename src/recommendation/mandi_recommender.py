"""
Mandi Recommender Module.
Core engine integrating data ingestion, historical merging, dynamic V3 feature engineering,
XGBoost model forecasting, risk assessment, transport economics, and mandi ranking across commodities.
"""
from pathlib import Path
from typing import Any, List, Optional


import pandas as pd

from src.config.commodity_registry import get_commodity_config
from src.config.config import (
    DEFAULT_COMMODITY,
    DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM,
    MARKET_METADATA_FILE,
)
from src.data.data_reliability import evaluate_data_reliability
from src.data.ingestion.current_data_fetcher import CurrentDataFetcher
from src.data.preprocessing.historical_merger import merge_current_with_history
from src.economics.economics_engine import calculate_economics
from src.features.inference_feature_generator import get_latest_inference_features
from src.models.model_quality_gate import can_use_model, evaluate_model_gating
from src.models.model_predictor import ModelPredictor
from src.recommendation.schemas import MandiRecommendationItem, RecommendationResult
from src.risk.risk_engine import RiskEngine
from src.utils.geo_utils import haversine_distance
from src.utils.logger import logger


class MandiRecommender:
    """
    Production recommendation engine for agricultural produce mandis across commodities.
    """

    def __init__(
        self,
        metadata_file: Path = MARKET_METADATA_FILE,
        fetcher: Optional[CurrentDataFetcher] = None,
        predictor: Optional[ModelPredictor] = None,
        risk_engine: Optional[RiskEngine] = None,
    ):
        self.metadata_file = Path(metadata_file)
        self.fetcher = fetcher or CurrentDataFetcher()
        self.predictor = predictor or ModelPredictor()
        self.risk_engine = risk_engine or RiskEngine()
        self._market_metadata: Optional[pd.DataFrame] = None

    def load_market_metadata(self, commodity: Optional[str] = None) -> pd.DataFrame:
        """
        Load market metadata CSV containing coordinates and locations.
        Filters by commodity if specified and present in metadata.
        """
        if not self.metadata_file.exists():
            raise FileNotFoundError(
                f"Market metadata file not found at: {self.metadata_file}"
            )

        df = pd.read_csv(self.metadata_file)
        df.columns = [col.strip().lower() for col in df.columns]

        required_cols = ["market", "state", "district", "latitude", "longitude"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise KeyError(f"Metadata file missing required columns: {missing}")

        for col in ["market", "state", "district"]:
            df[col] = df[col].astype(str).str.strip()

        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

        before = len(df)
        missing_coords = df["latitude"].isna() | df["longitude"].isna()
        if missing_coords.any():
            skipped = int(missing_coords.sum())
            logger.warning(
                f"Skipping {skipped} markets without verified coordinates "
                f"(set unavailable rather than inventing GPS)."
            )
            df = df.loc[~missing_coords].copy()
        logger.info(f"Markets with usable coordinates: {len(df)} / {before}")

        if "commodity" in df.columns and commodity:
            filtered = df[df["commodity"].astype(str).str.strip().str.lower() == commodity.strip().lower()].copy()
            if not filtered.empty:
                return filtered

        return df

    def recommend(
        self,
        farmer_latitude: float,
        farmer_longitude: float,
        quantity_quintals: float,
        commodity: str = DEFAULT_COMMODITY,
        max_distance_km: Optional[float] = None,
        transport_rate: float = DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM,
        farmer_facing: bool = True,
    ) -> RecommendationResult:
        """
        Execute full recommendation pipeline given farmer location and produce quantity.
        """
        # 1. Input Validation
        if quantity_quintals <= 0:
            raise ValueError(f"Quantity quintals must be positive. Got: {quantity_quintals}")

        if not (-90.0 <= farmer_latitude <= 90.0):
            raise ValueError(f"Invalid farmer latitude: {farmer_latitude}")

        if not (-180.0 <= farmer_longitude <= 180.0):
            raise ValueError(f"Invalid farmer longitude: {farmer_longitude}")

        config = get_commodity_config(commodity)
        logger.info(
            f"Starting recommendation for {config.name}: quantity={quantity_quintals} quintals, "
            f"location=({farmer_latitude}, {farmer_longitude})"
        )

        # 2. Market Metadata & Geo Discovery
        metadata = self.load_market_metadata(commodity=commodity)

        # Compute distance to each known mandi
        metadata = metadata.copy()
        metadata["distance_km"] = metadata.apply(
            lambda row: haversine_distance(
                farmer_latitude, farmer_longitude, row["latitude"], row["longitude"]
            ),
            axis=1
        )

        # Distance filter if max_distance_km specified
        if max_distance_km is not None and max_distance_km > 0:
            initial_count = len(metadata)
            metadata = metadata[metadata["distance_km"] <= max_distance_km].copy()
            logger.info(
                f"Distance filter (<= {max_distance_km} km) reduced candidates from {initial_count} to {len(metadata)}"
            )

        if metadata.empty:
            logger.warning(f"No mandis found within radius of {max_distance_km} km for commodity '{commodity}'.")
            return RecommendationResult(
                commodity=commodity,
                farmer_latitude=farmer_latitude,
                farmer_longitude=farmer_longitude,
                quantity_quintals=quantity_quintals,
                recommended_mandi="NONE",
                total_mandis_evaluated=0,
                data_source="NONE",
                recommendations=[]
            )

        # 3. Data Ingestion (Current data fetch with cache fallback)
        target_markets = metadata["market"].tolist()
        current_df, is_live, source_tag = self.fetcher.fetch_all_current_data(
            commodity=config.api_commodity_name,
            target_markets=target_markets
        )

        evaluated_items: List[MandiRecommendationItem] = []

        # 4. Process each candidate mandi
        for _, market_row in metadata.iterrows():
            mandi_name = market_row["market"]
            state = market_row["state"]
            district = market_row["district"]
            distance_km = float(market_row["distance_km"])

            try:
                # Merge recent history with current observation
                merged_df = merge_current_with_history(
                    current_df=current_df,
                    market=mandi_name,
                    commodity=commodity,
                    min_history_sessions=config.min_history_sessions
                )

                # Data Reliability Layer Check
                data_rel = evaluate_data_reliability(
                    commodity=commodity,
                    market=mandi_name,
                    merged_df=merged_df,
                    source=source_tag,
                    farmer_facing=farmer_facing
                )

                if not data_rel.inference_allowed:
                    logger.warning(
                        f"Skipping market '{mandi_name}' due to data reliability check: {data_rel.reason}"
                    )
                    continue

                # Model Quality Gate Check
                gate = evaluate_model_gating(commodity=commodity, market=mandi_name, farmer_facing=farmer_facing)
                if not gate.allowed:
                    logger.warning(
                        f"Skipping market '{mandi_name}' for recommendation: Model usage status '{gate.usage_status}' "
                        f"is not allowed (farmer_facing={farmer_facing}). Reason: {gate.reason}"
                    )
                    continue

                # Load trained model to identify required feature list
                _, required_features = self.predictor.load_market_model(
                    market=mandi_name,
                    commodity=commodity
                )

                # Generate V3 inference features
                X_inference, current_price, latest_date = get_latest_inference_features(
                    merged_df=merged_df,
                    required_features=required_features
                )

                # Run XGBoost inference
                pred_output = self.predictor.predict_next_price(
                    market=mandi_name,
                    X_features=X_inference,
                    current_price=current_price,
                    latest_date=latest_date,
                    commodity=commodity,
                    farmer_facing=farmer_facing,
                    data_reliability=data_rel
                )

                # Evaluate Risk & Confidence
                recent_prices = merged_df["modal_price"]
                risk_output = self.risk_engine.evaluate_risk_and_confidence(
                    market=mandi_name,
                    current_price=current_price,
                    predicted_change=pred_output.expected_change,
                    recent_series=recent_prices,
                    data_date=latest_date,
                    commodity=commodity
                )

                # Calculate Economics
                econ_output = calculate_economics(
                    distance_km=distance_km,
                    quantity_quintals=quantity_quintals,
                    predicted_price=pred_output.predicted_price,
                    transport_rate=transport_rate
                )

                # Assemble warning message
                warnings_list = []
                if gate.warning:
                    warnings_list.append(gate.warning)
                if data_rel.warning:
                    warnings_list.append(data_rel.warning)
                if risk_output.warning_message and risk_output.risk_level != "LOW":
                    warnings_list.append(risk_output.warning_message)
                combined_warning = " ".join(warnings_list)

                item = MandiRecommendationItem(
                    rank=0,  # Will be populated after sorting
                    mandi=mandi_name,
                    state=state,
                    district=district,
                    distance_km=econ_output.distance_km,
                    current_price=pred_output.current_price,
                    predicted_price=pred_output.predicted_price,
                    expected_change=pred_output.expected_change,
                    expected_change_pct=pred_output.expected_change_pct,
                    expected_direction=pred_output.expected_direction,
                    transport_cost=econ_output.transport_cost,
                    market_fee=econ_output.market_fee,
                    gross_revenue=econ_output.gross_revenue,
                    total_cost=econ_output.total_cost,
                    net_return=econ_output.net_return,
                    net_price_per_quintal=econ_output.net_price_per_quintal,
                    risk_level=risk_output.risk_level,
                    confidence_score=risk_output.confidence_score,
                    market_condition=risk_output.market_condition,
                    recommendation_label="ALTERNATIVE",
                    reason="",
                    warning=combined_warning,
                    lower_bound_80=risk_output.lower_bound_80,
                    upper_bound_80=risk_output.upper_bound_80,
                    model_usage_status=gate.usage_status,
                    model_reliability_score=gate.reliability_score,
                    model_quality_class=gate.quality_class,
                    data_source=data_rel.source,
                    data_freshness_status=data_rel.freshness_status,
                    data_age_days=data_rel.age_days,
                    historical_session_count=data_rel.session_count,
                    data_reliability_status=data_rel.status,
                    data_reliability_warning=data_rel.warning
                )

                evaluated_items.append(item)

            except Exception as e:
                logger.error(f"Error evaluating {commodity} market '{mandi_name}': {e}")
                continue



        if not evaluated_items:
            logger.error(f"No eligible {commodity} mandis could be evaluated successfully.")
            return RecommendationResult(
                commodity=commodity,
                farmer_latitude=farmer_latitude,
                farmer_longitude=farmer_longitude,
                quantity_quintals=quantity_quintals,
                recommended_mandi="NONE",
                total_mandis_evaluated=0,
                data_source=source_tag,
                recommendations=[]
            )

        # 5. Rank Mandis based on Expected Net Return (Primary economic metric)
        evaluated_items.sort(key=lambda x: x.net_return, reverse=True)

        for rank_idx, item in enumerate(evaluated_items, start=1):
            item.rank = rank_idx
            if rank_idx == 1:
                item.recommendation_label = "RECOMMENDED"
                item.reason = (
                    f"Recommended as top mandi providing the highest expected net return "
                    f"of Rs.{item.net_return:,.2f} (Rs.{item.net_price_per_quintal:.2f}/quintal) after deducting "
                    f"Rs.{item.transport_cost:.2f} transport cost for {item.distance_km:.1f} km."
                )
            else:
                item.recommendation_label = "ALTERNATIVE"
                item.reason = (
                    f"Alternative market choice providing expected net return of Rs.{item.net_return:,.2f} "
                    f"at a distance of {item.distance_km:.1f} km."
                )

        recommended_mandi_name = evaluated_items[0].mandi

        logger.info(
            f"Recommendation completed for {commodity}. Top Mandi: {recommended_mandi_name} "
            f"(Net Return: Rs.{evaluated_items[0].net_return:,.2f})"
        )

        return RecommendationResult(
            commodity=commodity,
            farmer_latitude=farmer_latitude,
            farmer_longitude=farmer_longitude,
            quantity_quintals=quantity_quintals,
            recommended_mandi=recommended_mandi_name,
            total_mandis_evaluated=len(evaluated_items),
            data_source=source_tag,
            recommendations=evaluated_items
        )


def recommend_mandi(
    farmer_latitude: float,
    farmer_longitude: float,
    quantity_quintals: float,
    commodity: str = DEFAULT_COMMODITY,
    max_distance_km: Optional[float] = None,
    transport_rate: float = DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM,
    farmer_facing: bool = True,
) -> RecommendationResult:
    """
    Convenience function to run mandi recommendation for any commodity.
    """
    recommender = MandiRecommender()
    return recommender.recommend(
        farmer_latitude=farmer_latitude,
        farmer_longitude=farmer_longitude,
        quantity_quintals=quantity_quintals,
        commodity=commodity,
        max_distance_km=max_distance_km,
        transport_rate=transport_rate,
        farmer_facing=farmer_facing,
    )


def recommend_canonical(
    farmer_latitude: float,
    farmer_longitude: float,
    quantity_quintals: float,
    commodity: str = DEFAULT_COMMODITY,
    max_distance_km: Optional[float] = None,
    transport_rate: float = DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM,
    farmer_facing: bool = True,
) -> Any:
    """
    Convenience function executing recommendation and returning canonical AI inference contract.
    """
    res = recommend_mandi(
        farmer_latitude=farmer_latitude,
        farmer_longitude=farmer_longitude,
        quantity_quintals=quantity_quintals,
        commodity=commodity,
        max_distance_km=max_distance_km,
        transport_rate=transport_rate,
        farmer_facing=farmer_facing,
    )
    return res.to_canonical_contract()


