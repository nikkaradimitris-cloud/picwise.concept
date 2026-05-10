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

from picwise_nlu.training_pack import evaluate_stage_19_training_pack, get_stage_19_training_pack  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalNLUStage19LearningSafetyTests(unittest.TestCase):
    def test_generator_source_has_no_claude_api_or_llm_calls(self) -> None:
        source = (SRC / "picwise_nlu" / "query_variant_generator.py").read_text(encoding="utf-8").lower()
        for forbidden in ("claude", "openai", "anthropic", "http://", "https://", "requests.", "api_key", "live_llm"):
            self.assertNotIn(forbidden, source)

    def test_generator_does_not_modify_alias_dictionaries(self) -> None:
        brand_file = SRC / "picwise_nlu" / "brand_resolver.py"
        model_file = SRC / "picwise_nlu" / "model_resolver.py"
        before = (_sha256(brand_file), _sha256(model_file))
        _ = get_stage_19_training_pack(max_variants_per_seed=10)
        after = (_sha256(brand_file), _sha256(model_file))
        self.assertEqual(before, after)

    def test_training_pack_does_not_auto_edit_source_files(self) -> None:
        target_files = [
            SRC / "picwise_nlu" / "query_variant_generator.py",
            SRC / "picwise_nlu" / "training_pack.py",
            SRC / "picwise_nlu" / "expected_dataset.py",
        ]
        before = {str(path): _sha256(path) for path in target_files}
        _ = evaluate_stage_19_training_pack(max_variants_per_seed=10)
        after = {str(path): _sha256(path) for path in target_files}
        self.assertEqual(before, after)

    def test_ambiguous_variants_expect_review_safe_behavior(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=25)
        rows = [
            row
            for row in report.get("results", [])
            if str(row.get("seed_id", "")) == "stage19_ambiguous_unknown"
            or str(row.get("case_id", "")).startswith("stage19_ambiguous_unknown")
        ]
        self.assertGreater(len(rows), 0)
        for row in rows:
            expected = row.get("expected", {})
            self.assertTrue(bool(expected.get("needs_review", True)))

    def test_no_app_router_integration_changes_required(self) -> None:
        app_source = (SRC / "picwise_app" / "app.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("stage_19_training_pack", app_source)
        self.assertNotIn("query_variant_generator", app_source)
        self.assertNotIn("training_pack", app_source)

    def test_no_decision_machine_imports_required(self) -> None:
        generator_source = (SRC / "picwise_nlu" / "query_variant_generator.py").read_text(encoding="utf-8").lower()
        pack_source = (SRC / "picwise_nlu" / "training_pack.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("picwise_search.decision_router", generator_source)
        self.assertNotIn("picwise_search.offer_resolver", generator_source)
        self.assertNotIn("picwise_search.decision_router", pack_source)
        self.assertNotIn("picwise_search.offer_resolver", pack_source)

    def test_safety_outputs_are_json_serializable(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=8)
        self.assertIsInstance(json.dumps(report, sort_keys=True), str)


if __name__ == "__main__":
    unittest.main()
