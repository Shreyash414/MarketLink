"""
Model Registry Module.
Tracks trained models, features, validation metrics, and training metadata per commodity and market.
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.config import PROCESSED_DATA_DIR


MODEL_REGISTRY_FILE = PROCESSED_DATA_DIR / "models" / "model_registry.json"


@dataclass
class ModelMetadata:
    commodity: str
    market: str
    model_type: str
    model_file: str
    feature_file: str
    feature_count: int
    test_mae: float
    status: str  # "VALIDATED", "EXPERIMENTAL", "DEPRECATED"
    trained_at: Optional[str] = None
    features: Optional[List[str]] = None


# Default seed registry containing validated Onion models
DEFAULT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "onion": {
        "bareilly": {
            "commodity": "Onion",
            "market": "Bareilly",
            "model_type": "change_xgboost_v3",
            "model_file": "bareilly_final_model.json",
            "feature_file": "bareilly_final_features.csv",
            "feature_count": 5,
            "test_mae": 29.25,
            "status": "VALIDATED",
            "trained_at": "2025-11-04"
        },
        "bargarh": {
            "commodity": "Onion",
            "market": "Bargarh",
            "model_type": "change_xgboost_v3",
            "model_file": "bargarh_final_model.json",
            "feature_file": "bargarh_final_features.csv",
            "feature_count": 20,
            "test_mae": 270.51,
            "status": "VALIDATED",
            "trained_at": "2025-11-04"
        },
        "nagpur": {
            "commodity": "Onion",
            "market": "Nagpur",
            "model_type": "change_xgboost_v3",
            "model_file": "nagpur_final_model.json",
            "feature_file": "nagpur_final_features.csv",
            "feature_count": 50,
            "test_mae": 159.96,
            "status": "VALIDATED",
            "trained_at": "2025-11-04"
        }
    }
}


def load_model_registry() -> Dict[str, Dict[str, Any]]:
    """
    Load the JSON model registry from disk or return defaults if not found.
    """
    if MODEL_REGISTRY_FILE.exists():
        try:
            with open(MODEL_REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_REGISTRY.copy()
    return DEFAULT_REGISTRY.copy()


def save_model_registry(registry_data: Dict[str, Dict[str, Any]]) -> None:
    """
    Save the model registry dictionary to disk.
    """
    MODEL_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)


def get_registered_model(commodity: str, market: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve model metadata for a given commodity and market.
    """
    registry = load_model_registry()
    c_key = commodity.strip().lower()
    m_key = market.strip().lower()
    return registry.get(c_key, {}).get(m_key)


def list_all_models() -> List[Dict[str, Any]]:
    """
    Retrieve a flat list of all registered models across all commodities and markets.
    """
    registry = load_model_registry()
    models = []
    for comm, markets in registry.items():
        for mkt, meta in markets.items():
            models.append(meta)
    return models


def register_model(
    commodity: str,
    market: str,
    model_type: str,
    model_file: str,
    feature_file: str,
    feature_count: int,
    test_mae: float,
    status: str = "VALIDATED",
    trained_at: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    variety: Optional[str] = None,
    grade: Optional[str] = None,
    rmse: Optional[float] = None,
    r2: Optional[float] = None,
    direction_accuracy: Optional[float] = None,
    baseline_mae: Optional[float] = None,
    improvement_pct: Optional[float] = None,
    train_rows: Optional[int] = None,
    val_rows: Optional[int] = None,
    test_rows: Optional[int] = None,
    model_path: Optional[str] = None,
    feature_list: Optional[List[str]] = None
) -> None:
    """
    Register a newly trained model into the central registry with full reproducibility metadata.
    """
    registry = load_model_registry()
    c_key = commodity.strip().lower()
    m_key = market.strip().lower()

    if c_key not in registry:
        registry[c_key] = {}

    entry: Dict[str, Any] = {
        "commodity": commodity.strip(),
        "market": market.strip(),
        "state": state or "N/A",
        "district": district or "N/A",
        "variety": variety or "N/A",
        "grade": grade or "N/A",
        "model_type": model_type,
        "model_version": "v3",
        "model_file": model_file,
        "model_path": model_path or model_file,
        "feature_file": feature_file,
        "feature_list": feature_list or [],
        "feature_count": feature_count,
        "train_rows": train_rows,
        "val_rows": val_rows,
        "test_rows": test_rows,
        "test_mae": test_mae,
        "rmse": rmse,
        "r2": r2,
        "direction_accuracy": direction_accuracy,
        "baseline_mae": baseline_mae,
        "improvement_pct": improvement_pct,
        "status": status,
        "trained_at": trained_at
    }

    registry[c_key][m_key] = entry
    save_model_registry(registry)

