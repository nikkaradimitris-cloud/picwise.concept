from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.query_variant_generator import generate_noisy_variants_for_term  # noqa: E402
from picwise_search_memory.blind_evaluation import generate_blind_evaluation_cases  # noqa: E402
from picwise_search_memory.canonical_registry import build_canonical_vocabulary_registry  # noqa: E402
from picwise_search_memory.index_builder import build_offline_search_index  # noqa: E402
from picwise_search_memory.index_lookup import lookup_offline_search_index  # noqa: E402
from picwise_search_memory.taxonomy_search_memory_bridge import (  # noqa: E402
    build_taxonomy_search_memory_bridge_report,
    export_taxonomy_search_memory_terms,
)

_TYPO_PROBE_STRINGS = {
    "coffe grindr",
    "vaccum cleaner",
    "bluethoth speker",
    "gming mouse",
    "car batery",
    "bike helmt",
    "winter jakcet",
    "baby car seet",
    "usb caible",
}


class PicWiseSearchMemoryTaxonomyBridgeStage7CTests(unittest.TestCase):
    def test_bridge_report_inspects_stages_and_reports_missing_honestly(self) -> None:
        report = build_taxonomy_search_memory_bridge_report()
        self.assertIn("stage24c", report.stages_inspected)
        self.assertIn("stage27c", report.stages_inspected)
        self.assertGreater(len(report.files_found), 0)
        self.assertGreater(len(report.disconnected_assets), 0)
        self.assertGreaterEqual(len(report.gaps_found), 1)
        self.assertTrue(any(gap.reason in {"missing", "disconnected"} for gap in report.gaps_found))

    def test_bridge_exports_clean_canonical_terms_only(self) -> None:
        terms = export_taxonomy_search_memory_terms()
        self.assertGreater(len(terms), 0)
        for term in terms[:500]:
            with self.subTest(term=term.normalized_term):
                self.assertEqual(term.canonical_term, term.normalized_term)
                self.assertNotIn(term.normalized_term, _TYPO_PROBE_STRINGS)
                self.assertEqual(term.language, "english")
                self.assertEqual(term.status, "offline_source_only")
                self.assertIn("taxonomy_bridge", term.quality_flags)
                self.assertNotIn("product", term.__dict__)
                self.assertNotIn("offer", term.__dict__)
                self.assertNotIn("price", term.__dict__)
                self.assertNotIn("affiliate", term.__dict__)

    def test_registry_consumes_bridge_records_with_source_metadata(self) -> None:
        registry = build_canonical_vocabulary_registry()
        bridge_records = [record for record in registry.records if record.source == "taxonomy_bridge"]
        self.assertGreater(len(bridge_records), 0)
        for record in bridge_records[:100]:
            with self.subTest(canonical_id=record.canonical_id):
                self.assertIn("taxonomy_bridge", record.quality_flags)
                self.assertTrue({"nlu_export", "nlu_training_pack", "deep_pack"}.intersection(set(record.quality_flags)))
                self.assertTrue(record.source_file)
                self.assertTrue(record.source_path)

    def test_index_includes_bridge_records_and_lookup_resolves_generated_variant(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry=registry)
        bridge_records = [record for record in registry.records if record.source == "taxonomy_bridge"]
        self.assertGreater(len(bridge_records), 0)
        bridge_canonical_ids = {record.canonical_id for record in bridge_records}
        index_canonical_ids = {entry.canonical_id for entry in index.entries}
        self.assertTrue(bridge_canonical_ids.issubset(index_canonical_ids))

        seed = bridge_records[0]
        generated = generate_noisy_variants_for_term(seed.canonical_term, seed.mega_category_id)
        variant = next((row["variant"] for row in generated if row.get("variant_type") != "exact_canonical"), "")
        self.assertTrue(variant)
        lookup = lookup_offline_search_index(variant, index)
        self.assertEqual(lookup.status, "match")
        self.assertIsNotNone(lookup.matched_entry)
        self.assertEqual(lookup.matched_entry.canonical_id, seed.canonical_id)

    def test_blind_evaluation_contains_bridge_sourced_generated_cases(self) -> None:
        registry = build_canonical_vocabulary_registry()
        cases = generate_blind_evaluation_cases(registry, include_negative_terms=True)
        bridge_generated_cases = [
            case
            for case in cases
            if case.should_match and case.source.startswith("taxonomy_bridge+") and case.variant_type != "exact_canonical"
        ]
        self.assertGreater(len(bridge_generated_cases), 0)


if __name__ == "__main__":
    unittest.main()
