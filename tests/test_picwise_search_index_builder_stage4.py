from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.query_variant_generator import _GENERATOR_VERSION as STAGE3_GENERATOR_VERSION  # noqa: E402
from picwise_search_memory import build_canonical_vocabulary_registry, build_offline_search_index  # noqa: E402

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


class PicWiseSearchIndexBuilderStage4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_canonical_vocabulary_registry()
        self.index = build_offline_search_index(self.registry)

    def test_builds_entries_from_canonical_registry(self) -> None:
        self.assertEqual(self.index.report.total_canonical_records, len(self.registry.records))
        self.assertGreater(self.index.report.total_index_entries, 0)

    def test_includes_exact_canonical_terms_as_variants(self) -> None:
        exact_entries = [entry for entry in self.index.entries if entry.variant_type == "exact_canonical"]
        self.assertEqual(len(exact_entries), len(self.registry.records))
        canonical_terms = {record.canonical_term for record in self.registry.records}
        exact_variants = {entry.variant for entry in exact_entries}
        self.assertEqual(canonical_terms, exact_variants)

    def test_includes_generated_noisy_variants(self) -> None:
        generated_entries = [entry for entry in self.index.entries if entry.variant_type != "exact_canonical"]
        self.assertGreater(len(generated_entries), 0)
        self.assertTrue(any(entry.generator_version == STAGE3_GENERATOR_VERSION for entry in generated_entries))

    def test_preserves_canonical_id_and_mega_category(self) -> None:
        canonical_lookup = {record.canonical_id: record for record in self.registry.records}
        for entry in self.index.entries[:500]:
            expected = canonical_lookup[entry.canonical_id]
            self.assertEqual(entry.mega_category_id, expected.mega_category_id)

    def test_produces_stable_deterministic_index_key(self) -> None:
        rebuilt = build_offline_search_index(self.registry)
        first_keys = [entry.index_key for entry in self.index.entries]
        second_keys = [entry.index_key for entry in rebuilt.entries]
        self.assertEqual(first_keys, second_keys)

    def test_deduplicates_duplicate_variants(self) -> None:
        seed_record = self.registry.records[0]
        generated = [
            {
                "canonical_term": seed_record.canonical_term,
                "variant": "bluethoth speaker",
                "mega_category_id": seed_record.mega_category_id,
                "variant_type": "missing_letter",
                "source": "taxonomy_clean_vocabulary",
                "generator_version": STAGE3_GENERATOR_VERSION,
            }
        ]
        duplicated = generated + [dict(generated[0])]
        index = build_offline_search_index(self.registry, duplicated)
        self.assertGreaterEqual(index.report.duplicates_removed, 1)

    def test_rejects_unsafe_or_too_short_variants(self) -> None:
        injected = [
            {
                "canonical_term": self.registry.records[0].canonical_term,
                "variant": "x",
                "mega_category_id": self.registry.records[0].mega_category_id,
                "variant_type": "missing_letter",
                "source": "taxonomy_clean_vocabulary",
                "generator_version": STAGE3_GENERATOR_VERSION,
            }
        ]
        index = build_offline_search_index(self.registry, injected)
        self.assertGreaterEqual(index.report.rejected_count, 1)

    def test_report_contains_totals_and_counts_by_category_and_type(self) -> None:
        report = self.index.report
        self.assertEqual(report.total_index_entries, len(self.index.entries))
        self.assertGreater(report.total_generated_variants, 0)
        self.assertGreater(len(report.counts_by_mega_category_id), 0)
        self.assertGreater(len(report.counts_by_variant_type), 0)
        self.assertIn("exact_canonical", report.counts_by_variant_type)

    def test_forbidden_product_offer_price_affiliate_fields_absent(self) -> None:
        for entry in self.index.entries[:500]:
            self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(set(entry.to_dict().keys())))


if __name__ == "__main__":
    unittest.main()
