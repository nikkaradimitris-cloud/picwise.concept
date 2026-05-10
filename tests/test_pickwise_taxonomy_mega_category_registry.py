import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.mega_category_registry import get_mega_category_registry


class TestPickwiseTaxonomyMegaCategoryRegistry(unittest.TestCase):
    def test_exactly_eighteen_mega_categories(self) -> None:
        mega_categories = get_mega_category_registry()
        self.assertEqual(len(mega_categories), 18)

    def test_mega_category_ids_are_unique(self) -> None:
        ids = [item["mega_category_id"] for item in get_mega_category_registry()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_mega_category_has_valid_engine_id(self) -> None:
        valid_engine_ids = {engine["engine_id"] for engine in get_engine_registry()}
        for mega_category in get_mega_category_registry():
            self.assertIn(mega_category["engine_id"], valid_engine_ids)

    def test_each_engine_has_exactly_three_mega_categories(self) -> None:
        counts = Counter(item["engine_id"] for item in get_mega_category_registry())
        for engine in get_engine_registry():
            self.assertEqual(counts[engine["engine_id"]], 3)

    def test_fashion_mega_categories_exist(self) -> None:
        ids = {item["mega_category_id"] for item in get_mega_category_registry()}
        self.assertIn("clothing_apparel_workwear", ids)
        self.assertIn("footwear_shoes_sneakers_boots", ids)
        self.assertIn("jewelry_watches_bags_fashion_accessories", ids)

    def test_tools_diy_garden_repair_engine_structure_exists(self) -> None:
        engine_to_categories = {
            engine["engine_id"]: set(engine["mega_category_ids"]) for engine in get_engine_registry()
        }
        self.assertIn("tools_diy_garden_repair_engine", engine_to_categories)
        self.assertEqual(
            engine_to_categories["tools_diy_garden_repair_engine"],
            {
                "power_tools_workshop",
                "hand_tools_consumables_measuring",
                "garden_outdoor_repair_building",
            },
        )

    def test_home_kitchen_living_structure_is_cohesive_not_tiny_split(self) -> None:
        engine_map = {engine["engine_id"]: engine for engine in get_engine_registry()}
        home_engine = engine_map["home_living_appliances_engine"]
        self.assertEqual(
            set(home_engine["mega_category_ids"]),
            {
                "home_appliances_laundry_climate",
                "kitchen_cooking_household",
                "furniture_living_storage_smart_home",
            },
        )
        self.assertEqual(len(home_engine["mega_category_ids"]), 3)

    def test_json_serializable(self) -> None:
        payload = {"mega_categories": get_mega_category_registry()}
        serialized = json.dumps(payload, sort_keys=True)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()
