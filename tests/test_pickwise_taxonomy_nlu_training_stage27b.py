import inspect
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.nlu_export import build_taxonomy_nlu_export
from picwise_taxonomy.nlu_training import (
    NLUTrainingPackBuildInput,
    NLUTrainingPackStatus,
    QueryVariantType,
    build_nlu_training_packs,
    build_training_catalog,
    validate_training_example,
)
from picwise_taxonomy.nlu_training import pack_builder as stage27b_pack_builder_module


class TestPickwiseTaxonomyNLUTrainingStage27B(unittest.TestCase):
    def test_stage27b_builds_training_packs_from_stage27a_export_records(self) -> None:
        export_result = build_taxonomy_nlu_export()
        training_result = build_nlu_training_packs(NLUTrainingPackBuildInput(export_records=export_result.records))
        source_ids = {record.export_id for record in export_result.records}
        referenced_ids = {
            source_ref
            for pack in training_result.packs
            for example in pack.examples
            for source_ref in example.source_taxonomy_refs
            if source_ref in source_ids
        }
        self.assertTrue(referenced_ids)
        self.assertTrue(source_ids.issubset(referenced_ids))

    def test_stage27b_represents_all_18_mega_categories(self) -> None:
        training_result = build_nlu_training_packs()
        self.assertEqual(training_result.total_packs, 18)
        self.assertEqual(len(training_result.examples_by_mega_category), 18)

    def test_packs_with_enough_signals_reach_100_deterministic_variants(self) -> None:
        training_result = build_nlu_training_packs()
        ready_packs = [pack for pack in training_result.packs if pack.status == NLUTrainingPackStatus.READY]
        self.assertTrue(ready_packs)
        self.assertTrue(
            all(
                sum(1 for example in pack.examples if example.safety_status == "safe_training_example") >= 100
                for pack in ready_packs
            )
        )

    def test_insufficient_signals_are_not_fake_filled(self) -> None:
        export_result = build_taxonomy_nlu_export()
        first = export_result.records[0]
        weak_record = replace(
            first,
            aliases=("basic alias",),
            greek_aliases=(),
            greeklish_aliases=(),
            typo_variants=(),
            spec_fields=(),
            intent_patterns=(),
            priority_terms=(),
        )
        training_result = build_nlu_training_packs(NLUTrainingPackBuildInput(export_records=(weak_record,)))
        weak_pack = next(pack for pack in training_result.packs if pack.mega_category_id == weak_record.mega_category_id)
        self.assertIn(weak_pack.status, {NLUTrainingPackStatus.PARTIAL, NLUTrainingPackStatus.INSUFFICIENT_DATA})
        self.assertLess(len(weak_pack.examples), 100)
        self.assertIn("needs_more_taxonomy_input", weak_pack.warnings)

    def test_examples_include_required_variant_types_when_signals_exist(self) -> None:
        training_result = build_nlu_training_packs()
        target = next(pack for pack in training_result.packs if pack.status == NLUTrainingPackStatus.READY)
        variant_types = {example.variant_type.value for example in target.examples}
        expected = {
            QueryVariantType.ALIAS.value,
            QueryVariantType.GREEK_ALIAS.value,
            QueryVariantType.GREEKLISH_ALIAS.value,
            QueryVariantType.TYPO_VARIANT.value,
            QueryVariantType.SPEC_INTENT.value,
            QueryVariantType.PRIORITY_TERM.value,
            QueryVariantType.MIXED_INTENT.value,
        }
        self.assertTrue(expected.issubset(variant_types))

    def test_examples_include_expected_engine_and_mega_category_ids(self) -> None:
        training_result = build_nlu_training_packs()
        for pack in training_result.packs:
            for example in pack.examples:
                self.assertEqual(example.expected_engine_id, pack.engine_id)
                self.assertEqual(example.expected_mega_category_id, pack.mega_category_id)

    def test_examples_validate_against_locked_engine_and_mega_registry(self) -> None:
        training_result = build_nlu_training_packs()
        catalog = build_training_catalog()
        for pack in training_result.packs:
            for example in pack.examples:
                check = validate_training_example(example, catalog)
                self.assertTrue(check["engine_exists"])
                self.assertTrue(check["mega_exists"])
                self.assertTrue(check["valid"])

    def test_ordering_ids_and_summary_counts_are_deterministic(self) -> None:
        first = build_nlu_training_packs()
        second = build_nlu_training_packs()
        self.assertEqual(
            [pack.pack_id for pack in first.packs],
            [pack.pack_id for pack in second.packs],
        )
        self.assertEqual(
            [example.example_id for pack in first.packs for example in pack.examples],
            [example.example_id for pack in second.packs for example in pack.examples],
        )
        self.assertEqual(first.examples_by_engine, second.examples_by_engine)
        self.assertEqual(first.examples_by_mega_category, second.examples_by_mega_category)
        self.assertEqual(first.examples_by_variant_type, second.examples_by_variant_type)
        self.assertEqual(first.examples_by_language_script, second.examples_by_language_script)

    def test_stage27b_modules_do_not_import_runtime_modules(self) -> None:
        source = inspect.getsource(stage27b_pack_builder_module).lower()
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

    def test_stage27b_has_no_commercial_logic(self) -> None:
        source = inspect.getsource(stage27b_pack_builder_module).lower()
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
