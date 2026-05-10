from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.mistake_collector import collect_mistakes, summarize_mistakes  # noqa: E402
from picwise_nlu.training_pack import evaluate_stage_19_training_pack  # noqa: E402

_BASELINE_ACCURACY = 0.3077
_BASELINE_FAILED = 27


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalNLUStage20FailureReductionTests(unittest.TestCase):
    def test_stage_19_failure_count_reduces_safely(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=200)
        self.assertGreaterEqual(report.get("total", 0), 39)
        self.assertGreater(report.get("accuracy", 0.0), _BASELINE_ACCURACY)
        self.assertEqual(report.get("unsafe_passes", -1), 0)
        self.assertLess(report.get("failed", 9999), _BASELINE_FAILED)

    def test_evaluation_report_is_json_serializable(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=120)
        self.assertIsInstance(json.dumps(report, ensure_ascii=True, sort_keys=True), str)

    def test_mistake_collector_still_works(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=120)
        mistakes = collect_mistakes(report)
        summary = summarize_mistakes(mistakes)
        self.assertIsInstance(mistakes, list)
        self.assertIsInstance(summary, dict)
        self.assertIn("total_mistakes", summary)
        self.assertIn("mismatch_field_counts", summary)
        self.assertIn("reason_counts", summary)

    def test_no_claude_api_or_live_llm_dependency_added(self) -> None:
        target_files = [
            SRC / "picwise_nlu" / "query_variant_generator.py",
            SRC / "picwise_nlu" / "training_pack.py",
            SRC / "picwise_nlu" / "output_builder.py",
        ]
        merged = "\n".join(path.read_text(encoding="utf-8").lower() for path in target_files)
        for forbidden in ("claude", "anthropic", "openai", "api_key", "live_llm", "http://", "https://", "requests."):
            self.assertNotIn(forbidden, merged)

    def test_no_runtime_dictionary_auto_mutation(self) -> None:
        target_files = [
            SRC / "picwise_nlu" / "typo_normalizer.py",
            SRC / "picwise_nlu" / "category_detector.py",
            SRC / "picwise_nlu" / "brand_resolver.py",
            SRC / "picwise_nlu" / "model_resolver.py",
            SRC / "picwise_nlu" / "priority_detector.py",
        ]
        before = {str(path): _sha256(path) for path in target_files}
        _ = evaluate_stage_19_training_pack(max_variants_per_seed=200)
        after = {str(path): _sha256(path) for path in target_files}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
