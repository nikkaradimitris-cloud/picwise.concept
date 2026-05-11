import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.importers.google_taxonomy_importer import parse_google_taxonomy_text
from picwise_taxonomy.mapping.gap_report_stage24e import STAGE_24E_TITLE, build_stage24e_gap_report
from picwise_taxonomy.mapping.google_stage24d import map_google_source_items_stage24e_gap_report


class TestPickwiseTaxonomyGapReportStage24E(unittest.TestCase):
    def test_stage24e_uses_stage24d_results_and_collects_unmapped_google_paths(self) -> None:
        source_items = parse_google_taxonomy_text(
            "\n".join(
                [
                    "Apparel & Accessories > Shoes",
                    "Animals & Pet Supplies > Live Animals",
                    "Business & Industrial",
                ]
            )
        )
        report = map_google_source_items_stage24e_gap_report(source_items)
        stage24e = report["stage24e_gap_report"]
        self.assertTrue(report["stage24e_gap_report_created"])
        self.assertEqual(stage24e["stage"], STAGE_24E_TITLE)
        self.assertEqual(stage24e["source_item_count"], 3)
        self.assertEqual(stage24e["mapping_result_count"], 3)
        self.assertGreaterEqual(stage24e["summary"]["gap_count"], 2)
        self.assertIn("unsupported_google_path", stage24e["summary"]["reason_counts"])

    def test_gap_record_contains_required_stage24e_fields(self) -> None:
        source_items = parse_google_taxonomy_text("Animals & Pet Supplies > Live Animals")
        stage24e = map_google_source_items_stage24e_gap_report(source_items)["stage24e_gap_report"]
        gap_record = stage24e["gap_records"][0]
        required_fields = {
            "source_id",
            "source_type",
            "original_path",
            "original_name",
            "normalized_path",
            "normalized_name",
            "reason_code",
            "confidence",
            "mapping_status",
            "operator_action_hint",
            "stage",
        }
        self.assertTrue(required_fields.issubset(set(gap_record.keys())))
        self.assertEqual(gap_record["stage"], STAGE_24E_TITLE)

    def test_weak_and_ambiguous_results_become_gaps_without_unsafe_suggestions(self) -> None:
        source_items = [
            {
                "source_item_id": "g1",
                "source_name": "google_product_taxonomy",
                "source_type": "public_taxonomy_reference",
                "raw_label": "mystery node",
                "raw_path": "Unknown > Mystery",
            },
            {
                "source_item_id": "g2",
                "source_name": "google_product_taxonomy",
                "source_type": "public_taxonomy_reference",
                "raw_label": "running shoes",
                "raw_path": "Fashion > Footwear > Running Shoes",
            },
        ]
        mapped_results = [
            {
                "source_item_id": "g1",
                "status": "needs_review",
                "confidence": "weak",
                "gap_reason": "weak_match_needs_review",
                "normalized_label": "mystery node",
                "normalized_path": "unknown > mystery",
                "operator_action_hint": "",
                "suggested_engine_id": "tools_diy_garden_repair_engine",
                "suggested_mega_category_id": "power_tools_workshop",
            },
            {
                "source_item_id": "g2",
                "status": "needs_review",
                "confidence": "path_match",
                "gap_reason": "ambiguous_engine",
                "normalized_label": "running shoes",
                "normalized_path": "fashion > footwear > running shoes",
                "operator_action_hint": "",
                "suggested_engine_id": "fashion_footwear_jewelry_accessories_engine",
                "suggested_mega_category_id": "footwear_shoes_sneakers_boots",
            },
        ]
        stage24e = build_stage24e_gap_report(source_items=source_items, mapped_results=mapped_results)
        self.assertEqual(stage24e["summary"]["gap_count"], 2)
        self.assertEqual(stage24e["summary"]["mapping_status_counts"]["needs_review"], 2)
        for gap_record in stage24e["gap_records"]:
            self.assertEqual(gap_record["suggested_engine_id"], "")
            self.assertEqual(gap_record["suggested_mega_category_id"], "")

    def test_safe_suggestions_kept_only_when_reason_is_safe(self) -> None:
        source_items = [
            {
                "source_item_id": "g3",
                "source_name": "google_product_taxonomy",
                "source_type": "public_taxonomy_reference",
                "raw_label": "legacy branch",
                "raw_path": "Electronics > Legacy",
            }
        ]
        mapped_results = [
            {
                "source_item_id": "g3",
                "status": "unmapped",
                "confidence": "none",
                "gap_reason": "no_engine_match",
                "normalized_label": "legacy branch",
                "normalized_path": "electronics > legacy",
                "operator_action_hint": "",
                "suggested_engine_id": "tech_electronics_office_engine",
                "suggested_mega_category_id": "phones_mobile_accessories",
            }
        ]
        stage24e = build_stage24e_gap_report(source_items=source_items, mapped_results=mapped_results)
        gap_record = stage24e["gap_records"][0]
        self.assertEqual(gap_record["suggested_engine_id"], "tech_electronics_office_engine")
        self.assertEqual(gap_record["suggested_mega_category_id"], "phones_mobile_accessories")

    def test_uncertain_stage24d_items_are_not_force_mapped(self) -> None:
        source_items = parse_google_taxonomy_text(
            "\n".join(
                [
                    "Animals & Pet Supplies > Live Animals",
                    "Business & Industrial",
                ]
            )
        )
        report = map_google_source_items_stage24e_gap_report(source_items)
        mapped_results = report["stage24d_mapping_batch"]["mapped_results"]
        uncertain = [item for item in mapped_results if item["status"] in {"unmapped", "needs_review"}]
        self.assertEqual(len(uncertain), 2)
        self.assertTrue(all(item["target"] is None for item in uncertain))

    def test_summary_is_deterministic_and_stage24e_does_not_create_stage25_outputs(self) -> None:
        source_items = [
            {
                "source_item_id": "z2",
                "source_name": "google_product_taxonomy",
                "source_type": "public_taxonomy_reference",
                "raw_label": "node two",
                "raw_path": "Business & Industrial",
            },
            {
                "source_item_id": "a1",
                "source_name": "google_product_taxonomy",
                "source_type": "public_taxonomy_reference",
                "raw_label": "node one",
                "raw_path": "Animals & Pet Supplies",
            },
        ]
        mapped_results = [
            {
                "source_item_id": "z2",
                "status": "needs_review",
                "confidence": "weak",
                "gap_reason": "weak_match_needs_review",
                "normalized_label": "node two",
                "normalized_path": "business industrial",
                "operator_action_hint": "",
                "suggested_engine_id": "x",
                "suggested_mega_category_id": "y",
            },
            {
                "source_item_id": "a1",
                "status": "unmapped",
                "confidence": "none",
                "gap_reason": "no_mega_category_match",
                "normalized_label": "node one",
                "normalized_path": "animals pet supplies",
                "operator_action_hint": "",
                "suggested_engine_id": "",
                "suggested_mega_category_id": "",
            },
        ]
        stage24e = build_stage24e_gap_report(source_items=source_items, mapped_results=mapped_results)
        self.assertEqual(stage24e["summary"]["mapping_status_counts"], {"needs_review": 1, "unmapped": 1})
        self.assertEqual(stage24e["summary"]["reason_counts"], {"unsupported_google_path": 2})
        self.assertFalse(stage24e["canonical_registry_created"])
        self.assertFalse(stage24e["coverage_matrix_created"])
        self.assertFalse(stage24e["dedup_rules_created"])


if __name__ == "__main__":
    unittest.main()
