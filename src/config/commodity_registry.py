"""
Commodity Registry Module.
Central configuration registry for agricultural commodities supported by SIH26132.
Catalogue rows are derived from official AGMARKNET names when available.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class CommodityConfig:
    """
    Configuration specification for an agricultural commodity.
    """
    name: str                           # Display name, e.g., "Onion"
    api_commodity_name: str             # AGMARKNET API filter name, e.g., "Onion"
    status: str                         # VALIDATED / DEVELOPMENT / DISCOVERY / INSUFFICIENT_DATA / ...
    model_type: str = "change_xgboost_v3"
    feature_version: str = "v3"
    min_history_sessions: int = 45
    default_markets: List[str] = field(default_factory=list)
    historical_mae: Dict[str, float] = field(default_factory=dict)
    model_dir_name: Optional[str] = None
    notes: str = ""
    training_eligible: bool = False
    model_status: str = "UNTRAINED"
    model_count: int = 0

    @property
    def key(self) -> str:
        return self.name.strip().lower()


# ============================================================
# PRE-CONFIGURED COMMODITIES REGISTRY
# ============================================================

_COMMODITIES: Dict[str, CommodityConfig] = {
    "onion": CommodityConfig(
        name="Onion",
        api_commodity_name="Onion",
        status="VALIDATED",
        model_type="change_xgboost_v3",
        feature_version="v3",
        min_history_sessions=45,
        default_markets=["Bareilly", "Bargarh", "Nagpur"],
        historical_mae={
            "bareilly": 29.25,
            "bargarh": 270.51,
            "nagpur": 159.96,
        },
        model_dir_name=None,  # Root change_xgboost_v3/final for backward compatibility
        notes="Production-validated ML pipeline with 3 calibrated XGBoost V3 models.",
        training_eligible=True,
        model_status="VALIDATED",
        model_count=3,
    ),
    "potato": CommodityConfig(
        name="Potato",
        api_commodity_name="Potato",
        status="DEVELOPMENT",
        model_type="change_xgboost_v3",
        feature_version="v3",
        min_history_sessions=45,
        default_markets=["Agra", "Farrukhabad", "Aligarh", "Hassan"],
        historical_mae={
            "agra": 55.0,
            "farrukhabad": 60.0,
            "aligarh": 50.0,
            "hassan": 65.0
        },
        model_dir_name="potato",
        notes="Awaiting genuine Potato historical training; proxy/relabeled Onion data is not valid.",
        training_eligible=False,
        model_status="UNTRAINED",
        model_count=0,
    ),
    "tomato": CommodityConfig(
        name="Tomato",
        api_commodity_name="Tomato",
        status="DEVELOPMENT",
        model_type="change_xgboost_v3",
        feature_version="v3",
        min_history_sessions=45,
        default_markets=["Kolar", "Nashik", "Madanapalle"],
        historical_mae={
            "kolar": 120.0,
            "nashik": 110.0,
            "madanapalle": 130.0
        },
        model_dir_name="tomato",
        notes="Awaiting genuine Tomato historical training; proxy/relabeled Onion data is not valid.",
        training_eligible=False,
        model_status="UNTRAINED",
        model_count=0,
    ),
    "wheat": CommodityConfig(
        name="Wheat",
        api_commodity_name="Wheat",
        status="DEVELOPMENT",
        model_type="change_xgboost_v3",
        feature_version="v3",
        min_history_sessions=45,
        default_markets=["Khanna", "Indore", "Kota"],
        historical_mae={
            "khanna": 35.0,
            "indore": 40.0,
            "kota": 38.0
        },
        model_dir_name="wheat",
        notes="Awaiting genuine Wheat historical training; proxy/relabeled Onion data is not valid.",
        training_eligible=False,
        model_status="UNTRAINED",
        model_count=0,
    ),
    "rice": CommodityConfig(
        name="Rice",
        api_commodity_name="Rice",
        status="DEVELOPMENT",
        model_type="change_xgboost_v3",
        feature_version="v3",
        min_history_sessions=45,
        default_markets=["Burdwan", "Karnal", "Guntur"],
        historical_mae={
            "burdwan": 45.0,
            "karnal": 50.0,
            "guntur": 48.0
        },
        model_dir_name="rice",
        notes="Awaiting genuine Rice historical training; proxy/relabeled Onion data is not valid.",
        training_eligible=False,
        model_status="UNTRAINED",
        model_count=0,
    ),
}


def get_commodity_config(commodity: str) -> CommodityConfig:
    """
    Retrieve configuration for a commodity.
    If not registered, returns a dynamic default configuration with status 'DISCOVERY'.
    """
    key = commodity.strip().lower()
    if key in _COMMODITIES:
        return _COMMODITIES[key]

    # Return dynamic generic config for discovery/unregistered commodity
    return CommodityConfig(
        name=commodity.strip().capitalize(),
        api_commodity_name=commodity.strip().capitalize(),
        status="DISCOVERY",
        model_type="change_xgboost_v3",
        feature_version="v3",
        min_history_sessions=45,
        default_markets=[],
        historical_mae={},
        model_dir_name=key,
        notes=f"Dynamically discovered commodity: {commodity}"
    )


def register_commodity_config(config: CommodityConfig) -> None:
    """
    Register or update a commodity configuration in runtime.
    """
    _COMMODITIES[config.key] = config


def list_registered_commodities() -> List[str]:
    """
    List names of all registered commodities.
    """
    return [cfg.name for cfg in _COMMODITIES.values()]


def load_catalogue_into_registry(catalogue_path: Optional[Path] = None) -> int:
    """
    Merge official AGMARKNET commodity names from a catalogue CSV.
    Does not invent names. Does not overwrite a VALIDATED seed commodity.
    """
    from src.config.config import PROCESSED_DATA_DIR

    path = catalogue_path or (PROCESSED_DATA_DIR / "commodity_catalogue.csv")
    if not path.exists():
        return 0

    df = pd.read_csv(path)
    if df.empty or "api_commodity_name" not in df.columns:
        return 0

    added = 0
    for _, row in df.iterrows():
        api_name = str(row.get("api_commodity_name") or "").strip()
        if not api_name or api_name.lower() in {"nan", "none"}:
            continue
        key = api_name.lower()
        display = str(row.get("display_name") or api_name).strip()
        status = str(row.get("status") or "DISCOVERY").strip()
        model_status = str(row.get("model_status") or "UNTRAINED").strip()
        eligible_raw = row.get("training_eligibility", row.get("training_eligible", False))
        eligible = str(eligible_raw).strip().lower() in {"true", "1", "yes"}
        markets_raw = str(row.get("candidate_markets") or "").strip()
        markets = [m.strip() for m in markets_raw.split("|") if m.strip()] if markets_raw else []
        model_count = int(row.get("model_count") or 0)

        if key in _COMMODITIES and _COMMODITIES[key].status == "VALIDATED":
            cfg = _COMMODITIES[key]
            if markets and not cfg.default_markets:
                cfg.default_markets = markets
            continue

        if key in _COMMODITIES:
            cfg = _COMMODITIES[key]
            cfg.status = status or cfg.status
            cfg.model_status = model_status or cfg.model_status
            cfg.training_eligible = eligible
            cfg.model_count = model_count or cfg.model_count
            if markets:
                cfg.default_markets = markets
            continue

        register_commodity_config(
            CommodityConfig(
                name=display,
                api_commodity_name=api_name,
                status=status,
                model_dir_name=key,
                notes="Derived from official AGMARKNET commodity names.",
                default_markets=markets,
                training_eligible=eligible,
                model_status=model_status,
                model_count=model_count,
            )
        )
        added += 1
    return added
