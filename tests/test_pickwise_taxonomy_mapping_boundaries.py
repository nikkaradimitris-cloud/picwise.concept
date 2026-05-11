import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import picwise_taxonomy.mapping.batch_mapper as mapping_batch_mapper_module
import picwise_taxonomy.mapping.gap_router as mapping_gap_router_module
import picwise_taxonomy.mapping.mapper as mapping_mapper_module
import picwise_taxonomy.mapping.validation as mapping_validation_module
from picwise_taxonomy.architecture_manifest import get_taxonomy_architecture_manifest


class TestPickwiseTaxonomyMappingBoundaries(unittest.TestCase):
    def test_mapping_modules_do_not_import_runtime_router_app_or_local_nlu(self) -> None:
        combined_source = (
            inspect.getsource(mapping_batch_mapper_module)
            + inspect.getsource(mapping_gap_router_module)
            + inspect.getsource(mapping_mapper_module)
            + inspect.getsource(mapping_validation_module)
        ).lower()
        self.assertNotIn("picwise_app", combined_source)
        self.assertNotIn("picwise_search", combined_source)
        self.assertNotIn("decision_router", combined_source)
        self.assertNotIn("picwise_nlu", combined_source)

    def test_mapping_layer_is_declared_and_boundary_safe_in_manifest(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        self.assertEqual(manifest["layers"]["mapping_layer"]["status"], "implemented")
        self.assertEqual(manifest["layers"]["mapping_layer"]["path"], "src/picwise_taxonomy/mapping/")
        self.assertFalse(manifest["dependency_boundaries"]["app_router_decision_machine_dependency_required"])
        self.assertFalse(manifest["dependency_boundaries"]["local_nlu_runtime_dependency_required"])
        self.assertTrue(manifest["layers"]["mapping_layer"]["product_inventory_forbidden"])
        self.assertTrue(manifest["layers"]["mapping_layer"]["commercial_fields_forbidden"])


if __name__ == "__main__":
    unittest.main()
