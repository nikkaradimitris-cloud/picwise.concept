import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.mapping.contracts import GapReason, MappingConfidence, MappingStatus


class TestPickwiseTaxonomyMappingContracts(unittest.TestCase):
    def test_mapping_status_values_are_locked(self) -> None:
        self.assertEqual(
            {status.value for status in MappingStatus},
            {"mapped", "needs_review", "unmapped", "invalid_source"},
        )

    def test_mapping_confidence_values_are_locked(self) -> None:
        self.assertEqual(
            {confidence.value for confidence in MappingConfidence},
            {"exact", "strong_alias", "path_match", "weak", "none"},
        )

    def test_gap_reason_includes_required_reason_codes(self) -> None:
        expected = {
            "no_engine_match",
            "no_mega_category_match",
            "ambiguous_engine",
            "ambiguous_mega_category",
            "unknown_department",
            "unknown_subcategory",
            "unknown_product_family",
            "invalid_source_item",
            "forbidden_inventory_field",
            "weak_match_needs_review",
        }
        self.assertTrue(expected.issubset({reason.value for reason in GapReason}))


if __name__ == "__main__":
    unittest.main()
