from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.evaluation_runner import (  # noqa: E402
    evaluate_local_nlu_cases,
    evaluate_single_case,
)


class LocalNLUEvaluationRunnerTests(unittest.TestCase):
    def test_report_shape_has_required_metrics(self) -> None:
        report = evaluate_local_nlu_cases(
            [{"case_id": "c1", "input": "asdf qwer", "expected": {"needs_review": True}}]
        )
        for key in [
            "total",
            "passed",
            "failed",
            "accuracy",
            "unsafe_passes",
            "manual_review_count",
            "failures",
        ]:
            self.assertIn(key, report)

    def test_default_expected_dataset_evaluates_without_crash(self) -> None:
        report = evaluate_local_nlu_cases()
        self.assertGreaterEqual(report["total"], 1)

    def test_unsafe_unknown_case_does_not_pass_as_resolved(self) -> None:
        result = evaluate_single_case(
            {
                "case_id": "unknown_case",
                "input": "zzzz qqqq xxxx",
                "expected": {"needs_review": True},
            }
        )
        self.assertFalse(result["unsafe_pass"])

    def test_report_json_serializable(self) -> None:
        report = evaluate_local_nlu_cases()
        self.assertIsInstance(json.dumps(report, sort_keys=True), str)

    def test_accuracy_is_between_zero_and_one(self) -> None:
        report = evaluate_local_nlu_cases()
        self.assertIsInstance(report["accuracy"], float)
        self.assertGreaterEqual(report["accuracy"], 0.0)
        self.assertLessEqual(report["accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
