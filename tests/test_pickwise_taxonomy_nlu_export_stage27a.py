import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.nlu_export import (
    TaxonomyNLUExportInput,
    TaxonomyNLUExportStatus,
    build_taxonomy_nlu_export,
    build_taxonomy_nlu_export_catalog,
    validate_export_record,
)
from picwise_taxonomy.nlu_export import exporter as stage27a_exporter_module
from picwise_taxonomy.nlu_export import validation as stage27a_validation_module


class TestPickwiseTaxonomyNLUExportStage27A(unittest.TestCase):
    def test_stage27a_generates_records_from_taxonomy_deep_pack_data(self) -> None:
        result = build_taxonomy_nlu_export()
        self.assertEqual(result.stage_title, "Stage 27A — Taxonomy → Local NLU Export")
        self.assertEqual(result.total_records, 18)
        self.assertGreater(result.active_records, 0)
        self.assertTrue(result.valid)

    def test_records_validate_against_engine_and_mega_registry_locks(self) -> None:
        result = build_taxonomy_nlu_export()
        catalog = build_taxonomy_nlu_export_catalog()
        for record in result.records:
            check = validate_export_record(record, catalog)
            self.assertTrue(check["engine_exists"])
            self.assertTrue(check["mega_exists"])
            self.assertTrue(check["valid"])

    def test_mega_category_must_belong_to_selected_engine(self) -> None:
        result = build_taxonomy_nlu_export()
        catalog = build_taxonomy_nlu_export_catalog()
        for record in result.records:
            check = validate_export_record(record, catalog)
            self.assertTrue(check["mega_belongs_to_engine"])

    def test_export_includes_required_signal_types(self) -> None:
        result = build_taxonomy_nlu_export()
        for record in result.records:
            self.assertTrue(record.aliases)
            self.assertTrue(record.greek_aliases)
            self.assertTrue(record.greeklish_aliases)
            self.assertTrue(record.typo_variants)
            self.assertTrue(record.spec_fields)
            self.assertTrue(record.intent_patterns)
            self.assertTrue(record.priority_terms)
            self.assertTrue(record.source_stage_refs)

    def test_export_includes_all_stage26_deep_pack_mega_categories(self) -> None:
        result = build_taxonomy_nlu_export()
        mega_ids = {record.mega_category_id for record in result.records}
        expected_stage26_ids = {
            "car_parts_service_maintenance",
            "tyres_wheels_car_accessories",
            "moto_bicycle_mobility_gear",
            "home_appliances_laundry_climate",
            "kitchen_cooking_household",
            "furniture_living_storage_smart_home",
            "phones_mobile_accessories",
            "computers_office_peripherals",
            "audio_video_gaming_cameras",
            "health_wellness_safety_devices",
            "beauty_grooming_personal_care",
            "baby_kids_pets_sports_outdoor",
        }
        self.assertTrue(expected_stage26_ids.issubset(mega_ids))

    def test_review_only_and_disabled_gap_never_count_as_active(self) -> None:
        default_pack = stage27a_exporter_module.get_default_source_packs()[0]
        weak_record = dict(default_pack["mega_categories"][0])
        weak_record["alias_terms"] = []
        weak_record["intent_patterns"] = []
        invalid_record = dict(default_pack["mega_categories"][1])
        invalid_record["engine_id"] = "invalid_engine_for_stage27a"
        custom_pack = {
            "source": default_pack.get("source", ""),
            "stage_title": default_pack.get("stage_title", ""),
            "mega_categories": [weak_record, invalid_record],
        }
        result = build_taxonomy_nlu_export(TaxonomyNLUExportInput(source_packs=(custom_pack,)))
        self.assertEqual(result.total_records, 2)
        self.assertEqual(result.active_records, 0)
        self.assertEqual(result.review_only_records, 1)
        self.assertEqual(result.disabled_gap_records, 1)
        self.assertTrue(all(record.status != TaxonomyNLUExportStatus.ACTIVE for record in result.records))

    def test_ordering_and_summary_counts_are_deterministic(self) -> None:
        first = build_taxonomy_nlu_export()
        second = build_taxonomy_nlu_export()
        self.assertEqual([record.export_id for record in first.records], [record.export_id for record in second.records])
        self.assertEqual(first.counts_by_engine, second.counts_by_engine)
        self.assertEqual(first.counts_by_mega_category, second.counts_by_mega_category)
        self.assertEqual(first.total_aliases, second.total_aliases)
        self.assertEqual(first.total_greek_aliases, second.total_greek_aliases)
        self.assertEqual(first.total_greeklish_aliases, second.total_greeklish_aliases)
        self.assertEqual(first.total_typo_variants, second.total_typo_variants)
        self.assertEqual(first.total_spec_fields, second.total_spec_fields)
        self.assertEqual(first.total_intent_patterns, second.total_intent_patterns)
        self.assertEqual(first.total_priority_terms, second.total_priority_terms)

    def test_stage27a_does_not_create_stage27b_or_stage27c_outputs(self) -> None:
        result = build_taxonomy_nlu_export()
        self.assertFalse(hasattr(result, "training_packs"))
        self.assertFalse(hasattr(result, "coverage_audit"))
        self.assertFalse(hasattr(result, "safety_audit"))

    def test_stage27a_modules_do_not_import_local_nlu_or_runtime_modules(self) -> None:
        exporter_source = inspect.getsource(stage27a_exporter_module)
        validation_source = inspect.getsource(stage27a_validation_module)
        combined = f"{exporter_source}\n{validation_source}".lower()
        forbidden_runtime_tokens = (
            "src/picwise_nlu",
            "picwise_nlu.",
            "picwise_app",
            "picwise_search",
            "buying_pages",
            "decision_router",
            "specific_product",
        )
        self.assertTrue(all(token not in combined for token in forbidden_runtime_tokens))

    def test_stage27a_has_no_product_inventory_or_affiliate_logic(self) -> None:
        exporter_source = inspect.getsource(stage27a_exporter_module).lower()
        forbidden_commercial_tokens = (
            "price",
            "sku",
            "stock",
            "checkout",
            "seller",
            "affiliate",
            "offer_url",
            "product_inventory",
        )
        self.assertTrue(all(token not in exporter_source for token in forbidden_commercial_tokens))


if __name__ == "__main__":
    unittest.main()

