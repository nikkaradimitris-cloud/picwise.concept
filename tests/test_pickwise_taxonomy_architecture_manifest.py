import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.architecture_manifest import get_taxonomy_architecture_manifest


class TestPickwiseTaxonomyArchitectureManifest(unittest.TestCase):
    def test_manifest_exists(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        self.assertIsInstance(manifest, dict)
        self.assertTrue(manifest)

    def test_manifest_is_json_serializable(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        serialized = json.dumps(manifest, sort_keys=True)
        self.assertIsInstance(serialized, str)

    def test_manifest_contains_required_layers(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        layer_names = sorted(manifest["layers"].keys())
        self.assertEqual(
            layer_names,
            sorted(
                [
                    "engine_registry",
                    "mega_category_registry",
                    "coverage_plan",
                    "deep_packs",
                    "workbench",
                    "importers",
                    "mapping_layer",
                    "future_canonical_registry",
                    "future_nlu_export",
                ]
            ),
        )

    def test_engine_registry_is_source_of_truth_for_engines(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        layer = manifest["layers"]["engine_registry"]
        self.assertTrue(layer["source_of_truth"])
        self.assertIn("Source of truth", layer["role"])

    def test_mega_category_registry_is_source_of_truth_for_mega_categories(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        layer = manifest["layers"]["mega_category_registry"]
        self.assertTrue(layer["source_of_truth"])
        self.assertIn("Source of truth", layer["role"])

    def test_deep_packs_are_curated_seed_data_not_product_inventory(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        layer = manifest["layers"]["deep_packs"]
        self.assertTrue(layer["curated_seed_data"])
        self.assertTrue(layer["taxonomy_seed_only"])
        self.assertFalse(layer["final_source_of_truth"])
        self.assertTrue(layer["product_inventory_forbidden"])

    def test_importers_are_source_item_producers_only(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        layer = manifest["layers"]["importers"]
        self.assertEqual(layer["importer_scope"], "source_item_producer_only")
        self.assertFalse(layer["maps_directly_to_runtime"])

    def test_mapping_layer_is_implemented_and_future_layers_remain_planned(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        self.assertEqual(manifest["layers"]["mapping_layer"]["status"], "implemented")
        self.assertEqual(manifest["layers"]["future_canonical_registry"]["status"], "planned")
        self.assertEqual(manifest["layers"]["future_nlu_export"]["status"], "planned")

    def test_forbidden_commercial_inventory_fields_declared(self) -> None:
        manifest = get_taxonomy_architecture_manifest()
        expected_terms = {
            "product",
            "products",
            "sku",
            "offer",
            "offers",
            "price",
            "affiliate",
            "seller",
            "store",
            "stock",
            "checkout",
        }
        self.assertTrue(expected_terms.issubset(set(manifest["forbidden_commercial_terms"])))


if __name__ == "__main__":
    unittest.main()
