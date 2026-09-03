"""
Targeted historical AGMARKNET acquisition from the official data.gov.in API.

Why previous downloads failed
-----------------------------
The historical resource (35985678-0d79-46b4-9ed6-6f13308a1d24) contains
80M+ rows. Unfiltered queries and short timeouts (3s/5s) stall. The
current-daily resource is a one-day snapshot and cannot train models.

What works
----------
Official JSON API with PascalCase filters:
  filters[Commodity], filters[Market], filters[State],
  filters[District], filters[Variety], filters[Grade],
  filters[Arrival_Date]
plus pagination (limit/offset), long read timeouts, retries, and resume.

Do not download the full 81M-row dump when commodity+market filters suffice.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

from src.config.config import (
    API_BASE_URL,
    API_RESOURCE_ID_HISTORICAL,
    CACHE_DIR,
    DATA_GOV_API_KEY,
    HIST_API_CONNECT_TIMEOUT,
    HIST_API_MAX_RETRIES,
    HIST_API_PAGE_LIMIT,
    HIST_API_READ_TIMEOUT,
    HIST_API_RETRY_STATUSES,
    HIST_REQUEST_SLEEP_SEC,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
)
from src.utils.logger import logger

HEADERS = {"User-Agent": "SIH26132-historical-fetcher/1.0"}

PASCAL_FILTER_MAP = {
    "commodity": "Commodity",
    "market": "Market",
    "state": "State",
    "district": "District",
    "variety": "Variety",
    "grade": "Grade",
    "arrival_date": "Arrival_Date",
}


def history_output_path(commodity: str, market: str) -> Path:
    c_clean = commodity.strip().lower().replace(" ", "_")
    m_clean = market.strip().lower().replace(" ", "_")
    return RAW_DATA_DIR / f"{c_clean}_{m_clean}_history.csv"


def manifest_path() -> Path:
    return PROCESSED_DATA_DIR / "historical_download_manifest.json"


def load_manifest() -> Dict[str, Any]:
    path = manifest_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"downloads": []}
    return {"downloads": []}


def save_manifest(manifest: Dict[str, Any]) -> None:
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def upsert_manifest_row(row: Dict[str, Any]) -> None:
    manifest = load_manifest()
    downloads = manifest.setdefault("downloads", [])
    key = (str(row.get("commodity", "")).lower(), str(row.get("market", "")).lower())
    kept = [
        item
        for item in downloads
        if (str(item.get("commodity", "")).lower(), str(item.get("market", "")).lower()) != key
    ]
    kept.append(row)
    manifest["downloads"] = kept
    manifest["source"] = "data.gov.in AGMARKNET"
    manifest["resource_id"] = API_RESOURCE_ID_HISTORICAL
    manifest["request_method"] = "GET JSON paginated with PascalCase filters"
    manifest["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_manifest(manifest)


class HistoricalDataFetcher:
    """
    Resumable, targeted historical downloader for official AGMARKNET prices.
    """

    def __init__(
        self,
        resource_id: str = API_RESOURCE_ID_HISTORICAL,
        api_key: Optional[str] = DATA_GOV_API_KEY,
        page_limit: int = HIST_API_PAGE_LIMIT,
        max_retries: int = HIST_API_MAX_RETRIES,
        connect_timeout: int = HIST_API_CONNECT_TIMEOUT,
        read_timeout: int = HIST_API_READ_TIMEOUT,
    ):
        self.resource_id = resource_id
        self.api_key = api_key
        self.page_limit = page_limit
        self.max_retries = max_retries
        self.timeout = (connect_timeout, read_timeout)
        self.api_url = f"{API_BASE_URL}{self.resource_id}"
        self.checkpoint_dir = CACHE_DIR / "historical_checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _require_key(self) -> str:
        if not self.api_key:
            raise ValueError(
                "DATA_GOV_API_KEY not found. Historical acquisition cannot proceed."
            )
        return self.api_key

    def build_params(
        self,
        *,
        commodity: Optional[str] = None,
        market: Optional[str] = None,
        state: Optional[str] = None,
        district: Optional[str] = None,
        variety: Optional[str] = None,
        grade: Optional[str] = None,
        arrival_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "api-key": self._require_key(),
            "format": "json",
            "limit": limit or self.page_limit,
            "offset": offset,
        }
        filters = {
            "Commodity": commodity,
            "Market": market,
            "State": state,
            "District": district,
            "Variety": variety,
            "Grade": grade,
            "Arrival_Date": arrival_date,
        }
        for field, value in filters.items():
            if value:
                params[f"filters[{field}]"] = value
        return params

    def fetch_page(self, params: Dict[str, Any]) -> Tuple[List[Dict], Optional[int], Optional[str]]:
        """
        Fetch one page. Returns (records, total, error).
        """
        safe = {k: v for k, v in params.items() if k != "api-key"}
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Historical API request attempt {attempt}/{self.max_retries} params={safe}"
                )
                response = requests.get(
                    self.api_url,
                    params=params,
                    headers=HEADERS,
                    timeout=self.timeout,
                )
                if response.status_code in HIST_API_RETRY_STATUSES:
                    last_error = f"HTTP {response.status_code}"
                    wait = min(60, 2 ** attempt)
                    logger.warning(f"{last_error}; retrying in {wait}s")
                    time.sleep(wait)
                    continue
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.error(last_error)
                    return [], None, last_error
                payload = response.json()
                records = payload.get("records") or []
                total = payload.get("total")
                logger.info(
                    f"Historical page ok: offset={params.get('offset')} "
                    f"records={len(records)} total={total}"
                )
                return records, total, None
            except (requests.exceptions.Timeout, requests.exceptions.RequestException) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                wait = min(60, 2 ** attempt)
                logger.warning(f"Historical request failed ({last_error}); retrying in {wait}s")
                time.sleep(wait)
        return [], None, last_error or "exhausted retries"

    def probe_total(
        self,
        commodity: str,
        market: Optional[str] = None,
        state: Optional[str] = None,
        district: Optional[str] = None,
        variety: Optional[str] = None,
        grade: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = self.build_params(
            commodity=commodity,
            market=market,
            state=state,
            district=district,
            variety=variety,
            grade=grade,
            limit=1,
            offset=0,
        )
        records, total, error = self.fetch_page(params)
        sample_commodity = records[0].get("Commodity") if records else None
        return {
            "commodity": commodity,
            "market": market,
            "state": state,
            "district": district,
            "total": int(total) if total is not None else 0,
            "ok": error is None,
            "error": error,
            "sample_commodity": sample_commodity,
            "genuine": bool(
                sample_commodity
                and str(sample_commodity).strip().lower() == commodity.strip().lower()
            ),
        }

    def _checkpoint_file(self, commodity: str, market: str) -> Path:
        name = f"{commodity.strip().lower()}_{market.strip().lower()}.json".replace(" ", "_")
        return self.checkpoint_dir / name

    def _load_checkpoint(self, commodity: str, market: str) -> Dict[str, Any]:
        path = self._checkpoint_file(commodity, market)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_checkpoint(self, commodity: str, market: str, payload: Dict[str, Any]) -> None:
        path = self._checkpoint_file(commodity, market)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def download_market_history(
        self,
        commodity: str,
        market: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
        variety: Optional[str] = None,
        grade: Optional[str] = None,
        max_records: Optional[int] = None,
        resume: bool = True,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Download one commodity+market series. Returns a status dictionary.
        """
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        out_path = history_output_path(commodity, market)
        started = datetime.now().isoformat(timespec="seconds")

        probe = self.probe_total(
            commodity=commodity,
            market=market,
            state=state,
            district=district,
            variety=variety,
            grade=grade,
        )
        if not probe["ok"]:
            row = {
                "commodity": commodity,
                "market": market,
                "state": state,
                "district": district,
                "status": "BLOCKED_BY_DATA_ACCESS",
                "reason": probe["error"],
                "record_count": 0,
                "source": "data.gov.in",
                "resource_id": self.resource_id,
                "request_method": "GET JSON",
                "output_file": str(out_path),
                "started_at": started,
            }
            upsert_manifest_row(row)
            return row
        if probe["total"] == 0:
            row = {
                "commodity": commodity,
                "market": market,
                "state": state,
                "district": district,
                "status": "INSUFFICIENT_DATA",
                "reason": "API returned total=0 for these filters",
                "record_count": 0,
                "source": "data.gov.in",
                "resource_id": self.resource_id,
                "request_method": "GET JSON PascalCase filters",
                "filters": {
                    "Commodity": commodity,
                    "Market": market,
                    "State": state,
                    "District": district,
                    "Variety": variety,
                    "Grade": grade,
                },
                "output_file": str(out_path),
                "started_at": started,
            }
            upsert_manifest_row(row)
            return row

        expected = probe["total"]
        if max_records is not None:
            expected = min(expected, max_records)

        if out_path.exists() and not force:
            existing = pd.read_csv(out_path)
            if len(existing) >= expected * 0.98:
                summary = _summarize_frame(existing, commodity, market)
                row = {
                    **summary,
                    "status": "CACHED",
                    "reason": "Existing targeted download already complete",
                    "source": "data.gov.in",
                    "resource_id": self.resource_id,
                    "request_method": "GET JSON PascalCase filters",
                    "filters": {
                        "Commodity": commodity,
                        "Market": market,
                        "State": state,
                    },
                    "api_total": probe["total"],
                    "output_file": str(out_path),
                    "started_at": started,
                }
                upsert_manifest_row(row)
                return row

        offset = 0
        collected: List[Dict] = []
        if resume:
            ckpt = self._load_checkpoint(commodity, market)
            if ckpt.get("records_file") and Path(ckpt["records_file"]).exists():
                prior = pd.read_csv(ckpt["records_file"])
                collected = prior.to_dict(orient="records")
                offset = int(ckpt.get("offset", len(collected)))
                logger.info(f"Resuming {commodity}/{market} at offset={offset} ({len(collected)} rows)")

        last_error = None
        while offset < expected:
            params = self.build_params(
                commodity=commodity,
                market=market,
                state=state,
                district=district,
                variety=variety,
                grade=grade,
                limit=self.page_limit,
                offset=offset,
            )
            records, total, error = self.fetch_page(params)
            if error:
                last_error = error
                break
            if not records:
                break
            collected.extend(records)
            offset += len(records)
            self._save_checkpoint(
                commodity,
                market,
                {
                    "offset": offset,
                    "n_collected": len(collected),
                    "records_file": str(out_path.with_suffix(".partial.csv")),
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                },
            )
            pd.DataFrame(collected).to_csv(out_path.with_suffix(".partial.csv"), index=False)
            if len(records) < self.page_limit:
                break
            time.sleep(HIST_REQUEST_SLEEP_SEC)

        if not collected:
            row = {
                "commodity": commodity,
                "market": market,
                "state": state,
                "district": district,
                "status": "BLOCKED_BY_DATA_ACCESS",
                "reason": last_error or "No records returned after pagination",
                "record_count": 0,
                "api_total": probe["total"],
                "source": "data.gov.in",
                "resource_id": self.resource_id,
                "output_file": str(out_path),
            }
            upsert_manifest_row(row)
            return row

        df = pd.DataFrame(collected)
        df.to_csv(out_path, index=False)
        partial = out_path.with_suffix(".partial.csv")
        if partial.exists():
            partial.unlink()
        ckpt_file = self._checkpoint_file(commodity, market)
        if ckpt_file.exists():
            ckpt_file.unlink()

        summary = _summarize_frame(df, commodity, market)
        incomplete = len(df) < probe["total"] * 0.98
        status = "PARTIAL" if incomplete or last_error else "DOWNLOADED"
        reason = last_error if last_error else "Targeted official historical download complete"
        if probe["sample_commodity"] and str(probe["sample_commodity"]).lower() != commodity.lower():
            status = "POOR_DATA_QUALITY"
            reason = (
                f"API sample commodity '{probe['sample_commodity']}' does not match requested '{commodity}'"
            )
        row = {
            **summary,
            "status": status,
            "reason": reason,
            "source": "data.gov.in AGMARKNET",
            "resource_id": self.resource_id,
            "request_method": "GET JSON paginated PascalCase filters",
            "filters": {
                "Commodity": commodity,
                "Market": market,
                "State": state,
                "District": district,
                "Variety": variety,
                "Grade": grade,
            },
            "api_total": probe["total"],
            "output_file": str(out_path),
            "started_at": started,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }
        upsert_manifest_row(row)
        logger.info(
            f"Saved {len(df)} genuine {commodity} records for {market} -> {out_path}"
        )
        return row


