import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.mapping import map_source_item_to_taxonomy, route_mapping_result_to_gap
from picwise_taxonomy.workbench.source_item import build_source_item


class TestPickwiseTaxonomyMappingMapper(unittest.TestCase):
    def _build_item(self, **overrides: object) -> dict:
        item = build_source_item(
            source_item_id="source_map_001",
            source_name="test_source",
            source_type="manual_seed",
            raw_label="demolition hammers",
            raw_parent_label="power tools workshop",
            raw_path="Tools > Power Tools / Workshop > demolition hammers",
            proposed_engine_id="tools_diy_garden_repair_engine",
            proposed_mega_category_id="power_tools_workshop",
            proposed_aliases=["demolition hammers"],
        )
        item.update(overrides)
        return item

    def test_valid_source_maps_to_correct_engine_and_mega_category(self) -> None:
        result = map_source_item_to_taxonomy(self._build_item())
        self.assertEqual(result.status.value, "mapped")
        self.assertEqual(result.target.engine_id, "tools_diy_garden_repair_engine")
        self.assertEqual(result.target.mega_category_id, "power_tools_workshop")

    def test_valid_source_maps_to_product_family_when_seed_exists(self) -> None:
        result = map_source_item_to_taxonomy(
            self._build_item(
                source_item_id="source_map_002",
                raw_label="demolition hammer platforms",
                raw_parent_label="demolition hammers",
                raw_path="Tools > Power Tools / Workshop > demolition hammer platforms",
            )
        )
        self.assertEqual(result.status.value, "mapped")
        self.assertEqual(result.target.product_family, "demolition hammer platforms")

    def test_ambiguous_item_routes_to_gap_not_mapped(self) -> None:
        source_item = self._build_item(
            source_item_id="source_map_003",
            raw_label="running shoes",
            raw_parent_label="shoes",
            raw_path="Fashion > Footwear > running shoes",
            proposed_engine_id="home_living_appliances_engine",
            proposed_mega_category_id="footwear_shoes_sneakers_boots",
        )
        result = map_source_item_to_taxonomy(source_item)
        gap = route_mapping_result_to_gap(result, source_item=source_item)
        self.assertEqual(result.status.value, "needs_review")
        self.assertNotEqual(result.status.value, "mapped")
        self.assertIsNotNone(gap)

    def test_weak_match_routes_to_review_or_gap_not_mapped(self) -> None:
        source_item = self._build_item(
            source_item_id="source_map_004",
            raw_label="mystery branch",
            raw_parent_label="misc",
            raw_path="Workshop Stuff > mystery branch",
            proposed_engine_id="",
            proposed_mega_category_id="",
        )
        result = map_source_item_to_taxonomy(source_item)
        gap = route_mapping_result_to_gap(result, source_item=source_item)
        self.assertNotEqual(result.status.value, "mapped")
        self.assertIn(result.confidence.value, {"weak", "none"})
        self.assertIsNotNone(gap)

    def test_invalid_source_item_routes_to_invalid_source_gap(self) -> None:
        result = map_source_item_to_taxonomy({"source_item_id": "broken"})
        self.assertEqual(result.status.value, "invalid_source")
        self.assertEqual(result.gap_reason.value, "invalid_source_item")
        self.assertIsNotNone(route_mapping_result_to_gap(result, source_item={"source_item_id": "broken"}))

    def test_forbidden_inventory_fields_are_rejected_to_gap(self) -> None:
        source_item = self._build_item(source_item_id="source_map_005")
        source_item["price"] = "10"
        result = map_source_item_to_taxonomy(source_item)
        self.assertEqual(result.status.value, "invalid_source")
        self.assertEqual(result.gap_reason.value, "forbidden_inventory_field")
        gap = route_mapping_result_to_gap(result, source_item=source_item)
        self.assertEqual(gap["reason_code"], "forbidden_inventory_field")


if __name__ == "__main__":
    unittest.main()
