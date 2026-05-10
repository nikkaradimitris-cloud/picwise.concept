from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.training_pack import (  # noqa: E402
    evaluate_stage_19_training_pack,
    get_stage_19_training_pack,
    summarize_stage_19_training_pack,
)

_RESOLVED_STATUSES = {"intent_resolved", "specific_product_resolved", "general_intent_resolved"}


class LocalNLUTrainingPackStage19Tests(unittest.TestCase):
    def test_training_pack_is_non_empty(self) -> None:
        cases = get_stage_19_training_pack(max_variants_per_seed=20)
        self.assertIsInstance(cases, list)
        self.assertGreater(len(cases), 0)

    def test_pack_summary_contains_seed_variant_and_category_counts(self) -> None:
        cases = get_stage_19_training_pack(max_variants_per_seed=15)
        summary = summarize_stage_19_training_pack(cases)
        self.assertIn("total_cases", summary)
        self.assertIn("by_seed", summary)
        self.assertIn("by_variant_type", summary)
        self.assertIn("by_category", summary)
        self.assertGreater(summary["total_cases"], 0)

    def test_evaluation_runs_without_crash_and_has_required_metrics(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=10)
        for key in (
            "total",
            "passed",
            "failed",
            "accuracy",
            "unsafe_passes",
            "manual_review_count",
            "failures",
        ):
            self.assertIn(key, report)

    def test_unsafe_ambiguous_cases_do_not_pass_as_resolved(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=30)
        results = report.get("results", [])
        ambiguous_rows = [
            row
            for row in results
            if row.get("case_id", "").startswith("stage19_ambiguous_unknown")
        ]
        self.assertGreater(len(ambiguous_rows), 0)
        for row in ambiguous_rows:
            if row.get("passed"):
                actual = row.get("actual", {})
                status = str(actual.get("status", ""))
                confidence = float(actual.get("confidence", 0.0))
                self.assertTrue(status not in _RESOLVED_STATUSES or confidence < 0.7)

    def test_report_has_no_product_offer_price_or_affiliate_fields(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=8)
        blob = json.dumps(report, sort_keys=True).lower()
        for forbidden in ("products", "offers", "price", "prices", "affiliate", "affiliate_url"):
            self.assertNotIn(forbidden, blob)

    def test_report_is_json_serializable(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=8)
        self.assertIsInstance(json.dumps(report, sort_keys=True), str)


if __name__ == "__main__":
    unittest.main()
