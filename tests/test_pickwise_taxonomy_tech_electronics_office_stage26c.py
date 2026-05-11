import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs.tech_electronics_office import (
    get_tech_electronics_office_pack,
    summarize_tech_electronics_office_pack,
    validate_tech_electronics_office_pack,
)


class TestPickwiseTaxonomyTechElectronicsOfficeStage26C(unittest.TestCase):
    def test_stage_title_is_exact_official(self) -> None:
        pack = get_tech_electronics_office_pack()
        self.assertEqual(pack["stage_title"], "Stage 26C — Tech / Electronics / Office Deep Pack")

    def test_engine_and_mega_categories_are_locked_registry_ids(self) -> None:
        pack = get_tech_electronics_office_pack()
        self.assertEqual(pack["engine_id"], "tech_electronics_office_engine")
        mega_ids = [record["mega_category_id"] for record in pack["mega_categories"]]
        self.assertEqual(
            mega_ids,
            [
                "phones_mobile_accessories",
                "computers_office_peripherals",
                "audio_video_gaming_cameras",
            ],
        )

    def test_stage_26c_prompt_coverage_markers_exist(self) -> None:
        merged = " ".join(
            value
            for record in get_tech_electronics_office_pack()["mega_categories"]
            for key in ("departments", "subcategories", "aliases", "spec_fields", "intent_patterns")
            for value in record[key]
        ).lower()
        for marker in (
            "κινητά",
            "laptops",
            "monitors",
            "printers",
            "routers",
            "power banks",
            "φορτιστές",
            "καλώδια",
            "gaming",
            "audio",
            "tv",
            "cameras",
            "office tech",
            "peripherals",
        ):
            self.assertIn(marker.lower(), merged)

    def test_summary_and_validation_are_stable(self) -> None:
        summary = summarize_tech_electronics_office_pack()
        validation = validate_tech_electronics_office_pack()
        self.assertEqual(summary["stage_title"], "Stage 26C — Tech / Electronics / Office Deep Pack")
        self.assertTrue(summary["deterministic_ordering"])
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["passed"])


if __name__ == "__main__":
    unittest.main()
