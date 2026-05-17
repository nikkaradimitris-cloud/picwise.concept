from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search_memory.blind_evaluation import (  # noqa: E402
    build_blind_evaluation_report,
    evaluate_blind_cases,
    generate_blind_evaluation_cases,
)
from picwise_search_memory.canonical_registry import build_canonical_vocabulary_registry  # noqa: E402
from picwise_search_memory.index_builder import build_offline_search_index  # noqa: E402


class PicWiseSearchIndexBlindEvaluationStage6ATests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_canonical_vocabulary_registry()
        self.index = build_offline_search_index(self.registry)
        self.cases = generate_blind_evaluation_cases(self.registry, include_negative_terms=True)
        self.results = evaluate_blind_cases(self.cases, self.index)
        self.report = build_blind_evaluation_report(self.cases, self.results)

    def test_cases_are_generated_from_registry_not_fixed_probe_source(self) -> None:
        self.assertGreater(len(self.registry.records), 0)
        positive_cases = [row for row in self.cases if row.should_match]
        negative_shared_cases = [row for row in self.cases if row.variant_type == "shared_term_negative"]
        self.assertGreater(len(negative_shared_cases), 0)
        self.assertGreater(len(positive_cases), len(self.registry.records) * 0.60)
        canonical_ids_from_cases = {row.canonical_id for row in positive_cases}
        canonical_ids_from_registry = {row.canonical_id for row in self.registry.records}
        self.assertTrue(canonical_ids_from_cases.issubset(canonical_ids_from_registry))
        self.assertGreater(len(canonical_ids_from_cases), int(len(canonical_ids_from_registry) * 0.90))

    def test_all_available_mega_categories_are_represented(self) -> None:
        categories_in_registry = {row.mega_category_id for row in self.registry.records}
        categories_in_cases = {row.expected_mega_category_id for row in self.cases if row.should_match}
        self.assertEqual(categories_in_categories_sorted(categories_in_cases), categories_in_categories_sorted(categories_in_registry))

    def test_generated_variants_and_exact_canonical_cases_are_included(self) -> None:
        variant_types = {row.variant_type for row in self.cases if row.should_match}
        self.assertIn("exact_canonical", variant_types)
        noisy_types = variant_types - {"exact_canonical"}
        self.assertGreater(len(noisy_types), 0)
        self.assertTrue(
            {"joined_words", "missing_letter", "extra_letter", "swapped_adjacent_letters", "repeated_letter", "vowel_drop"}
            .intersection(noisy_types)
        )

    def test_negative_broad_terms_are_included(self) -> None:
        broad_terms = {"bank", "charger", "apple", "nike", "bosch", "insurance", "loan", "erp", "crm", "accounting software"}
        broad_cases = [row for row in self.cases if row.variant_type == "broad_term_negative"]
        self.assertEqual({row.query for row in broad_cases}, broad_terms)
        self.assertTrue(all(not row.should_match for row in broad_cases))

    def test_cross_category_shared_terms_are_marked_as_negative_cases(self) -> None:
        shared_cases = [row for row in self.cases if row.variant_type == "shared_term_negative"]
        self.assertGreater(len(shared_cases), 0)
        self.assertTrue(all(not row.should_match for row in shared_cases))
        self.assertTrue(all(not row.expected_mega_category_id for row in shared_cases))
        self.assertTrue(all(not row.canonical_id for row in shared_cases))

    def test_failed_cases_are_reported_honestly(self) -> None:
        failed_results = [row for row in self.results if not row.passed]
        self.assertEqual(len(self.report.failed_cases), len(failed_results))
        self.assertEqual({row.case_id for row in self.report.failed_cases}, {row.case_id for row in failed_results})

    def test_no_provider_or_offer_fields_in_report_dict(self) -> None:
        forbidden = {"product", "products", "offer", "offers", "price", "prices", "affiliate", "provider"}
        report_dump = str(self.report.to_dict()).lower()
        for key in forbidden:
            with self.subTest(key=key):
                self.assertNotIn(f"'{key}'", report_dump)


def categories_in_categories_sorted(values: set[str]) -> list[str]:
    return sorted(value for value in values if value)


if __name__ == "__main__":
    unittest.main()
