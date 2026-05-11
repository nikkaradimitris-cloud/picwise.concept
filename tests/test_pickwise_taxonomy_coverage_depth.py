import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.coverage_plan import get_coverage_plan_for_mega_category


def _joined(values: list[str]) -> str:
    return " ".join(values).lower()


class TestPickwiseTaxonomyCoverageDepth(unittest.TestCase):
    def _assert_strong_vertical_seed_depth(self, record: dict) -> None:
        self.assertGreaterEqual(len(record["department_seed_examples"]), 6)
        self.assertGreaterEqual(len(record["subcategory_seed_examples"]), 10)
        self.assertGreaterEqual(len(record["product_family_seed_examples"]), 8)
        self.assertGreaterEqual(len(record["spec_schema_seed_examples"]), 8)
        self.assertGreaterEqual(len(record["buying_priority_seed_examples"]), 6)
        self.assertGreaterEqual(len(record["intent_pattern_seed_examples"]), 5)

    def test_fashion_engine_has_strong_dedicated_coverage(self) -> None:
        for mega_category_id in (
            "clothing_apparel_workwear",
            "footwear_shoes_sneakers_boots",
            "jewelry_watches_bags_fashion_accessories",
        ):
            record = get_coverage_plan_for_mega_category(mega_category_id)
            self.assertIsNotNone(record)
            assert record is not None
            self._assert_strong_vertical_seed_depth(record)
            self.assertEqual(record["engine_id"], "fashion_footwear_jewelry_accessories_engine")

    def test_tools_diy_garden_repair_has_strong_coverage(self) -> None:
        for mega_category_id in (
            "power_tools_workshop",
            "hand_tools_consumables_measuring",
            "garden_outdoor_repair_building",
        ):
            record = get_coverage_plan_for_mega_category(mega_category_id)
            self.assertIsNotNone(record)
            assert record is not None
            self._assert_strong_vertical_seed_depth(record)
            self.assertIn("deep_vertical_pack_v1", record["coverage_depth_target"])

    def test_home_living_appliances_is_not_shallow_or_split_into_tiny_fragments(self) -> None:
        record = get_coverage_plan_for_mega_category("home_appliances_laundry_climate")
        self.assertIsNotNone(record)
        assert record is not None
        self._assert_strong_vertical_seed_depth(record)

        joined_departments = _joined(record["department_seed_examples"])
        joined_subcategories = _joined(record["subcategory_seed_examples"])
        joined_families = _joined(record["product_family_seed_examples"])
        merged = " ".join((joined_departments, joined_subcategories, joined_families))
        for expected_keyword in (
            "appliances",
            "laundry",
            "climate",
            "cleaning",
            "refriger",
            "dishwash",
        ):
            self.assertIn(expected_keyword, merged)

    def test_home_engine_collectively_covers_home_kitchen_living_scope(self) -> None:
        ids = (
            "home_appliances_laundry_climate",
            "kitchen_cooking_household",
            "furniture_living_storage_smart_home",
        )
        merged = []
        for mega_category_id in ids:
            record = get_coverage_plan_for_mega_category(mega_category_id)
            self.assertIsNotNone(record)
            assert record is not None
            merged.extend(record["department_seed_examples"])
            merged.extend(record["subcategory_seed_examples"])
            merged.extend(record["product_family_seed_examples"])

        haystack = _joined(merged)
        for expected_keyword in (
            "small",
            "appliance",
            "kitchen",
            "clean",
            "climate",
            "furniture",
            "storage",
            "smart",
        ):
            self.assertIn(expected_keyword, haystack)

    def test_selected_verticals_have_more_than_shallow_seed_counts(self) -> None:
        record = get_coverage_plan_for_mega_category("power_tools_workshop")
        self.assertIsNotNone(record)
        assert record is not None
        total_seed_items = (
            len(record["department_seed_examples"])
            + len(record["subcategory_seed_examples"])
            + len(record["product_family_seed_examples"])
            + len(record["spec_schema_seed_examples"])
            + len(record["buying_priority_seed_examples"])
            + len(record["intent_pattern_seed_examples"])
        )
        self.assertGreaterEqual(total_seed_items, 45)


if __name__ == "__main__":
    unittest.main()
