import inspect
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_taxonomy.workbench import schema
from picwise_taxonomy.workbench.schema import (
    build_taxonomy_record,
    normalize_taxonomy_record,
    validate_taxonomy_record,
)


class TestPickwiseTaxonomyWorkbenchSchema(unittest.TestCase):
    def _sample_record(self) -> dict:
        return build_taxonomy_record(
            taxonomy_id="node_001",
            parent_id="parent_001",
            engine_id="auto_moto_mobility_engine",
            mega_category_id="moto_bicycle_mobility_gear",
            node_type="department",
            canonical_label="Mobility Gear",
            display_label="Mobility Gear",
            labels=["Mobility Gear", "mobility gear"],
            aliases=["scooter gear"],
            greek_aliases=["πατίνια"],
            greeklish_aliases=["patinia"],
            typo_aliases=["patina"],
            spec_fields=["wheel_size"],
            priority_terms=["safety"],
            intent_patterns=["daily commute"],
            ambiguity_rules=["check sports overlap"],
            source_references=[{"source_name": "manual", "source_type": "manual_seed"}],
            coverage_status="partial",
            review_status="needs_review",
            confidence=0.72,
            notes="seed node",
            schema_version="24A.1",
        )

    def test_build_taxonomy_record_returns_required_fields(self) -> None:
        record = self._sample_record()
        required_fields = {
            "taxonomy_id",
            "parent_id",
            "engine_id",
            "mega_category_id",
            "node_type",
            "canonical_label",
            "display_label",
            "labels",
            "aliases",
            "greek_aliases",
            "greeklish_aliases",
            "typo_aliases",
            "spec_fields",
            "priority_terms",
            "intent_patterns",
            "ambiguity_rules",
            "source_references",
            "coverage_status",
            "review_status",
            "confidence",
            "notes",
            "schema_version",
        }
        self.assertTrue(required_fields.issubset(set(record.keys())))

    def test_normalize_taxonomy_record_deterministic(self) -> None:
        record = self._sample_record()
        normalized_once = normalize_taxonomy_record(record)
        normalized_twice = normalize_taxonomy_record(normalized_once)
        self.assertEqual(normalized_once, normalized_twice)

    def test_validate_taxonomy_record_passes_valid_record(self) -> None:
        result = validate_taxonomy_record(self._sample_record())
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])

    def test_invalid_node_type_fails(self) -> None:
        record = self._sample_record()
        record["node_type"] = "unknown"
        result = validate_taxonomy_record(record)
        self.assertFalse(result["valid"])
        self.assertFalse(result["node_type_valid"])

    def test_invalid_coverage_status_fails(self) -> None:
        record = self._sample_record()
        record["coverage_status"] = "excellent"
        result = validate_taxonomy_record(record)
        self.assertFalse(result["valid"])
        self.assertFalse(result["coverage_status_valid"])

    def test_invalid_review_status_fails(self) -> None:
        record = self._sample_record()
        record["review_status"] = "reviewed"
        result = validate_taxonomy_record(record)
        self.assertFalse(result["valid"])
        self.assertFalse(result["review_status_valid"])

    def test_forbidden_fields_fail(self) -> None:
        for forbidden_key in (
            "product",
            "products",
            "offer",
            "offers",
            "price",
            "affiliate",
            "commission",
            "seller",
            "store",
            "sku",
        ):
            record = self._sample_record()
            record[forbidden_key] = "bad"
            result = validate_taxonomy_record(record)
            self.assertFalse(result["valid"])
            self.assertFalse(result["no_forbidden_inventory_fields"])

    def test_json_serializable(self) -> None:
        record = self._sample_record()
        json.dumps(record, sort_keys=True)
        result = validate_taxonomy_record(record)
        self.assertTrue(result["is_json_serializable"])

    def test_no_external_calls_in_schema_module(self) -> None:
        source = inspect.getsource(schema).lower()
        self.assertNotIn("anthropic", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)


if __name__ == "__main__":
    unittest.main()
