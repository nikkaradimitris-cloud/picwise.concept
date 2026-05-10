from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.training_pack import evaluate_stage_19_training_pack  # noqa: E402

_BASELINE_ACCURACY_STAGE20 = 1.0
_MIN_SAFE_ACCURACY = 0.95
_BASELINE_MANUAL_REVIEW_STAGE20 = 3
_FORBIDDEN_FIELDS = {"product", "products", "offer", "offers", "price", "prices", "affiliate", "affiliate_url"}


def _collect_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key).lower())
            keys |= _collect_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            keys |= _collect_keys(nested)
    return keys


class LocalNLUStage21SafetyRegressionTests(unittest.TestCase):
    def test_stage20_pack_accuracy_and_failures_remain_safe(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=200)
        accuracy = float(report.get("accuracy", 0.0))
        failed = int(report.get("failed", 0))
        unsafe_passes = int(report.get("unsafe_passes", -1))
        manual_review_count = int(report.get("manual_review_count", 0))

        self.assertGreaterEqual(accuracy, _MIN_SAFE_ACCURACY)
        if accuracy >= _BASELINE_ACCURACY_STAGE20:
            self.assertEqual(failed, 0)
        self.assertEqual(unsafe_passes, 0)
        self.assertGreaterEqual(manual_review_count, _BASELINE_MANUAL_REVIEW_STAGE20)

    def test_no_claude_api_or_live_llm_in_stage21_related_nlu_files(self) -> None:
        target_files = [
            SRC / "picwise_nlu" / "output_builder.py",
            SRC / "picwise_nlu" / "evaluation_runner.py",
            SRC / "picwise_nlu" / "training_pack.py",
            SRC / "picwise_nlu" / "query_variant_generator.py",
        ]
        merged = "\n".join(path.read_text(encoding="utf-8").lower() for path in target_files)
        for forbidden in (
            "claude",
            "anthropic",
            "openai",
            "live_llm",
            "api_key",
            "http://",
            "https://",
            "requests.",
        ):
            self.assertNotIn(forbidden, merged)

    def test_no_app_router_or_decision_machine_stage21_coupling(self) -> None:
        nlu_targets = [
            SRC / "picwise_nlu" / "output_builder.py",
            SRC / "picwise_nlu" / "evaluation_runner.py",
            SRC / "picwise_nlu" / "training_pack.py",
            SRC / "picwise_nlu" / "query_variant_generator.py",
        ]
        merged = "\n".join(path.read_text(encoding="utf-8").lower() for path in nlu_targets)
        forbidden_imports = (
            "picwise_app.app",
            "picwise_search.decision_router",
            "picwise_search.offer_resolver",
            "src.picwise_engine",
            "picwise_engine.",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(forbidden, merged)

    def test_no_product_offer_price_affiliate_fields_in_stage19_pack_report(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=80)
        keys = _collect_keys(report)
        self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(keys))


if __name__ == "__main__":
    unittest.main()
