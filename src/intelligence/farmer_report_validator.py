"""
Farmer Report Intelligence & Crowd-Sourced Signal Validation Module.
Validates, scores, and aggregates ground-truth farmer observations
without contaminating the primary AGMARKNET machine learning training data.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config.config import PROCESSED_DATA_DIR
from src.utils.logger import logger

VALIDATED_REPORTS_FILE = PROCESSED_DATA_DIR / "community_reports_validated.csv"


@dataclass
class FarmerReport:
    report_id: str
    farmer_id: str
    commodity: str
    market: str
    reported_price: float
    report_date: str
    quantity_quintals: Optional[float] = None
    variety: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ValidationResult:
    report_id: str
    is_valid: bool
    trust_score: float  # 0.0 to 100.0
    status: str         # "ACCEPTED", "FLAGGED_SUSPICIOUS", "REJECTED"
    rejection_reason: Optional[str] = None
    price_deviation_pct: Optional[float] = None
    benchmark_price: Optional[float] = None


class FarmerReportValidator:
    """
    Quality control and anomaly detection engine for crowd-sourced farmer price reports.
    """

    def __init__(
        self,
        max_allowed_deviation_pct: float = 50.0,
        max_report_age_days: int = 7,
        min_plausible_price: float = 100.0,
        max_plausible_price: float = 20000.0,
    ):
        self.max_allowed_deviation_pct = max_allowed_deviation_pct
        self.max_report_age_days = max_report_age_days
        self.min_plausible_price = min_plausible_price
        self.max_plausible_price = max_plausible_price

    def get_benchmark_price(self, commodity: str, market: str) -> Optional[float]:
        """
        Lookup the freshest known modal price for the commodity/market as a baseline.
        """
        c_clean = commodity.strip().lower()
        m_clean = market.strip().lower()

        # Check processed model files or current cache
        paths = [
            PROCESSED_DATA_DIR / f"{c_clean}_{m_clean}_model.csv",
            PROCESSED_DATA_DIR / "current" / f"{c_clean}_current.csv"
        ]
        for p in paths:
            if p.exists():
                try:
                    df = pd.read_csv(p)
                    if "modal_price" in df.columns:
                        return float(df["modal_price"].dropna().iloc[-1])
                except Exception:
                    pass
        return None

    def validate_report(
        self,
        report: FarmerReport,
        existing_reports: Optional[List[FarmerReport]] = None
    ) -> ValidationResult:
        """
        Run multi-point safety validation on a single farmer report.
        """
        # 1. Price sanity check
        if report.reported_price <= 0:
            return ValidationResult(
                report_id=report.report_id,
                is_valid=False,
                trust_score=0.0,
                status="REJECTED",
                rejection_reason="Price must be strictly positive."
            )

        if not (self.min_plausible_price <= report.reported_price <= self.max_plausible_price):
            return ValidationResult(
                report_id=report.report_id,
                is_valid=False,
                trust_score=0.0,
                status="REJECTED",
                rejection_reason=f"Price Rs.{report.reported_price} outside plausible agricultural range [Rs.{self.min_plausible_price}, Rs.{self.max_plausible_price}]."
            )

        # 2. Date validity check
        try:
            r_date = pd.to_datetime(report.report_date)
            now = pd.Timestamp.now()
            if r_date > now + pd.Timedelta(days=1):
                return ValidationResult(
                    report_id=report.report_id,
                    is_valid=False,
                    trust_score=0.0,
                    status="REJECTED",
                    rejection_reason=f"Future date {report.report_date} is invalid."
                )
            age_days = (now - r_date).days
            if age_days > self.max_report_age_days:
                return ValidationResult(
                    report_id=report.report_id,
                    is_valid=False,
                    trust_score=20.0,
                    status="REJECTED",
                    rejection_reason=f"Report is stale ({age_days} days old, max allowed is {self.max_report_age_days} days)."
                )
        except Exception as e:
            return ValidationResult(
                report_id=report.report_id,
                is_valid=False,
                trust_score=0.0,
                status="REJECTED",
                rejection_reason=f"Malformed date format: {e}"
            )

        # 3. Duplicate check (prevent spamming by the same farmer)
        if existing_reports:
            for ex in existing_reports:
                if (
                    ex.farmer_id == report.farmer_id
                    and ex.commodity.lower() == report.commodity.lower()
                    and ex.market.lower() == report.market.lower()
                    and ex.report_date == report.report_date
                    and ex.report_id != report.report_id
                ):
                    return ValidationResult(
                        report_id=report.report_id,
                        is_valid=False,
                        trust_score=10.0,
                        status="REJECTED",
                        rejection_reason="Duplicate report submitted by same farmer on same date."
                    )

        # 4. Statistical anomaly / deviation check against AGMARKNET benchmark
        benchmark = self.get_benchmark_price(report.commodity, report.market)
        if benchmark is not None and benchmark > 0:
            dev_pct = float(abs(report.reported_price - benchmark) / benchmark * 100.0)
            if dev_pct > self.max_allowed_deviation_pct:
                return ValidationResult(
                    report_id=report.report_id,
                    is_valid=False,
                    trust_score=35.0,
                    status="FLAGGED_SUSPICIOUS",
                    rejection_reason=f"Reported price deviates by {dev_pct:.1f}% from recent benchmark Rs.{benchmark:.2f} (exceeds {self.max_allowed_deviation_pct}% threshold).",
                    price_deviation_pct=round(dev_pct, 1),
                    benchmark_price=round(benchmark, 2)
                )
            
            # Trust score calculation
            trust_score = max(50.0, 100.0 - (dev_pct * 0.8) - (age_days * 3.0))
        else:
            dev_pct = None
            trust_score = 75.0  # Moderate default trust if benchmark unavailable

        return ValidationResult(
            report_id=report.report_id,
            is_valid=True,
            trust_score=round(trust_score, 1),
            status="ACCEPTED",
            price_deviation_pct=round(dev_pct, 1) if dev_pct is not None else None,
            benchmark_price=round(benchmark, 2) if benchmark is not None else None
        )

    def process_and_persist_reports(
        self,
        reports: List[FarmerReport],
        output_file: Path = VALIDATED_REPORTS_FILE
    ) -> pd.DataFrame:
        """
        Validate a batch of reports and save verified ones to isolated community CSV.
        """
        results = []
        for r in reports:
            res = self.validate_report(r, existing_reports=reports)
            row = asdict(r)
            row.update({
                "is_valid": res.is_valid,
                "trust_score": res.trust_score,
                "status": res.status,
                "rejection_reason": res.rejection_reason,
                "price_deviation_pct": res.price_deviation_pct,
                "benchmark_price": res.benchmark_price,
                "validated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            results.append(row)

        df = pd.DataFrame(results)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        logger.info(f"Persisted {len(df)} validated farmer reports to: {output_file}")
        return df


if __name__ == "__main__":
    validator = FarmerReportValidator()
    
    sample_reports = [
        FarmerReport("R001", "F101", "Onion", "Bareilly", 1350.0, "2026-09-01", 10.0, "Red", "Good quality local harvest"),
        FarmerReport("R002", "F102", "Onion", "Bareilly", 4500.0, "2026-09-01", 5.0, "Red", "Extreme anomalous price"),
        FarmerReport("R003", "F103", "Potato", "Agra", -50.0, "2026-09-01", 12.0, "Jyoti", "Negative price error"),
        FarmerReport("R004", "F104", "Wheat", "Khanna", 2260.0, "2026-08-30", 20.0, "Sharbati", "Realistic grain price"),
        FarmerReport("R005", "F104", "Wheat", "Khanna", 2260.0, "2026-08-30", 20.0, "Sharbati", "Duplicate submission"),
        FarmerReport("R006", "F105", "Tomato", "Kolar", 2100.0, "2025-01-01", 15.0, "Hybrid", "Stale report (over a year old)")
    ]

    print("================================================================================")
    print("FARMER REPORT INTELLIGENCE & VALIDATION LAYER (PHASE 14)")
    print("================================================================================")
    
    df_results = validator.process_and_persist_reports(sample_reports)
    print("\nVALIDATION RESULTS:")
    print(df_results[["report_id", "farmer_id", "commodity", "market", "reported_price", "trust_score", "status", "rejection_reason"]].to_string(index=False))
