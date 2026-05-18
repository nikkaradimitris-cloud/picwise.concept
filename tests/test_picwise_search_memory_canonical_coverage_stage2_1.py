from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search_memory.canonical_registry import build_canonical_vocabulary_registry  # noqa: E402
from picwise_search_memory.canonical_vocabulary_coverage import (  # noqa: E402
    load_offline_canonical_coverage_by_mega_category,
    required_anchor_terms,
)
from picwise_search_memory.validation import normalize_term, stable_canonical_id  # noqa: E402
from picwise_taxonomy.mega_category_registry import get_mega_category_registry  # noqa: E402

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

_TYPO_PROBE_STRINGS = frozenset(
    {
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
)
_FORBIDDEN_CANONICAL_TYPOS = frozenset({"wach", "mixr"})

_REQUIRED_ANCHORS = {term for term, _category in required_anchor_terms()}


class PicWiseSearchMemoryCanonicalCoverageStage21Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.coverage = load_offline_canonical_coverage_by_mega_category()
        self.registry = build_canonical_vocabulary_registry()
        self.registry_terms = {record.normalized_term for record in self.registry.records}

    def test_coverage_exists_for_all_retail_mega_categories(self) -> None:
        expected_ids = {
            str(row.get("mega_category_id", "")).strip()
            for row in get_mega_category_registry()
            if str(row.get("mega_category_id", "")).strip()
        }
        self.assertEqual(set(self.coverage.keys()), expected_ids)
        for mega_category_id in sorted(expected_ids):
            with self.subTest(mega_category_id=mega_category_id):
                self.assertGreaterEqual(len(self.coverage[mega_category_id]), 30)

    def test_required_clean_anchor_concepts_present(self) -> None:
        for term, mega_category_id in required_anchor_terms():
            with self.subTest(term=term):
                normalized = normalize_term(term)
                self.assertIn(normalized, self.coverage[mega_category_id])
                self.assertIn(normalized, self.registry_terms)

    def test_canonical_vocabulary_has_no_typo_probe_strings(self) -> None:
        for record in self.registry.records:
            with self.subTest(term=record.normalized_term):
                self.assertNotIn(record.normalized_term, _TYPO_PROBE_STRINGS)

        for terms in self.coverage.values():
            for term in terms:
                with self.subTest(term=term):
                    self.assertNotIn(term, _TYPO_PROBE_STRINGS)
                    self.assertNotIn(term, _FORBIDDEN_CANONICAL_TYPOS)

    def test_single_token_product_families_exist_with_source_provenance(self) -> None:
        expected = {
            "watch": "jewelry_watches_bags_fashion_accessories",
            "mixer": "kitchen_cooking_household",
            "boots": "footwear_shoes_sneakers_boots",
            "drill": "power_tools_workshop",
            "keyboard": "computers_office_peripherals",
        }
        by_term = {(row.normalized_term, row.mega_category_id): row for row in self.registry.records}
        for term, category in expected.items():
            with self.subTest(term=term):
                key = (term, category)
                self.assertIn(key, by_term)
                record = by_term[key]
                self.assertIn(record.source, {"offline_canonical_vocabulary_coverage", "taxonomy_bridge", "taxonomy_clean_vocabulary"})
                self.assertIn(record.status, {"active", "offline_source_only"})

    def test_forbidden_commercial_fields_absent_from_records(self) -> None:
        for record in self.registry.records:
            with self.subTest(canonical_id=record.canonical_id):
                self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(set(record.to_dict().keys())))

    def test_canonical_ids_are_deterministic(self) -> None:
        for record in self.registry.records:
            expected = stable_canonical_id(record.mega_category_id, record.normalized_term)
            self.assertEqual(record.canonical_id, expected)

    def test_terms_dedupe_by_normalized_term_and_mega_category(self) -> None:
        signatures = [(record.mega_category_id, record.normalized_term) for record in self.registry.records]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_coverage_records_use_offline_source_metadata(self) -> None:
        coverage_records = [row for row in self.registry.records if row.source == "offline_canonical_vocabulary_coverage"]
        self.assertGreater(len(coverage_records), 0)
        for record in coverage_records[:20]:
            with self.subTest(canonical_id=record.canonical_id):
                self.assertEqual(record.language, "english")
                self.assertEqual(record.status, "offline_source_only")
                self.assertIn("offline_canonical_coverage", record.quality_flags)

    def test_registry_merges_deep_pack_and_coverage_layers(self) -> None:
        sources = {record.source for record in self.registry.records}
        self.assertIn("taxonomy_clean_vocabulary", sources)
        self.assertIn("offline_canonical_vocabulary_coverage", sources)
        self.assertIn("taxonomy_bridge", sources)

    def test_all_mega_categories_represented_in_registry(self) -> None:
        expected_ids = {
            str(row.get("mega_category_id", "")).strip()
            for row in get_mega_category_registry()
            if str(row.get("mega_category_id", "")).strip()
        }
        registry_ids = {record.mega_category_id for record in self.registry.records}
        self.assertEqual(registry_ids, expected_ids)
        for mega_category_id in expected_ids:
            count = sum(1 for record in self.registry.records if record.mega_category_id == mega_category_id)
            self.assertGreaterEqual(count, 30)

    def test_required_anchors_are_clean_canonical_terms(self) -> None:
        for term in _REQUIRED_ANCHORS:
            self.assertEqual(term, normalize_term(term))
            self.assertNotIn(term, _TYPO_PROBE_STRINGS)


if __name__ == "__main__":
    unittest.main()
