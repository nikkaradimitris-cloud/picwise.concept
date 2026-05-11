import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.importers import import_validation
from picwise_taxonomy.importers.import_validation import (
    reject_inventory_like_source_record,
    validate_imported_source_items,
    validate_importer_foundation,
)
from picwise_taxonomy.importers.path_parser import build_source_item_from_path


class TestPickwiseTaxonomyImportValidation(unittest.TestCase):
    def test_validate_imported_source_items_passes_valid_source_items(self) -> None:
        items = [
            build_source_item_from_path(
                path="Apparel & Accessories > Shoes > Athletic Shoes",
                source_name="manual_seed_list",
                source_type="manual_seed",
            )
        ]
        result = validate_imported_source_items(items)
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])

    def test_reject_inventory_like_source_record_flags_forbidden_fields(self) -> None:
        record = {
            "path": "Hardware > Tools",
            "price": "10.00",
            "store_offer": "x",
            "sku": "sku-1",
        }
        result = reject_inventory_like_source_record(record)
        self.assertFalse(result["valid"])
        self.assertGreaterEqual(result["forbidden_key_count"], 3)

    def test_taxonomy_safe_product_family_classification_not_rejected(self) -> None:
        record = {
            "path": "Hardware > Tools",
            "metadata": {"product_family": "tools", "product_families": ["tools"]},
        }
        result = reject_inventory_like_source_record(record)
        self.assertTrue(result["valid"])

    def test_validate_importer_foundation_returns_valid_passed(self) -> None:
        result = validate_importer_foundation()
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])

    def test_no_claude_api_or_live_llm_required(self) -> None:
        result = validate_importer_foundation()
        self.assertTrue(result["no_claude_or_api_or_live_llm_dependency"])

    def test_no_app_router_or_decision_machine_dependency_required(self) -> None:
        source = inspect.getsource(import_validation)
        self.assertNotIn("picwise_app.app", source)
        self.assertNotIn("picwise_search.decision_router", source)
        self.assertNotIn("picwise_search.offer_resolver", source)

    def test_no_local_nlu_runtime_change_required(self) -> None:
        source = inspect.getsource(import_validation)
        self.assertNotIn("picwise_nlu", source)


if __name__ == "__main__":
    unittest.main()
