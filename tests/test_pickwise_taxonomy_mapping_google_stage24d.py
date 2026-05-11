import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.importers.google_taxonomy_importer import parse_google_taxonomy_text
from picwise_taxonomy.mapping.google_stage24d import (
    load_google_source_items_from_local_import_path,
    map_google_source_item_stage24d,
    map_google_source_items_stage24d,
    map_google_taxonomy_local_file_stage24d,
)
from picwise_taxonomy.mega_category_registry import get_mega_category_registry

REAL_GOOGLE_TAXONOMY_FILE = ROOT / "data" / "taxonomy_sources" / "google" / "taxonomy.en-US.txt"


class TestPickwiseTaxonomyMappingGoogleStage24D(unittest.TestCase):
    def _single_item(self, raw_path: str) -> dict:
        return parse_google_taxonomy_text(raw_path)[0]

    def test_can_consume_stage24c_google_source_items_from_local_import_path(self) -> None:
        if not REAL_GOOGLE_TAXONOMY_FILE.exists():
            self.skipTest("Real local Google taxonomy file is required for this Stage 24D proof.")
        loaded = load_google_source_items_from_local_import_path(REAL_GOOGLE_TAXONOMY_FILE)
        self.assertEqual(loaded["file_path"], str(REAL_GOOGLE_TAXONOMY_FILE))
        self.assertTrue(loaded["import_report"]["valid"])
        self.assertGreaterEqual(len(loaded["items"]), 1000)

    def test_apparel_and_accessories_shoes_maps_to_fashion_footwear_target(self) -> None:
        result = map_google_source_item_stage24d(self._single_item("Apparel & Accessories > Shoes"))
        self.assertEqual(result.status.value, "mapped")
        self.assertEqual(result.target.engine_id, "fashion_footwear_jewelry_accessories_engine")
        self.assertEqual(result.target.mega_category_id, "footwear_shoes_sneakers_boots")

    def test_vehicle_parts_path_maps_to_auto_mobility_target(self) -> None:
        result = map_google_source_item_stage24d(
            self._single_item("Vehicles & Parts > Vehicle Parts & Accessories")
        )
        self.assertEqual(result.status.value, "mapped")
        self.assertEqual(result.target.engine_id, "auto_moto_mobility_engine")
        self.assertEqual(result.target.mega_category_id, "car_parts_service_maintenance")

    def test_mobile_phones_path_maps_to_tech_electronics_target(self) -> None:
        result = map_google_source_item_stage24d(
            self._single_item("Electronics > Communications > Telephony > Mobile Phones")
        )
        self.assertEqual(result.status.value, "mapped")
        self.assertEqual(result.target.engine_id, "tech_electronics_office_engine")
        self.assertEqual(result.target.mega_category_id, "phones_mobile_accessories")

    def test_kitchen_and_dining_path_maps_to_home_living_target(self) -> None:
        result = map_google_source_item_stage24d(self._single_item("Home & Garden > Kitchen & Dining"))
        self.assertEqual(result.status.value, "mapped")
        self.assertEqual(result.target.engine_id, "home_living_appliances_engine")
        self.assertEqual(result.target.mega_category_id, "kitchen_cooking_household")

    def test_ambiguous_google_path_is_not_force_mapped(self) -> None:
        result = map_google_source_item_stage24d(self._single_item("Animals & Pet Supplies > Live Animals"))
        self.assertIn(result.status.value, {"needs_review", "unmapped"})
        self.assertIsNone(result.target)

    def test_weak_google_path_is_not_force_mapped(self) -> None:
        result = map_google_source_item_stage24d(self._single_item("Business & Industrial"))
        self.assertIn(result.status.value, {"needs_review", "unmapped"})
        self.assertIsNone(result.target)

    def test_mapped_engine_and_mega_ids_exist_and_relationship_is_valid(self) -> None:
        paths = [
            "Apparel & Accessories > Shoes",
            "Vehicles & Parts > Vehicle Parts & Accessories",
            "Electronics > Communications > Telephony > Mobile Phones",
            "Home & Garden > Kitchen & Dining",
        ]
        engine_ids = {entry["engine_id"] for entry in get_engine_registry()}
        mega_to_engine = {entry["mega_category_id"]: entry["engine_id"] for entry in get_mega_category_registry()}
        for path in paths:
            result = map_google_source_item_stage24d(self._single_item(path))
            self.assertEqual(result.status.value, "mapped")
            self.assertIn(result.target.engine_id, engine_ids)
            self.assertIn(result.target.mega_category_id, mega_to_engine)
            self.assertEqual(mega_to_engine[result.target.mega_category_id], result.target.engine_id)

    def test_batch_mapping_returns_stage24d_only_proof_flags(self) -> None:
        source_items = parse_google_taxonomy_text(
            "\n".join(
                [
                    "Apparel & Accessories > Shoes",
                    "Vehicles & Parts > Vehicle Parts & Accessories",
                    "Electronics > Communications > Telephony > Mobile Phones",
                    "Home & Garden > Kitchen & Dining",
                    "Animals & Pet Supplies > Live Animals",
                    "Business & Industrial",
                ]
            )
        )
        batch = map_google_source_items_stage24d(source_items)
        self.assertEqual(batch["summary"]["total_items"], 6)
        self.assertTrue(batch["stage24d"]["mapped_targets_valid"])
        self.assertFalse(batch["stage24d"]["stage24e_gap_report_created"])
        self.assertFalse(batch["stage24d"]["canonical_registry_created"])

    def test_local_file_stage24d_mapping_does_not_create_stage24e_or_canonical_outputs(self) -> None:
        if not REAL_GOOGLE_TAXONOMY_FILE.exists():
            self.skipTest("Real local Google taxonomy file is required for this Stage 24D proof.")
        report = map_google_taxonomy_local_file_stage24d(REAL_GOOGLE_TAXONOMY_FILE)
        self.assertTrue(report["import_report"]["valid"])
        self.assertFalse(report["stage24e_gap_report_created"])
        self.assertFalse(report["canonical_registry_created"])
        self.assertFalse(report["mapping_batch"]["stage24d"]["stage24e_gap_report_created"])
        self.assertFalse(report["mapping_batch"]["stage24d"]["canonical_registry_created"])


if __name__ == "__main__":
    unittest.main()
