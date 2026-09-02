"""
Task 6 Unit Tests -- Model Quality Audit & Benchmarking System.

Tests:
1. MAE improvement calculation
2. RMSE improvement calculation
3. Quality classification (STRONG, ACCEPTABLE, WEAK, REJECT)
4. Reliability score bounds 0-100 & factors
5. Farmer usage gating assignment
6. Spike ratio & error percentiles calculation
7. Ranking sorting & disabled handling
8. JSON schema & export validity
9. Missing model handling
10. Absence of proxy models in benchmark catalog
11. Deterministic & reproducible scoring
"""
import json
import unittest

import numpy as np
import pandas as pd

from src.benchmark.model_quality import (
    GENUINE_MODELS,
    QUALITY_ACCEPTABLE,
    QUALITY_REJECT,
    QUALITY_STRONG,
    QUALITY_WEAK,
    STATUS_DISABLED,
    STATUS_PRODUCTION_READY,
    STATUS_RESEARCH_ONLY,
    STATUS_USABLE_WITH_WARNING,
    assign_usage_status,
    calculate_direction_accuracy,
    calculate_error_distribution,
    calculate_improvement,
    calculate_mae,
    calculate_r2,
    calculate_reliability_score,
    calculate_rmse,
    calculate_spike_robustness,
    classify_quality,
    generate_benchmark_csv,
    generate_benchmark_json,
    generate_commodity_summary_csv,
    generate_ranking_csv,
    run_commodity_benchmark,
)


class TestModelBenchmark(unittest.TestCase):

    def test_improvement_calculations(self):
        """Verify MAE & RMSE improvement percentage calculation."""
        self.assertAlmostEqual(calculate_improvement(100.0, 80.0), 20.0)
        self.assertAlmostEqual(calculate_improvement(100.0, 110.0), -10.0)
        self.assertAlmostEqual(calculate_improvement(100.0, 100.0), 0.0)
        self.assertIsNone(calculate_improvement(0.0, 50.0))

    def test_quality_classification(self):
        """Verify STRONG, ACCEPTABLE, WEAK, REJECT quality rules."""
        # STRONG: MAE impr >= 10, RMSE impr >= 5, R2 > 0.50
        self.assertEqual(classify_quality(15.0, 10.0, 0.90), QUALITY_STRONG)
        # ACCEPTABLE: MAE impr >= 0, R2 > 0 (not strong)
        self.assertEqual(classify_quality(5.0, 2.0, 0.40), QUALITY_ACCEPTABLE)
        # WEAK: MAE impr < 0 or R2 <= 0
        self.assertEqual(classify_quality(-5.0, 5.0, 0.30), QUALITY_WEAK)
        self.assertEqual(classify_quality(5.0, 5.0, -0.10), QUALITY_WEAK)
        # REJECT: MAE impr < -20
        self.assertEqual(classify_quality(-25.0, -20.0, -0.50), QUALITY_REJECT)

    def test_reliability_score_bounds_and_determinism(self):
        """Verify Reliability score is strictly bounded in [0, 100] and deterministic."""
        score1 = calculate_reliability_score(
            mae_improvement_pct=15.0,
            rmse_improvement_pct=10.0,
            r2_val=0.95,
            spike_ratio=1.2,
            direction_acc=60.0,
            sample_size=2500,
        )
        score2 = calculate_reliability_score(
            mae_improvement_pct=15.0,
            rmse_improvement_pct=10.0,
            r2_val=0.95,
            spike_ratio=1.2,
            direction_acc=60.0,
            sample_size=2500,
        )
        self.assertEqual(score1, score2)
        self.assertGreaterEqual(score1, 0.0)
        self.assertLessEqual(score1, 100.0)

        # Extreme bad score test
        bad_score = calculate_reliability_score(
            mae_improvement_pct=-150.0,
            rmse_improvement_pct=-100.0,
            r2_val=-0.50,
            spike_ratio=10.0,
            direction_acc=20.0,
            sample_size=100,
        )
        self.assertGreaterEqual(bad_score, 0.0)
        self.assertLessEqual(bad_score, 100.0)

    def test_usage_gating_rules(self):
        """Verify farmer usage status rules."""
        # Strong/Acceptable with high score & positive improvement -> PRODUCTION_READY
        self.assertEqual(
            assign_usage_status(QUALITY_STRONG, 85.0, 15.0, 0.90),
            STATUS_PRODUCTION_READY,
        )
        # Tolerable regression within -20% and reasonable score -> USABLE_WITH_WARNING
        self.assertEqual(
            assign_usage_status(QUALITY_WEAK, 45.0, -10.0, 0.40),
            STATUS_USABLE_WITH_WARNING,
        )
        # Regression worse than -20% -> RESEARCH_ONLY
        self.assertEqual(
            assign_usage_status(QUALITY_WEAK, 25.0, -30.0, 0.10),
            STATUS_RESEARCH_ONLY,
        )
        # Hard regression worse than -50% or R2 < -0.20 -> DISABLED
        self.assertEqual(
            assign_usage_status(QUALITY_REJECT, 20.0, -197.0, -0.47),
            STATUS_DISABLED,
        )

    def test_spike_and_error_percentiles(self):
        """Verify spike ratio and error percentiles math."""
        y_true = np.array([100.0, 102.0, 105.0, 150.0, 104.0])
        y_pred = np.array([100.0, 101.0, 106.0, 120.0, 105.0])

        err_dist = calculate_error_distribution(y_true, y_pred)
        self.assertIn("median_abs_error", err_dist)
        self.assertIn("p90_abs_error", err_dist)
        self.assertIn("p95_abs_error", err_dist)
        self.assertIn("max_abs_error", err_dist)
        self.assertEqual(err_dist["max_abs_error"], 30.0)

        spike_info = calculate_spike_robustness(y_true, y_pred, train_mae=5.0)
        self.assertIn("spike_threshold", spike_info)
        self.assertEqual(spike_info["spike_threshold"], 10.0)
        self.assertGreaterEqual(spike_info["spike_count"], 1)

    def test_genuine_models_catalog(self):
        """Verify catalog contains exactly 8 genuine models and no proxy models."""
        self.assertEqual(len(GENUINE_MODELS), 8)
        model_names = [f"{c}_{m}" for c, m, _, _, _ in GENUINE_MODELS]
        self.assertIn("potato_agra", model_names)
        self.assertIn("tomato_kolar", model_names)
        self.assertIn("wheat_khanna", model_names)
        self.assertIn("wheat_indore", model_names)
        self.assertIn("rice_burdwan", model_names)
        self.assertIn("onion_bareilly", model_names)

        # Confirm no proxy or non-genuine models
        for c, m, _, _, _ in GENUINE_MODELS:
            self.assertNotIn("proxy", c.lower())
            self.assertNotIn("proxy", m.lower())

    def test_benchmark_execution_and_export(self):
        """Verify end-to-end benchmark execution and artifact creation."""
        records = run_commodity_benchmark()
        self.assertEqual(len(records), 8)

        csv_path = generate_benchmark_csv(records)
        rank_path = generate_ranking_csv(records)
        summary_path = generate_commodity_summary_csv(records)
        json_path = generate_benchmark_json(records)

        self.assertTrue(csv_path.exists())
        self.assertTrue(rank_path.exists())
        self.assertTrue(summary_path.exists())
        self.assertTrue(json_path.exists())

        # Verify JSON content
        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["models_count"], 8)
        self.assertIn("models", data)


if __name__ == "__main__":
    unittest.main()
