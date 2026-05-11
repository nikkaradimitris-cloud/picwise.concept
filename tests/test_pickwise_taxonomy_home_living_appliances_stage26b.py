import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs.home_living_appliances import (
    get_home_living_appliances_pack,
    summarize_home_living_appliances_pack,
    validate_home_living_appliances_pack,
)


class TestPickwiseTaxonomyHomeLivingAppliancesStage26B(unittest.TestCase):
    def test_stage_title_is_exact_official(self) -> None:
        pack = get_home_living_appliances_pack()
        self.assertEqual(pack["stage_title"], "Stage 26B — Home / Living / Appliances Deep Pack")

    def test_engine_and_mega_categories_are_locked_registry_ids(self) -> None:
        pack = get_home_living_appliances_pack()
        self.assertEqual(pack["engine_id"], "home_living_appliances_engine")
        mega_ids = [record["mega_category_id"] for record in pack["mega_categories"]]
        self.assertEqual(
            mega_ids,
            [
                "home_appliances_laundry_climate",
                "kitchen_cooking_household",
                "furniture_living_storage_smart_home",
            ],
        )

    def test_stage_26b_prompt_coverage_markers_exist(self) -> None:
        merged = " ".join(
            value
            for record in get_home_living_appliances_pack()["mega_categories"]
            for key in ("departments", "subcategories", "aliases", "spec_fields", "intent_patterns")
            for value in record[key]
        ).lower()
        for marker in (
            "πλυντήρια",
            "ψυγεία",
            "κουζίνες",
            "φούρνοι",
            "στεγνωτήρια",
            "πλυντήρια πιάτων",
            "σκούπες",
            "air fryer",
            "μίξερ",
            "μίνι πίμερ",
            "καφετιέρες",
            "αφυγραντήρες",
            "κλιματιστικά",
            "έπιπλα",
            "φωτισμός",
            "smart home",
            "storage",
        ):
            self.assertIn(marker.lower(), merged)

    def test_summary_and_validation_are_stable(self) -> None:
        summary = summarize_home_living_appliances_pack()
        validation = validate_home_living_appliances_pack()
        self.assertEqual(summary["stage_title"], "Stage 26B — Home / Living / Appliances Deep Pack")
        self.assertTrue(summary["deterministic_ordering"])
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["passed"])


if __name__ == "__main__":
    unittest.main()
