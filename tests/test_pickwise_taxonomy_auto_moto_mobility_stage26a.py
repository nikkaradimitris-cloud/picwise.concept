import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs.auto_moto_mobility import (
    get_auto_moto_mobility_pack,
    summarize_auto_moto_mobility_pack,
    validate_auto_moto_mobility_pack,
)


class TestPickwiseTaxonomyAutoMotoMobilityStage26A(unittest.TestCase):
    def test_stage_title_is_exact_official(self) -> None:
        pack = get_auto_moto_mobility_pack()
        self.assertEqual(pack["stage_title"], "Stage 26A — Auto / Moto / Mobility Deep Pack")

    def test_engine_and_mega_categories_are_locked_registry_ids(self) -> None:
        pack = get_auto_moto_mobility_pack()
        self.assertEqual(pack["engine_id"], "auto_moto_mobility_engine")
        mega_ids = [record["mega_category_id"] for record in pack["mega_categories"]]
        self.assertEqual(
            mega_ids,
            [
                "car_parts_service_maintenance",
                "tyres_wheels_car_accessories",
                "moto_bicycle_mobility_gear",
            ],
        )

    def test_stage_26a_prompt_coverage_markers_exist(self) -> None:
        merged = " ".join(
            value
            for record in get_auto_moto_mobility_pack()["mega_categories"]
            for key in ("departments", "subcategories", "aliases", "spec_fields", "intent_patterns")
            for value in record[key]
        ).lower()
        for marker in (
            "αυτοκίνητο",
            "μηχανή",
            "λάστιχα",
            "λάδια",
            "φίλτρα",
            "μπαταρίες",
            "ανταλλακτικά",
            "dash cams",
            "παιδικά καθίσματα",
            "ποδήλατα",
            "e-bikes",
            "πατίνια",
            "ηλεκτρικά πατίνια",
            "mobility gear",
        ):
            self.assertIn(marker.lower(), merged)

    def test_summary_and_validation_are_stable(self) -> None:
        summary = summarize_auto_moto_mobility_pack()
        validation = validate_auto_moto_mobility_pack()
        self.assertEqual(summary["stage_title"], "Stage 26A — Auto / Moto / Mobility Deep Pack")
        self.assertTrue(summary["deterministic_ordering"])
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["passed"])


if __name__ == "__main__":
    unittest.main()
