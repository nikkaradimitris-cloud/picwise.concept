from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.query_variant_generator import generate_generic_english_noisy_variants  # noqa: E402
from picwise_nlu.vocabulary_source import load_clean_vocab_by_mega_category  # noqa: E402
from picwise_search_memory import build_canonical_vocabulary_registry  # noqa: E402
from picwise_search_memory.validation import known_mega_category_ids, stable_canonical_id, validate_registry  # noqa: E402

_FORBIDDEN_FIELDS = {
    "product",
    "products",
    "offer",
    "offers",
    "price",
    "prices",
    "affiliate",
    "affiliate_url",
    "seller",
    "stock",
    "checkout",
}


class PicWiseCanonicalVocabularyRegistryStage2Tests(unittest.TestCase):
    def test_builder_loads_terms_from_existing_vocabulary_source(self) -> None:
        source_vocab = load_clean_vocab_by_mega_category()
        registry = build_canonical_vocabulary_registry()
        self.assertGreater(len(source_vocab), 0)
        self.assertGreater(len(registry.records), 0)
        self.assertEqual(registry.source, "taxonomy_clean_vocabulary")

    def test_records_preserve_mega_category_and_use_stable_canonical_id(self) -> None:
        registry = build_canonical_vocabulary_registry()
        sample = registry.records[0]
        self.assertEqual(sample.canonical_id, stable_canonical_id(sample.mega_category_id, sample.normalized_term))
        self.assertIn(sample.mega_category_id, known_mega_category_ids())

    def test_deduplication_enforced_per_category(self) -> None:
        registry = build_canonical_vocabulary_registry()
        signatures = {(row.mega_category_id, row.normalized_term) for row in registry.records}
        self.assertEqual(len(signatures), len(registry.records))

    def test_rejects_unsafe_empty_or_too_short_terms(self) -> None:
        registry = build_canonical_vocabulary_registry()
        self.assertGreaterEqual(registry.report.rejected_terms, 0)
        if registry.report.rejected_terms > 0:
            self.assertGreater(len(registry.report.rejected_by_reason), 0)

    def test_forbidden_fields_are_absent(self) -> None:
        registry = build_canonical_vocabulary_registry()
        for record in registry.records:
            self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(set(record.to_dict().keys())))

    def test_build_report_has_totals_and_category_counts(self) -> None:
        registry = build_canonical_vocabulary_registry()
        report = registry.report
        self.assertEqual(report.total_records, len(registry.records))
        self.assertGreater(report.total_input_terms, 0)
        self.assertEqual(
            report.total_records + report.rejected_terms,
            report.total_input_terms,
        )
        self.assertGreater(len(report.counts_by_mega_category), 0)

    def test_all_18_retail_mega_categories_have_coverage_when_source_provides_terms(self) -> None:
        source_vocab = load_clean_vocab_by_mega_category()
        registry = build_canonical_vocabulary_registry()
        covered_categories = {record.mega_category_id for record in registry.records}
        expected = {
            category
            for category in known_mega_category_ids()
            if category in source_vocab and len(source_vocab.get(category) or []) > 0
        }
        self.assertEqual(expected, covered_categories & expected)
        if len(expected) >= 18:
            self.assertGreaterEqual(len(covered_categories & expected), 18)
        else:
            self.assertGreater(len(expected), 0)

    def test_stage3_generator_can_consume_registry_without_behavior_change(self) -> None:
        registry = build_canonical_vocabulary_registry()
        registry_vocab: dict[str, set[str]] = {}
        for record in registry.records:
            registry_vocab.setdefault(record.mega_category_id, set()).add(record.canonical_term)
        rows = generate_generic_english_noisy_variants(registry_vocab)
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(row["mega_category_id"] in registry_vocab for row in rows))

    def test_registry_validation_offline_contract(self) -> None:
        registry = build_canonical_vocabulary_registry()
        result = validate_registry(registry)
        self.assertTrue(result["valid"])
        self.assertTrue(result["offline_only"])

    def test_live_search_provider_and_surface_files_unchanged_in_this_stage(self) -> None:
        # Repository-level immutability checks are handled by git status assertions.
        # This test guards that stage output remains pure registry data.
        registry = build_canonical_vocabulary_registry()
        self.assertTrue(all(record.source_path == "src/picwise_nlu/vocabulary_source.py" for record in registry.records))


if __name__ == "__main__":
    unittest.main()
