import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.importers.path_parser import (
    build_source_item_from_path,
    parse_taxonomy_path,
    split_taxonomy_path,
)
from picwise_taxonomy.workbench.source_item import validate_source_item


class TestPickwiseTaxonomyImportPathParser(unittest.TestCase):
    def test_split_taxonomy_path_works_with_angle_separator(self) -> None:
        segments = split_taxonomy_path("Apparel & Accessories > Shoes > Athletic Shoes")
        self.assertEqual(segments, ["Apparel & Accessories", "Shoes", "Athletic Shoes"])

    def test_parse_taxonomy_path_returns_segments_leaf_parent_depth(self) -> None:
        parsed = parse_taxonomy_path("Apparel & Accessories > Shoes > Athletic Shoes")
        self.assertEqual(parsed["path_segments"], ["Apparel & Accessories", "Shoes", "Athletic Shoes"])
        self.assertEqual(parsed["leaf_label"], "Athletic Shoes")
        self.assertEqual(parsed["parent_label"], "Shoes")
        self.assertEqual(parsed["depth"], 3)
        self.assertEqual(parsed["normalized_path"], "Apparel & Accessories > Shoes > Athletic Shoes")

    def test_build_source_item_from_path_returns_valid_workbench_source_item(self) -> None:
        item = build_source_item_from_path(
            path="Hardware > Tools > Hand Tools",
            source_name="manual_seed_list",
        )
        validation = validate_source_item(item)
        self.assertTrue(validation["valid"])
        self.assertEqual(item["raw_label"], "Hand Tools")
        self.assertEqual(item["raw_parent_label"], "Tools")

    def test_empty_path_handled_safely(self) -> None:
        parsed = parse_taxonomy_path("   ")
        self.assertEqual(parsed["path_segments"], [])
        self.assertEqual(parsed["leaf_label"], "")
        self.assertEqual(parsed["parent_label"], "")
        self.assertEqual(parsed["depth"], 0)
        self.assertTrue(parsed["is_empty_path"])

    def test_outputs_are_json_serializable(self) -> None:
        parsed = parse_taxonomy_path("Home & Garden > Kitchen & Dining")
        item = build_source_item_from_path(
            path="Home & Garden > Kitchen & Dining",
            source_name="manual_seed_list",
        )
        json.dumps(parsed, sort_keys=True)
        json.dumps(item, sort_keys=True)

    def test_no_inventory_or_commercial_fields_present(self) -> None:
        item = build_source_item_from_path(
            path="Vehicles & Parts > Vehicle Parts & Accessories",
            source_name="manual_seed_list",
        )
        forbidden_keys = {
            "product",
            "products",
            "offer",
            "offers",
            "price",
            "prices",
            "affiliate",
            "seller",
            "sku",
        }
        self.assertTrue(forbidden_keys.isdisjoint(set(item.keys())))


if __name__ == "__main__":
    unittest.main()
