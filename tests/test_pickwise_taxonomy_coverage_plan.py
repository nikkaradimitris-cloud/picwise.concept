import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.coverage_plan import get_mega_category_coverage_plan
from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.mega_category_registry import get_mega_category_registry


class TestPickwiseTaxonomyCoveragePlan(unittest.TestCase):
    def test_returns_exactly_eighteen_records(self) -> None:
        plan = get_mega_category_coverage_plan()
        self.assertEqual(len(plan), 18)

    def test_every_record_references_locked_engine_and_mega_category(self) -> None:
        valid_engine_ids = {entry["engine_id"] for entry in get_engine_registry()}
        valid_mega_category_ids = {entry["mega_category_id"] for entry in get_mega_category_registry()}
        for record in get_mega_category_coverage_plan():
            self.assertIn(record["engine_id"], valid_engine_ids)
            self.assertIn(record["mega_category_id"], valid_mega_category_ids)

    def test_required_seed_lists_exist_and_are_not_empty(self) -> None:
        required_list_fields = (
            "department_seed_examples",
            "subcategory_seed_examples",
            "product_family_seed_examples",
            "spec_schema_seed_examples",
            "buying_priority_seed_examples",
            "alias_seed_examples",
            "greeklish_seed_examples",
            "typo_seed_examples",
            "intent_pattern_seed_examples",
        )
        for record in get_mega_category_coverage_plan():
            for field in required_list_fields:
                self.assertIn(field, record)
                self.assertIsInstance(record[field], list)
                self.assertGreater(len(record[field]), 0)

    def test_coverage_status_and_depth_target_exist(self) -> None:
        allowed_statuses = {
            "architecture_locked",
            "needs_deep_expansion",
            "partially_seeded",
            "not_started",
        }
        for record in get_mega_category_coverage_plan():
            self.assertIn("coverage_status", record)
            self.assertIn(record["coverage_status"], allowed_statuses)
            self.assertIn("coverage_depth_target", record)
            self.assertIsInstance(record["coverage_depth_target"], str)
            self.assertTrue(record["coverage_depth_target"])

    def test_no_product_offer_price_affiliate_fields_except_required_product_family(self) -> None:
        for record in get_mega_category_coverage_plan():
            keys = set(record.keys())
            self.assertNotIn("offer", keys)
            self.assertNotIn("offers", keys)
            self.assertNotIn("price", keys)
            self.assertNotIn("prices", keys)
            self.assertNotIn("affiliate", keys)
            self.assertNotIn("affiliate_url", keys)
            self.assertIn("product_family_seed_examples", keys)

    def test_json_serializable(self) -> None:
        payload = {"coverage_plan": get_mega_category_coverage_plan()}
        serialized = json.dumps(payload, sort_keys=True)
        self.assertIsInstance(serialized, str)

    def test_deterministic_ordering(self) -> None:
        first = get_mega_category_coverage_plan()
        second = get_mega_category_coverage_plan()
        self.assertEqual(
            [record["mega_category_id"] for record in first],
            [record["mega_category_id"] for record in second],
        )
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()
