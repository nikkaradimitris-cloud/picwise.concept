import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy import taxonomy_validation
from picwise_taxonomy.taxonomy_validation import validate_taxonomy_lock


class TestPickwiseTaxonomyLockValidation(unittest.TestCase):
    def test_validate_taxonomy_lock_returns_valid(self) -> None:
        result = validate_taxonomy_lock()
        self.assertTrue(result["valid"])

    def test_engine_count_is_six(self) -> None:
        result = validate_taxonomy_lock()
        self.assertEqual(result["engine_count"], 6)

    def test_mega_category_count_is_eighteen(self) -> None:
        result = validate_taxonomy_lock()
        self.assertEqual(result["mega_category_count"], 18)

    def test_fashion_engine_validation_passes(self) -> None:
        result = validate_taxonomy_lock()
        self.assertTrue(result["engine_validation"]["fashion_engine_exists"])
        self.assertTrue(result["mega_category_validation"]["fashion_engine_has_three_mega_categories"])

    def test_no_closed_decision_machine_dependency_required(self) -> None:
        source = inspect.getsource(taxonomy_validation)
        self.assertNotIn("picwise_search.decision_router", source)
        self.assertNotIn("picwise_search.offer_resolver", source)

    def test_no_local_nlu_runtime_dependency_required(self) -> None:
        source = inspect.getsource(taxonomy_validation)
        self.assertNotIn("picwise_nlu", source)

    def test_no_claude_or_api_or_live_llm_dependency(self) -> None:
        source = inspect.getsource(taxonomy_validation).lower()
        self.assertNotIn("claude", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("anthropic", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)

    def test_no_product_offer_price_affiliate_fields(self) -> None:
        result = validate_taxonomy_lock()
        self.assertFalse(result["engine_validation"]["forbidden_fields_present"])
        self.assertFalse(result["mega_category_validation"]["forbidden_fields_present"])


if __name__ == "__main__":
    unittest.main()
