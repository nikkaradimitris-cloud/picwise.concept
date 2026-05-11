import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs.health_beauty_family_lifestyle import (
    get_health_beauty_family_lifestyle_pack,
    summarize_health_beauty_family_lifestyle_pack,
    validate_health_beauty_family_lifestyle_pack,
)


class TestPickwiseTaxonomyHealthBeautyFamilyLifestyleStage26D(unittest.TestCase):
    def test_stage_title_is_exact_official(self) -> None:
        pack = get_health_beauty_family_lifestyle_pack()
        self.assertEqual(pack["stage_title"], "Stage 26D — Health / Beauty / Family / Lifestyle Deep Pack")

    def test_engine_and_mega_categories_are_locked_registry_ids(self) -> None:
        pack = get_health_beauty_family_lifestyle_pack()
        self.assertEqual(pack["engine_id"], "health_beauty_family_lifestyle_engine")
        mega_ids = [record["mega_category_id"] for record in pack["mega_categories"]]
        self.assertEqual(
            mega_ids,
            [
                "health_wellness_safety_devices",
                "beauty_grooming_personal_care",
                "baby_kids_pets_sports_outdoor",
            ],
        )

    def test_stage_26d_prompt_coverage_markers_exist(self) -> None:
        merged = " ".join(
            value
            for record in get_health_beauty_family_lifestyle_pack()["mega_categories"]
            for key in ("departments", "subcategories", "aliases", "spec_fields", "intent_patterns")
            for value in record[key]
        ).lower()
        for marker in (
            "health devices",
            "beauty",
            "grooming",
            "baby/kids",
            "pets",
            "sports",
            "outdoor",
            "wellness",
            "safety devices",
        ):
            self.assertIn(marker.lower(), merged)

    def test_summary_and_validation_are_stable(self) -> None:
        summary = summarize_health_beauty_family_lifestyle_pack()
        validation = validate_health_beauty_family_lifestyle_pack()
        self.assertEqual(summary["stage_title"], "Stage 26D — Health / Beauty / Family / Lifestyle Deep Pack")
        self.assertTrue(summary["deterministic_ordering"])
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["passed"])


if __name__ == "__main__":
    unittest.main()
