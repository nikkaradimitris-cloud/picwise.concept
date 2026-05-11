import inspect
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.workbench import source_item
from picwise_taxonomy.workbench.source_item import (
    build_source_item,
    normalize_source_item,
    validate_source_item,
)


class TestPickwiseTaxonomyWorkbenchSourceItem(unittest.TestCase):
    def _sample_item(self) -> dict:
        return build_source_item(
            source_item_id="src_001",
            source_name="stage24_seed",
            source_type="manual_seed",
            raw_label="Πατίνια",
            raw_parent_label="Κινητικότητα",
            raw_path="auto/mobility",
            raw_metadata={"sheet": "seed", "row": 12},
            proposed_engine_id="auto_moto_mobility_engine",
            proposed_mega_category_id="moto_bicycle_mobility_gear",
            proposed_node_type="product_family",
            proposed_canonical_label="Scooters",
            proposed_aliases=["scooters"],
            proposed_spec_fields=["wheel_size"],
            proposed_intent_patterns=["city commute"],
            confidence=0.8,
            status="draft",
            notes="seed candidate",
        )

    def test_build_source_item_returns_required_fields(self) -> None:
        item = self._sample_item()
        required_fields = {
            "source_item_id",
            "source_name",
            "source_type",
            "raw_label",
            "raw_parent_label",
            "raw_path",
            "raw_metadata",
            "proposed_engine_id",
            "proposed_mega_category_id",
            "proposed_node_type",
            "proposed_canonical_label",
            "proposed_aliases",
            "proposed_spec_fields",
            "proposed_intent_patterns",
            "confidence",
            "status",
            "notes",
        }
        self.assertTrue(required_fields.issubset(set(item.keys())))

    def test_normalize_source_item_deterministic(self) -> None:
        item = self._sample_item()
        normalized_once = normalize_source_item(item)
        normalized_twice = normalize_source_item(normalized_once)
        self.assertEqual(normalized_once, normalized_twice)

    def test_validate_source_item_passes_valid_manual_seed_item(self) -> None:
        result = validate_source_item(self._sample_item())
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])

    def test_source_type_validation_works(self) -> None:
        item = self._sample_item()
        item["source_type"] = "bad_source"
        result = validate_source_item(item)
        self.assertFalse(result["valid"])
        self.assertFalse(result["source_type_valid"])

    def test_no_api_fetch_scrape_behavior_exists(self) -> None:
        source = inspect.getsource(source_item).lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)
        self.assertNotIn("scrapy", source)
        self.assertNotIn("selenium", source)

    def test_json_serializable(self) -> None:
        item = self._sample_item()
        json.dumps(item, sort_keys=True)
        result = validate_source_item(item)
        self.assertTrue(result["is_json_serializable"])


if __name__ == "__main__":
    unittest.main()
