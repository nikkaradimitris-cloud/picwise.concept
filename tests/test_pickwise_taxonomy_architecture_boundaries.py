import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import picwise_taxonomy.architecture_manifest as architecture_manifest_module
from picwise_taxonomy.architecture_manifest import (
    get_taxonomy_architecture_manifest,
    validate_taxonomy_architecture_manifest,
)


class TestPickwiseTaxonomyArchitectureBoundaries(unittest.TestCase):
    def test_architecture_validation_returns_valid_passed(self) -> None:
        result = validate_taxonomy_architecture_manifest()
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])

    def test_manifest_does_not_require_app_router_or_decision_machine_imports(self) -> None:
        source = inspect.getsource(architecture_manifest_module)
        self.assertNotIn("picwise_search.decision_router", source)
        self.assertNotIn("picwise_search.offer_resolver", source)
        self.assertNotIn("picwise_app.app", source)
        self.assertNotIn("picwise_engine", source)

    def test_manifest_does_not_require_local_nlu_runtime_imports(self) -> None:
        source = inspect.getsource(architecture_manifest_module)
        self.assertNotIn("picwise_nlu", source)
        manifest = get_taxonomy_architecture_manifest()
        self.assertFalse(manifest["dependency_boundaries"]["local_nlu_runtime_dependency_required"])

    def test_manifest_does_not_call_network_api_or_llm(self) -> None:
        source = inspect.getsource(architecture_manifest_module).lower()
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("anthropic", source)
        self.assertNotIn("claude", source)

    def test_manifest_confirms_no_product_inventory_responsibility(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        self.assertTrue(manifest["forbidden_responsibilities"]["product_inventory"])
        self.assertFalse(manifest["keeps_owned_product_inventory"])

    def test_manifest_confirms_no_offer_price_affiliate_responsibility(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        self.assertTrue(manifest["forbidden_responsibilities"]["offer_pricing_logic"])
        self.assertTrue(manifest["forbidden_responsibilities"]["affiliate_link_logic"])

    def test_current_taxonomy_packages_import_safely(self) -> None:
        import picwise_taxonomy.coverage_plan  # noqa: F401
        import picwise_taxonomy.deep_packs  # noqa: F401
        import picwise_taxonomy.engine_registry  # noqa: F401
        import picwise_taxonomy.importers  # noqa: F401
        import picwise_taxonomy.mapping  # noqa: F401
        import picwise_taxonomy.mega_category_registry  # noqa: F401
        import picwise_taxonomy.workbench  # noqa: F401


if __name__ == "__main__":
    unittest.main()
