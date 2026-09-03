"""
Model Registry Module.
Tracks trained models, features, validation metrics, and training metadata per commodity and market.
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.config import (
    MARKET_METADATA_FILE,
    MODEL_DIR,
    PROCESSED_DATA_DIR,
    get_model_dir,
)


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


def validate_registered_artifacts() -> Dict[str, Any]:
    """
    Audit and validate all registered models, feature lists, and supporting datasets
    against the filesystem. Returns comprehensive audit status.
    """
    results: Dict[str, Any] = {
        "registry_file": str(MODEL_REGISTRY_FILE.resolve()),
        "registry_file_exists": MODEL_REGISTRY_FILE.exists(),
        "market_metadata_file": str(MARKET_METADATA_FILE.resolve()),
        "market_metadata_file_exists": MARKET_METADATA_FILE.exists(),
        "models": [],
        "missing_artifacts": [],
    }

    registry = load_model_registry()
    for comm, markets in registry.items():
        target_dir = get_model_dir(commodity=comm)
        for mkt, meta in markets.items():
            model_fname = meta.get("model_file", f"{mkt}_final_model.json")
            feat_fname = meta.get("feature_file", f"{mkt}_final_features.csv")

            model_path = target_dir / model_fname
            feat_path = target_dir / feat_fname

            # Fallback for Onion at default MODEL_DIR
            if not model_path.exists() and MODEL_DIR.exists():
                fallback_m = MODEL_DIR / model_fname
                if fallback_m.exists():
                    model_path = fallback_m
            if not feat_path.exists() and MODEL_DIR.exists():
                fallback_f = MODEL_DIR / feat_fname
                if fallback_f.exists():
                    feat_path = fallback_f

            hist_path = PROCESSED_DATA_DIR / f"{comm.lower()}_{mkt.lower()}_model.csv"

            model_exists = model_path.exists()
            feat_exists = feat_path.exists()
            hist_exists = hist_path.exists()

            entry_status = {
                "commodity": comm,
                "market": mkt,
                "model_file": str(model_path.resolve()),
                "model_exists": model_exists,
                "feature_file": str(feat_path.resolve()),
                "feature_exists": feat_exists,
                "history_file": str(hist_path.resolve()),
                "history_exists": hist_exists,
                "usage_status": meta.get("usage_status", "UNKNOWN"),
            }
            results["models"].append(entry_status)

            if not model_exists:
                results["missing_artifacts"].append(f"Model file missing: {model_path.resolve()}")
            if not feat_exists:
                results["missing_artifacts"].append(f"Feature CSV missing: {feat_path.resolve()}")
            if not hist_exists:
                results["missing_artifacts"].append(f"Historical baseline data missing: {hist_path.resolve()}")

    return results


def validate_startup_artifacts(strict: bool = False) -> Dict[str, Any]:
    """
    Validate required model and data artifacts at startup/runtime.
    If strict=True, raises FileNotFoundError with descriptive message listing missing artifacts.
    Otherwise, returns structured audit results.
    """
    results = validate_registered_artifacts()
    if strict and results["missing_artifacts"]:
        missing_list = "\n  - ".join(results["missing_artifacts"])
        raise FileNotFoundError(
            f"Required runtime model/data artifacts are missing:\n  - {missing_list}\n"
            f"Please verify deployment and ensure all required artifacts are present."
        )
    return results



