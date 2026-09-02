"""
Expand mandi GPS metadata without fabricating coordinates.

Existing project coordinates are retained and tagged.
Additional rows come from the official current catalogue (market/state/district).
Coordinates are filled only from a conservative public district-headquarters
lookup. Unmatched markets are stored with blank lat/lon and UNAVAILABLE status.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from src.config.config import MARKET_METADATA_FILE, PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.utils.logger import logger

# Public district / city headquarters coordinates (decimal degrees).
# These are approximate market locations (district HQ), not surveyed mandi gates.
DISTRICT_HQ_APPROX: Dict[Tuple[str, str], Tuple[float, float]] = {
    ("uttar pradesh", "bareilly"): (28.3670, 79.4304),
    ("uttar pradesh", "agra"): (27.1767, 78.0081),
    ("uttar pradesh", "aligarh"): (27.8974, 78.0880),
    ("uttar pradesh", "farrukhabad"): (27.3826, 79.5830),
    ("uttar pradesh", "lucknow"): (26.8467, 80.9462),
    ("uttar pradesh", "kanpur"): (26.4499, 80.3319),
    ("uttar pradesh", "varanasi"): (25.3176, 82.9739),
    ("odisha", "bargarh"): (21.3435, 83.6357),
    ("maharashtra", "nagpur"): (21.1458, 79.0882),
    ("maharashtra", "nashik"): (19.9975, 73.7898),
    ("maharashtra", "pune"): (18.5204, 73.8567),
    ("maharashtra", "mumbai"): (19.0760, 72.8777),
    ("karnataka", "kolar"): (13.1367, 78.1291),
    ("karnataka", "hassan"): (13.0072, 76.0962),
    ("karnataka", "bengaluru"): (12.9716, 77.5946),
    ("karnataka", "bangalore"): (12.9716, 77.5946),
    ("andhra pradesh", "chittoor"): (13.2172, 79.1006),
    ("andhra pradesh", "guntur"): (16.3067, 80.4365),
    ("punjab", "ludhiana"): (30.9010, 75.8573),
    ("punjab", "patiala"): (30.3398, 76.3869),
    ("madhya pradesh", "indore"): (22.7196, 75.8577),
    ("rajasthan", "kota"): (25.2138, 75.8648),
    ("west bengal", "purba bardhaman"): (23.2324, 87.8615),
    ("west bengal", "bardhaman"): (23.2324, 87.8615),
    ("haryana", "karnal"): (29.6857, 76.9905),
    ("delhi", "delhi"): (28.6139, 77.2090),
    ("gujarat", "ahmedabad"): (23.0225, 72.5714),
    ("tamil nadu", "chennai"): (13.0827, 80.2707),
    ("bihar", "patna"): (25.5941, 85.1376),
    ("telangana", "hyderabad"): (17.3850, 78.4867),
    ("kerala", "ernakulam"): (9.9816, 76.2999),
    ("assam", "kamrup"): (26.1445, 91.7362),
    ("chhattisgarh", "raipur"): (21.2514, 81.6296),
    ("jharkhand", "ranchi"): (23.3441, 85.3096),
    ("uttarakhand", "dehradun"): (30.3165, 78.0322),
    ("himachal pradesh", "shimla"): (31.1048, 77.1734),
    ("jammu and kashmir", "jammu"): (32.7266, 74.8570),
}


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def _lookup_approx(state: str, district: str, market: str) -> Optional[Tuple[float, float]]:
    key = (_norm(state), _norm(district))
    if key in DISTRICT_HQ_APPROX:
        return DISTRICT_HQ_APPROX[key]
    key2 = (_norm(state), _norm(market))
    if key2 in DISTRICT_HQ_APPROX:
        return DISTRICT_HQ_APPROX[key2]
    return None


def expand_market_metadata() -> pd.DataFrame:
    existing = pd.DataFrame()
    if MARKET_METADATA_FILE.exists():
        existing = pd.read_csv(MARKET_METADATA_FILE)
        existing.columns = [c.strip().lower() for c in existing.columns]

    catalogue_rows = []
    current_raw = RAW_DATA_DIR / "mandi_current_raw.csv"
    if current_raw.exists():
        cur = pd.read_csv(current_raw)
        cur.columns = [c.strip().lower() for c in cur.columns]
        keep = [c for c in ["market", "state", "district", "commodity"] if c in cur.columns]
        catalogue_rows.append(cur[keep].drop_duplicates())

    for hist in RAW_DATA_DIR.glob("*_history.csv"):
        hist_df = pd.read_csv(hist)
        hist_df.columns = [c.strip().lower() for c in hist_df.columns]
        keep = [c for c in ["market", "state", "district", "commodity"] if c in hist_df.columns]
        if keep:
            catalogue_rows.append(hist_df[keep].drop_duplicates())

    combined = pd.concat(catalogue_rows, ignore_index=True) if catalogue_rows else pd.DataFrame(
        columns=["market", "state", "district", "commodity"]
    )
    for col in ["market", "state", "district", "commodity"]:
        if col not in combined.columns:
            combined[col] = ""
        combined[col] = combined[col].astype(str).str.strip()

    if not existing.empty:
        for col in ["market", "state", "district", "commodity"]:
            if col in existing.columns:
                existing[col] = existing[col].astype(str).str.strip()

    records = []
    seen = set()

    def add_row(market, state, district, commodity, lat, lon, status, source, approximate):
        key = (_norm(market), _norm(state), _norm(commodity))
        if not market or key in seen:
            return
        seen.add(key)
        records.append({
            "market": market,
            "state": state,
            "district": district,
            "latitude": lat,
            "longitude": lon,
            "commodity": commodity,
            "coordinate_status": status,
            "coordinate_source": source,
            "approximate": approximate,
        })

    if not existing.empty:
        for _, row in existing.iterrows():
            lat = pd.to_numeric(row.get("latitude"), errors="coerce")
            lon = pd.to_numeric(row.get("longitude"), errors="coerce")
            if pd.notna(lat) and pd.notna(lon):
                add_row(
                    row.get("market"),
                    row.get("state"),
                    row.get("district"),
                    row.get("commodity"),
                    float(lat),
                    float(lon),
                    "EXISTING_PROJECT",
                    "project_market_metadata",
                    False,
                )
            else:
                add_row(
                    row.get("market"),
                    row.get("state"),
                    row.get("district"),
                    row.get("commodity"),
                    None,
                    None,
                    "UNAVAILABLE",
                    "none",
                    False,
                )

    for _, row in combined.iterrows():
        approx = _lookup_approx(row["state"], row["district"], row["market"])
        if approx:
            add_row(
                row["market"],
                row["state"],
                row["district"],
                row["commodity"],
                approx[0],
                approx[1],
                "APPROXIMATE",
                "public_district_headquarters",
                True,
            )
        else:
            add_row(
                row["market"],
                row["state"],
                row["district"],
                row["commodity"],
                None,
                None,
                "UNAVAILABLE",
                "none",
                False,
            )

    out = pd.DataFrame(records)
    MARKET_METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(MARKET_METADATA_FILE, index=False)
    with_coords = int(out["latitude"].notna().sum())
    missing = int(out["latitude"].isna().sum())
    logger.info(
        f"Expanded market metadata: {len(out)} rows, {with_coords} with coordinates, {missing} unavailable"
    )
    summary = pd.DataFrame([
        {
            "total_rows": len(out),
            "unique_markets": out["market"].nunique(),
            "with_coordinates": with_coords,
            "missing_coordinates": missing,
            "approximate_coordinates": int((out["approximate"] == True).sum()),
        }
    ])
    summary.to_csv(PROCESSED_DATA_DIR / "gps_metadata_summary.csv", index=False)
    return out


if __name__ == "__main__":
    df = expand_market_metadata()
    print(df["coordinate_status"].value_counts().to_string())
