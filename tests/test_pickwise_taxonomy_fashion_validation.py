import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.deep_packs import fashion_footwear_jewelry_accessories
from picwise_taxonomy.deep_packs.fashion_footwear_jewelry_accessories import (
    get_fashion_mega_category_pack,
    summarize_fashion_footwear_jewelry_accessories_pack,
    validate_fashion_footwear_jewelry_accessories_pack,
)


class TestPickwiseTaxonomyFashionValidation(unittest.TestCase):
    def test_validate_returns_valid_and_passed(self) -> None:
        result = validate_fashion_footwear_jewelry_accessories_pack()
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])

    def test_summary_returns_counts(self) -> None:
        summary = summarize_fashion_footwear_jewelry_accessories_pack()
        self.assertEqual(summary["engine_id"], "fashion_footwear_jewelry_accessories_engine")
        self.assertEqual(summary["mega_category_count"], 3)
        self.assertEqual(len(summary["mega_categories_covered"]), 3)
        self.assertEqual(len(summary["department_counts"]), 3)
        self.assertEqual(len(summary["product_family_seed_counts"]), 3)
        self.assertEqual(len(summary["spec_field_counts"]), 3)
        self.assertEqual(len(summary["intent_pattern_counts"]), 3)

    def test_all_three_mega_categories_validate(self) -> None:
        for mega_category_id in (
            "clothing_apparel_workwear",
            "footwear_shoes_sneakers_boots",
            "jewelry_watches_bags_fashion_accessories",
        ):
            record = get_fashion_mega_category_pack(mega_category_id)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record["engine_id"], "fashion_footwear_jewelry_accessories_engine")
            self.assertIn("expansion_status", record)
            self.assertTrue(record["expansion_status"])

    def test_fashion_engine_is_dedicated_and_not_under_lifestyle(self) -> None:
        result = validate_fashion_footwear_jewelry_accessories_pack()
        self.assertTrue(result["fashion_engine_is_dedicated"])
        self.assertTrue(result["fashion_engine_not_under_lifestyle"])

    def test_no_claude_api_or_live_llm_required(self) -> None:
        result = validate_fashion_footwear_jewelry_accessories_pack()
        self.assertTrue(result["no_claude_or_api_or_live_llm_required"])

        source = inspect.getsource(fashion_footwear_jewelry_accessories).lower()
        self.assertNotIn("anthropic", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)

    def test_no_app_router_decision_machine_dependency_required(self) -> None:
        result = validate_fashion_footwear_jewelry_accessories_pack()
        self.assertTrue(result["no_app_router_or_decision_machine_dependency_required"])

        source = inspect.getsource(fashion_footwear_jewelry_accessories)
        self.assertNotIn("picwise_app.app", source)
        self.assertNotIn("picwise_search.decision_router", source)
        self.assertNotIn("picwise_search.offer_resolver", source)

    def test_no_local_nlu_runtime_change_required(self) -> None:
        result = validate_fashion_footwear_jewelry_accessories_pack()
        self.assertTrue(result["no_local_nlu_runtime_change_required"])

        source = inspect.getsource(fashion_footwear_jewelry_accessories)
        self.assertNotIn("picwise_nlu", source)


if __name__ == "__main__":
    unittest.main()
