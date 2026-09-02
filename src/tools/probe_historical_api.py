"""
Probe official data.gov.in AGMARKNET endpoints to determine which
historical acquisition strategies work from this network.

Does not download bulk history. Does not print API keys.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.config.config import (
    API_BASE_URL,
    API_RESOURCE_ID_CURRENT,
    API_RESOURCE_ID_HISTORICAL,
    DATA_GOV_API_KEY,
    PROCESSED_DATA_DIR,
)

HEADERS = {"User-Agent": "SIH26132-historical-probe/1.0"}


def _call(resource_id: str, params: dict, timeout: tuple, label: str) -> dict:
    url = f"{API_BASE_URL}{resource_id}"
    safe = {k: v for k, v in params.items() if k != "api-key"}
    started = time.time()
    result = {
        "label": label,
        "resource_id": resource_id,
        "params": safe,
        "timeout": list(timeout),
        "ok": False,
        "status_code": None,
        "elapsed_sec": None,
        "error": None,
        "total": None,
        "n_records": 0,
        "sample_keys": None,
        "sample_commodity": None,
        "sample_date": None,
        "sample_market": None,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        elapsed = round(time.time() - started, 2)
        result["elapsed_sec"] = elapsed
        result["status_code"] = resp.status_code
        if resp.status_code != 200:
            result["error"] = resp.text[:300]
            print(f"FAIL {label}: HTTP {resp.status_code} in {elapsed}s")
            return result
        payload = resp.json()
        records = payload.get("records", []) or []
        result["ok"] = True
        result["total"] = payload.get("total")
        result["n_records"] = len(records)
        if records:
            rec = records[0]
            result["sample_keys"] = sorted(list(rec.keys()))
            result["sample_commodity"] = rec.get("Commodity") or rec.get("commodity")
            result["sample_date"] = rec.get("Arrival_Date") or rec.get("arrival_date")
            result["sample_market"] = rec.get("Market") or rec.get("market")
        print(
            f"OK   {label}: HTTP {resp.status_code} in {elapsed}s "
            f"records={len(records)} total={payload.get('total')}"
        )
    except Exception as exc:
        elapsed = round(time.time() - started, 2)
        result["elapsed_sec"] = elapsed
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(f"FAIL {label}: {result['error']} after {elapsed}s")
    return result


def run_probe() -> list:
    if not DATA_GOV_API_KEY:
        raise RuntimeError("DATA_GOV_API_KEY missing")

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    yesterday_iso = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    results = []

    probes = [
        (
            API_RESOURCE_ID_CURRENT,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "limit": 5,
                "offset": 0,
            },
            (10, 30),
            "current_unfiltered_limit5",
        ),
        (
            API_RESOURCE_ID_CURRENT,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "limit": 10,
                "offset": 0,
                "filters[commodity]": "Potato",
            },
            (10, 30),
            "current_potato_lowercase_filter",
        ),
        (
            API_RESOURCE_ID_HISTORICAL,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "limit": 1,
                "offset": 0,
            },
            (15, 90),
            "hist_unfiltered_limit1_t90",
        ),
        (
            API_RESOURCE_ID_HISTORICAL,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "limit": 5,
                "offset": 0,
                "filters[Commodity]": "Onion",
                "filters[Market]": "Bareilly",
                "filters[State]": "Uttar Pradesh",
            },
            (15, 90),
            "hist_onion_bareilly_pascal_t90",
        ),
        (
            API_RESOURCE_ID_HISTORICAL,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "limit": 5,
                "offset": 0,
                "filters[commodity]": "Onion",
                "filters[market]": "Bareilly",
            },
            (10, 20),
            "hist_onion_bareilly_lowercase_t20",
        ),
        (
            API_RESOURCE_ID_HISTORICAL,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "limit": 5,
                "offset": 0,
                "filters[Commodity]": "Potato",
                "filters[Market]": "Agra",
            },
            (15, 90),
            "hist_potato_agra_pascal_t90",
        ),
        (
            API_RESOURCE_ID_HISTORICAL,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "limit": 10,
                "offset": 0,
                "filters[Arrival_Date]": yesterday,
                "filters[Commodity]": "Potato",
            },
            (15, 90),
            "hist_potato_arrival_dmy",
        ),
        (
            API_RESOURCE_ID_HISTORICAL,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "json",
                "limit": 10,
                "offset": 0,
                "filters[Arrival_Date]": yesterday_iso,
                "filters[Commodity]": "Potato",
            },
            (15, 90),
            "hist_potato_arrival_iso",
        ),
        (
            API_RESOURCE_ID_HISTORICAL,
            {
                "api-key": DATA_GOV_API_KEY,
                "format": "csv",
                "limit": 5,
                "offset": 0,
                "filters[Commodity]": "Potato",
                "filters[Market]": "Agra",
            },
            (15, 90),
            "hist_potato_agra_csv",
        ),
    ]

    for resource_id, params, timeout, label in probes:
        results.append(_call(resource_id, params, timeout, label))

    out_dir = PROCESSED_DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "historical_api_probe.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "probed_at": datetime.now().isoformat(timespec="seconds"),
                "source": "https://api.data.gov.in/resource/",
                "results": results,
            },
            f,
            indent=2,
        )
    print(f"Wrote {out_path}")
    return results


if __name__ == "__main__":
    load_dotenv()
    run_probe()
