import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.workbench.coverage_matrix import (
    build_coverage_matrix,
    detect_coverage_gaps,
    summarize_coverage_by_engine,
    summarize_coverage_by_mega_category,
)
from picwise_taxonomy.workbench.schema import build_taxonomy_record


class TestPickwiseTaxonomyWorkbenchCoverageMatrix(unittest.TestCase):
    def _sample_records(self) -> list[dict]:
        return [
            build_taxonomy_record(
                taxonomy_id="dep_001",
                node_type="department",
                canonical_label="Mobility",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                aliases=["mobility gear"],
                greek_aliases=["κινητικότητα"],
                greeklish_aliases=["kinitikotita"],
                typo_aliases=["kinitikotia"],
                spec_fields=["wheel_size"],
                priority_terms=["safety"],
                intent_patterns=["daily commute"],
                ambiguity_rules=["sports overlap"],
                coverage_status="strong",
                review_status="mapped",
            ),
            build_taxonomy_record(
                taxonomy_id="sub_001",
                parent_id="dep_001",
                node_type="subcategory",
                canonical_label="Scooters",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                aliases=["patinia"],
                spec_fields=["wheel_material"],
                priority_terms=["urban use"],
                intent_patterns=["city ride"],
                coverage_status="weak",
                review_status="needs_review",
            ),
            build_taxonomy_record(
                taxonomy_id="fam_001",
                parent_id="sub_001",
                node_type="product_family",
                canonical_label="Urban Scooters",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                aliases=["scooter family"],
                coverage_status="partial",
                review_status="draft",
            ),
            build_taxonomy_record(
                taxonomy_id="gap_001",
                node_type="gap",
                canonical_label="Missing Patinia",
                engine_id="auto_moto_mobility_engine",
                mega_category_id="moto_bicycle_mobility_gear",
                coverage_status="needs_review",
                review_status="needs_mapping",
            ),
        ]

    def test_build_coverage_matrix_works_with_sample_records(self) -> None:
        matrix = build_coverage_matrix(self._sample_records())
        self.assertEqual(matrix["engines"], 1)
        self.assertEqual(matrix["mega_categories"], 1)
        self.assertEqual(matrix["record_count"], 4)

    def test_counts_required_dimensions(self) -> None:
        matrix = build_coverage_matrix(self._sample_records())
        self.assertEqual(matrix["departments"], 1)
        self.assertEqual(matrix["subcategories"], 1)
        self.assertEqual(matrix["product_families"], 1)
        self.assertGreaterEqual(matrix["aliases"], 3)
        self.assertGreaterEqual(matrix["spec_fields"], 2)
        self.assertGreaterEqual(matrix["intent_patterns"], 2)
        self.assertEqual(matrix["gaps"], 1)

    def test_summarizes_by_engine(self) -> None:
        summary = summarize_coverage_by_engine(self._sample_records())
        self.assertIn("auto_moto_mobility_engine", summary)
        self.assertEqual(summary["auto_moto_mobility_engine"]["record_count"], 4)

    def test_summarizes_by_mega_category(self) -> None:
        summary = summarize_coverage_by_mega_category(self._sample_records())
        self.assertIn("moto_bicycle_mobility_gear", summary)
        self.assertEqual(summary["moto_bicycle_mobility_gear"]["record_count"], 4)

    def test_detects_weak_or_missing_coverage(self) -> None:
        gaps = detect_coverage_gaps(self._sample_records())
        self.assertGreaterEqual(len(gaps), 2)
        coverage_statuses = {entry["coverage_status"] for entry in gaps}
        self.assertIn("weak", coverage_statuses)
        self.assertIn("partial", coverage_statuses)

    def test_deterministic_output(self) -> None:
        once = build_coverage_matrix(self._sample_records())
        twice = build_coverage_matrix(self._sample_records())
        self.assertEqual(once, twice)

    def test_json_serializable(self) -> None:
        matrix = build_coverage_matrix(self._sample_records())
        json.dumps(matrix, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