def _summarize_frame(df: pd.DataFrame, commodity: str, market: str) -> Dict[str, Any]:
    work = df.copy()
    work.columns = [c.strip() for c in work.columns]
    date_col = next((c for c in work.columns if c.lower() in {"arrival_date", "date"}), None)
    start_date = end_date = None
    unique_dates = 0
    if date_col:
        parsed = pd.to_datetime(work[date_col], dayfirst=True, errors="coerce")
        unique_dates = int(parsed.nunique())
        if parsed.notna().any():
            start_date = str(parsed.min().date())
            end_date = str(parsed.max().date())
    comm_col = next((c for c in work.columns if c.lower() == "commodity"), None)
    unique_commodities = []
    if comm_col:
        unique_commodities = sorted(work[comm_col].dropna().astype(str).str.strip().unique().tolist())
    return {
        "commodity": commodity,
        "market": market,
        "record_count": int(len(work)),
        "unique_dates": unique_dates,
        "start_date": start_date,
        "end_date": end_date,
        "unique_commodities_in_file": unique_commodities,
    }


def normalize_historical_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize official AGMARKNET columns to lowercase pipeline names."""
    if df.empty:
        return df
    work = df.copy()
    work.columns = [str(c).strip().lower().replace(" ", "_") for c in work.columns]
    rename = {
        "arrival_date": "date",
        "min_price": "min_price",
        "max_price": "max_price",
        "modal_price": "modal_price",
    }
    work = work.rename(columns={k: v for k, v in rename.items() if k in work.columns})
    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"], dayfirst=True, errors="coerce")
    for col in ["min_price", "max_price", "modal_price"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    for col in ["state", "district", "market", "commodity", "variety", "grade"]:
        if col in work.columns:
            work[col] = work[col].astype(str).str.strip()
    return work
