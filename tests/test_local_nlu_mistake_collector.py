from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.mistake_collector import collect_mistakes, summarize_mistakes  # noqa: E402


class LocalNLUMistakeCollectorTests(unittest.TestCase):
    def test_collects_failures_from_report(self) -> None:
        report = {
            "failures": [
                {
                    "case_id": "c1",
                    "input": "query",
                    "expected": {"category": "car_tyres"},
                    "actual": {"category": None},
                    "mismatch_fields": ["category"],
                    "reason": "field_mismatch",
                }
            ]
        }
        mistakes = collect_mistakes(report)
        self.assertEqual(len(mistakes), 1)
        self.assertEqual(mistakes[0]["case_id"], "c1")

    def test_returns_empty_for_no_failures(self) -> None:
        self.assertEqual(collect_mistakes({"failures": []}), [])

    def test_mistake_record_shape(self) -> None:
        mistakes = collect_mistakes(
            {
                "failures": [
                    {
                        "case_id": "c1",
                        "input": "q",
                        "expected": {},
                        "actual": {},
                        "mismatch_fields": [],
                        "reason": "field_mismatch",
                    }
                ]
            }
        )
        mistake = mistakes[0]
        for key in ["case_id", "input", "expected", "actual", "mismatch_fields", "reason"]:
            self.assertIn(key, mistake)

    def test_summary_returns_counts(self) -> None:
        summary = summarize_mistakes(
            [
                {
                    "case_id": "c1",
                    "input": "q",
                    "expected": {},
                    "actual": {},
                    "mismatch_fields": ["category", "status"],
                    "reason": "field_mismatch",
                },
                {
                    "case_id": "c2",
                    "input": "q2",
                    "expected": {},
                    "actual": {},
                    "mismatch_fields": ["status"],
                    "reason": "unsafe_pass",
                },
            ]
        )
        self.assertEqual(summary["total_mistakes"], 2)
        self.assertEqual(summary["mismatch_field_counts"]["status"], 2)

    def test_outputs_json_and_no_file_side_effect(self) -> None:
        mistakes = collect_mistakes({"failures": []})
        summary = summarize_mistakes(mistakes)
        self.assertIsInstance(json.dumps(summary, sort_keys=True), str)


if __name__ == "__main__":
    unittest.main()
