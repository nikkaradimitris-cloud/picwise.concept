import inspect
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.workbench import validation
from picwise_taxonomy.workbench.validation import (
    validate_json_serializable,
    validate_no_inventory_fields,
    validate_workbench_foundation,
)


class TestPickwiseTaxonomyWorkbenchValidation(unittest.TestCase):
    def test_validate_no_inventory_fields_catches_forbidden_keys_recursively(self) -> None:
        payload = {
            "safe": {"nested": [{"ok": "value"}, {"product_name": "x"}]},
            "offers": [],
            "deeper": {"price_value": 10},
        }
        result = validate_no_inventory_fields(payload)
        self.assertFalse(result["valid"])
        self.assertGreaterEqual(result["forbidden_key_count"], 3)

    def test_validate_json_serializable_passes_clean_objects(self) -> None:
        obj = {"a": 1, "b": ["x", "y"], "c": {"nested": True}}
        result = validate_json_serializable(obj)
        self.assertTrue(result["valid"])
        json.dumps(obj, sort_keys=True)

    def test_validate_workbench_foundation_returns_valid_passed(self) -> None:
        result = validate_workbench_foundation()
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])

    def test_no_claude_api_live_llm_required(self) -> None:
        result = validate_workbench_foundation()
        self.assertTrue(result["no_claude_or_api_or_live_llm_dependency"])

        source = inspect.getsource(validation).lower()
        self.assertNotIn("anthropic", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)

    def test_no_app_router_decision_machine_dependency_required(self) -> None:
        source = inspect.getsource(validation)
        self.assertNotIn("picwise_app.app", source)
        self.assertNotIn("picwise_search.decision_router", source)
        self.assertNotIn("picwise_search.offer_resolver", source)

    def test_no_local_nlu_runtime_change_required(self) -> None:
        source = inspect.getsource(validation)
        self.assertNotIn("picwise_nlu", source)


if __name__ == "__main__":
    unittest.main()
