import inspect
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.nlu_audit import (
    NLUCoverageAuditInput,
    NLUCoverageStrength,
    NLUSafetyStatus,
    build_nlu_coverage_audit,
)
from picwise_taxonomy.nlu_audit import auditor as stage27c_auditor_module
from picwise_taxonomy.nlu_training import NLUTrainingPackBuildInput, build_nlu_training_packs


class TestPickwiseTaxonomyNLUAuditStage27C(unittest.TestCase):
    def test_stage27c_audits_stage27b_training_packs(self) -> None:
        training_result = build_nlu_training_packs()
        audit_result = build_nlu_coverage_audit(NLUCoverageAuditInput(training_result=training_result))
        self.assertEqual(audit_result.total_mega_categories, training_result.total_packs)
        self.assertEqual(audit_result.total_examples, training_result.total_examples)

    def test_stage27c_audits_all_18_mega_categories(self) -> None:
        audit_result = build_nlu_coverage_audit()
        self.assertEqual(audit_result.total_mega_categories, 18)
        self.assertEqual(len(audit_result.rows), 18)

    def test_coverage_strengths_are_deterministic(self) -> None:
        first = build_nlu_coverage_audit()
        second = build_nlu_coverage_audit()
        self.assertEqual(
            [(row.mega_category_id, row.coverage_strength.value) for row in first.rows],
            [(row.mega_category_id, row.coverage_strength.value) for row in second.rows],
        )
        self.assertEqual(first.examples_by_variant_type, second.examples_by_variant_type)
        self.assertEqual(first.examples_by_language_script, second.examples_by_language_script)
        self.assertEqual(first.examples_by_mega_category, second.examples_by_mega_category)

    def test_weak_partial_or_insufficient_categories_are_visible(self) -> None:
        weak_training = build_nlu_training_packs(NLUTrainingPackBuildInput(export_records=()))
        audit_result = build_nlu_coverage_audit(NLUCoverageAuditInput(training_result=weak_training))
        strengths = {row.coverage_strength for row in audit_result.rows}
        self.assertIn(NLUCoverageStrength.INSUFFICIENT_DATA, strengths)
        self.assertGreater(audit_result.insufficient_data_count, 0)

    def test_valid_audit_has_unsafe_passes_equal_zero(self) -> None:
        audit_result = build_nlu_coverage_audit()
        self.assertEqual(audit_result.unsafe_passes, 0)
        self.assertTrue(audit_result.valid)

    def test_unsafe_passes_make_audit_invalid(self) -> None:
        training_result = build_nlu_training_packs()
        first_pack = training_result.packs[0]
        first_example = first_pack.examples[0]
        unsafe_example = replace(first_example, safety_status="unsafe_pass")
        unsafe_pack = replace(first_pack, examples=(unsafe_example, *first_pack.examples[1:]))
        unsafe_packs = (unsafe_pack, *training_result.packs[1:])
        unsafe_training = replace(
            training_result,
            packs=unsafe_packs,
            total_examples=training_result.total_examples,
        )
        audit_result = build_nlu_coverage_audit(NLUCoverageAuditInput(training_result=unsafe_training))
        self.assertGreater(audit_result.unsafe_passes, 0)
        self.assertFalse(audit_result.valid)
        self.assertTrue(any(row.safety_status == NLUSafetyStatus.INVALID_UNSAFE_PASS for row in audit_result.rows))

    def test_missing_signal_coverage_is_reported_honestly(self) -> None:
        training_result = build_nlu_training_packs(NLUTrainingPackBuildInput(export_records=()))
        audit_result = build_nlu_coverage_audit(NLUCoverageAuditInput(training_result=training_result))
        warning_text = " ".join(audit_result.warnings)
        self.assertIn("missing_variant_type:greek_alias", warning_text)
        self.assertIn("missing_variant_type:greeklish_alias", warning_text)
        self.assertIn("missing_variant_type:typo_variant", warning_text)
        self.assertIn("missing_variant_type:spec_intent", warning_text)
        self.assertIn("missing_variant_type:mixed_intent", warning_text)

    def test_stage27c_modules_do_not_import_runtime_modules(self) -> None:
        source = inspect.getsource(stage27c_auditor_module).lower()
        forbidden_runtime_tokens = (
            "picwise_nlu.",
            "src/picwise_nlu",
            "picwise_app",
            "picwise_search",
            "buying_pages",
            "decision_router",
            "specific_product",
        )
        self.assertTrue(all(token not in source for token in forbidden_runtime_tokens))

    def test_stage27c_does_not_include_stage28_logic(self) -> None:
        source = inspect.getsource(stage27c_auditor_module).lower()
        forbidden_stage28_tokens = ("offer", "ranking", "redirect", "affiliate")
        self.assertTrue(all(token not in source for token in forbidden_stage28_tokens))

    def test_stage27c_has_no_commercial_logic(self) -> None:
        source = inspect.getsource(stage27c_auditor_module).lower()
        forbidden_commercial_tokens = (
            "sku",
            "stock",
            "checkout",
            "seller",
            "affiliate",
            "offer_url",
            "product_inventory",
        )
        self.assertTrue(all(token not in source for token in forbidden_commercial_tokens))


if __name__ == "__main__":
    unittest.main()
