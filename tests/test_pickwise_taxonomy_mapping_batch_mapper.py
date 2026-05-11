import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.mapping import map_source_items_batch
from picwise_taxonomy.workbench.source_item import build_source_item


class TestPickwiseTaxonomyMappingBatchMapper(unittest.TestCase):
    def test_batch_mapper_returns_expected_summary_counts(self) -> None:
        mapped_item = build_source_item(
            source_item_id="batch_001",
            source_name="batch_source",
            source_type="manual_seed",
            raw_label="demolition hammers",
            raw_parent_label="power tools workshop",
            raw_path="Tools > Power Tools / Workshop > demolition hammers",
            proposed_engine_id="tools_diy_garden_repair_engine",
            proposed_mega_category_id="power_tools_workshop",
        )
        weak_or_unmapped_item = build_source_item(
            source_item_id="batch_002",
            source_name="batch_source",
            source_type="manual_seed",
            raw_label="mystery branch",
            raw_parent_label="mystery",
            raw_path="Unknown > Mystery > branch",
        )
        invalid_item = dict(mapped_item)
        invalid_item["source_item_id"] = "batch_003"
        invalid_item["price"] = "20"

        batch = map_source_items_batch([mapped_item, weak_or_unmapped_item, invalid_item])
        self.assertEqual(batch["summary"]["total_items"], 3)
        self.assertEqual(len(batch["mapped_results"]), 3)
        self.assertGreaterEqual(batch["summary"]["status_counts"].get("mapped", 0), 1)
        self.assertGreaterEqual(batch["summary"]["status_counts"].get("invalid_source", 0), 1)
        self.assertGreaterEqual(batch["summary"]["gap_count"], 1)
        self.assertIn("tools_diy_garden_repair_engine", batch["summary"]["engine_counts"])
        self.assertIn("power_tools_workshop", batch["summary"]["mega_category_counts"])


if __name__ == "__main__":
    unittest.main()
