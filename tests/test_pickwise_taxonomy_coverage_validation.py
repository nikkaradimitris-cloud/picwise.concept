import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy import coverage_plan
from picwise_taxonomy.coverage_plan import (
    get_coverage_plan_for_mega_category,
    summarize_coverage_plan,
    validate_coverage_plan,
)


class TestPickwiseTaxonomyCoverageValidation(unittest.TestCase):
    def test_validate_coverage_plan_returns_valid_and_passed(self) -> None:
        result = validate_coverage_plan()
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])

    def test_exactly_six_engines_and_eighteen_mega_categories(self) -> None:
        result = validate_coverage_plan()
        self.assertEqual(result["engine_count"], 6)
        self.assertEqual(result["mega_category_count"], 18)

    def test_every_engine_has_exactly_three_mega_categories(self) -> None:
        result = validate_coverage_plan()
        per_engine = result["per_engine_mega_category_counts"]
        self.assertEqual(len(per_engine), 6)
        for count in per_engine.values():
            self.assertEqual(count, 3)

    def test_summarize_coverage_plan_returns_counts(self) -> None:
        summary = summarize_coverage_plan()
        self.assertEqual(summary["engine_count"], 6)
        self.assertEqual(summary["mega_category_count"], 18)
        self.assertEqual(len(summary["engines_represented"]), 6)
        self.assertEqual(len(summary["mega_categories_represented"]), 18)
        self.assertIsInstance(summary["coverage_status_counts"], dict)

    def test_local_nlu_proof_scope_not_falsely_claimed_as_full_taxonomy_coverage(self) -> None:
        result = validate_coverage_plan()
        self.assertTrue(result["local_nlu_proof_is_limited"])
        self.assertFalse(result["deep_taxonomy_completed"])

        for mega_category_id in (
            "tyres_wheels_car_accessories",
            "computers_office_peripherals",
            "phones_mobile_accessories",
        ):
            record = get_coverage_plan_for_mega_category(mega_category_id)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertIn(record["coverage_status"], {"partially_seeded", "needs_deep_expansion"})
            self.assertNotEqual(record["coverage_status"], "architecture_locked")

    def test_no_claude_or_api_or_live_llm_required(self) -> None:
        result = validate_coverage_plan()
        self.assertTrue(result["no_claude_or_api_or_live_llm_required"])

        source = inspect.getsource(coverage_plan).lower()
        self.assertNotIn("anthropic", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("https://", source)
        self.assertNotIn("http://", source)

    def test_no_app_router_or_decision_machine_dependency_required(self) -> None:
        result = validate_coverage_plan()
        self.assertTrue(result["no_app_router_or_decision_machine_dependency_required"])

        source = inspect.getsource(coverage_plan)
        self.assertNotIn("picwise_app.app", source)
        self.assertNotIn("picwise_search.decision_router", source)
        self.assertNotIn("picwise_search.offer_resolver", source)


if __name__ == "__main__":
    unittest.main()
