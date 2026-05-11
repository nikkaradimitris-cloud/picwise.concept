import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.workbench.gap_registry import (
    build_gap_record,
    create_gap_from_missing_term,
    validate_gap_record,
)


class TestPickwiseTaxonomyWorkbenchGapRegistry(unittest.TestCase):
    def _sample_gap(self) -> dict:
        return build_gap_record(
            gap_id="gap_patini",
            raw_term="πατίνια",
            normalized_term="πατίνια",
            suggested_engine_id="auto_moto_mobility_engine",
            suggested_mega_category_id="moto_bicycle_mobility_gear",
            suggested_department="mobility",
            suggested_subcategory="scooters",
            suggested_product_family="urban scooters",
            related_terms=["scooter"],
            greeklish_terms=["patinia"],
            typo_terms=["patina"],
            reason="missing taxonomy node",
            severity="high",
            status="needs_mapping",
            source="operator_gap_report",
            notes="stage24 test gap",
            schema_version="24A.1",
        )

    def test_build_gap_record_returns_required_fields(self) -> None:
        gap = self._sample_gap()
        required = {
            "gap_id",
            "raw_term",
            "normalized_term",
            "suggested_engine_id",
            "suggested_mega_category_id",
            "suggested_department",
            "suggested_subcategory",
            "suggested_product_family",
            "related_terms",
            "greeklish_terms",
            "typo_terms",
            "reason",
            "severity",
            "status",
            "source",
            "notes",
            "schema_version",
        }
        self.assertTrue(required.issubset(set(gap.keys())))

    def test_create_gap_from_missing_term_patini_works(self) -> None:
        gap = create_gap_from_missing_term("πατίνια")
        self.assertEqual(gap["raw_term"], "πατίνια")
        self.assertEqual(gap["suggested_engine_id"], "auto_moto_mobility_engine")
        self.assertEqual(gap["suggested_mega_category_id"], "moto_bicycle_mobility_gear")
        self.assertIn(gap["status"], {"needs_mapping", "mapped"})

    def test_gap_can_map_to_auto_moto_when_supplied(self) -> None:
        gap = create_gap_from_missing_term(
            "πατίνια",
            suggested_engine_id="auto_moto_mobility_engine",
            suggested_mega_category_id="moto_bicycle_mobility_gear",
        )
        self.assertEqual(gap["suggested_engine_id"], "auto_moto_mobility_engine")
        self.assertEqual(gap["suggested_mega_category_id"], "moto_bicycle_mobility_gear")
        self.assertEqual(gap["status"], "mapped")

    def test_severity_status_validation_works(self) -> None:
        bad_gap = self._sample_gap()
        bad_gap["severity"] = "severe"
        bad_gap["status"] = "unknown"
        result = validate_gap_record(bad_gap)
        self.assertFalse(result["valid"])
        self.assertFalse(result["severity_valid"])
        self.assertFalse(result["status_valid"])

    def test_gap_statuses_include_required_values(self) -> None:
        statuses = {"new_gap", "needs_mapping", "mapped", "needs_deep_pack", "covered", "rejected"}
        for status in statuses:
            gap = self._sample_gap()
            gap["status"] = status
            result = validate_gap_record(gap)
            self.assertTrue(result["status_valid"])

    def test_json_serializable(self) -> None:
        gap = self._sample_gap()
        json.dumps(gap, sort_keys=True)
        result = validate_gap_record(gap)
        self.assertTrue(result["is_json_serializable"])

    def test_no_product_offer_price_affiliate_fields(self) -> None:
        for forbidden in ("product", "offer", "price", "affiliate"):
            gap = self._sample_gap()
            gap[forbidden] = "forbidden"
            result = validate_gap_record(gap)
            self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
