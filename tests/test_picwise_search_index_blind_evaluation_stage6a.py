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

_FIXED_PROBE_QUERIES = {
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

_STAGE7A_REQUIRED_CATEGORIES = {
    "home_appliances_laundry_climate",
    "kitchen_cooking_household",
    "furniture_living_storage_smart_home",
    "phones_mobile_accessories",
    "computers_office_peripherals",
    "audio_video_gaming_cameras",
    "car_parts_service_maintenance",
    "tyres_wheels_car_accessories",
    "moto_bicycle_mobility_gear",
    "power_tools_workshop",
    "hand_tools_consumables_measuring",
    "garden_outdoor_repair_building",
    "health_wellness_safety_devices",
    "beauty_grooming_personal_care",
    "baby_kids_pets_sports_outdoor",
    "clothing_apparel_workwear",
    "footwear_shoes_sneakers_boots",
    "jewelry_watches_bags_fashion_accessories",
}


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
        self.assertEqual(categories_in_registry, _STAGE7A_REQUIRED_CATEGORIES)
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

    def test_stage6a_thresholds_pass_honestly_on_full_offline_index(self) -> None:
        from picwise_search_memory.blind_evaluation import run_offline_blind_index_evaluation

        report = run_offline_blind_index_evaluation()
        self.assertTrue(report.can_proceed_to_stage5)
        self.assertGreaterEqual(report.mega_category_accuracy, 0.90)
        self.assertGreaterEqual(report.canonical_accuracy, 0.70)
        self.assertLessEqual(report.wrong_category_rate, 0.05)
        self.assertLessEqual(report.false_positive_rate, 0.02)
        self.assertGreaterEqual(report.broad_term_safety_rate, 0.95)
        self.assertTrue(all(report.threshold_status.values()))

    def test_generated_blind_cases_include_terms_beyond_fixed_acceptance_probes(self) -> None:
        positive_queries = {row.query for row in self.cases if row.should_match}
        non_probe_queries = positive_queries - _FIXED_PROBE_QUERIES
        self.assertGreater(len(non_probe_queries), len(_FIXED_PROBE_QUERIES) * 10)

    def test_generated_blind_cases_include_unknown_terms_not_fixed_probes_for_all_categories(self) -> None:
        non_probe_positive_cases = [row for row in self.cases if row.should_match and row.query not in _FIXED_PROBE_QUERIES]
        self.assertGreater(len(non_probe_positive_cases), 0)
        categories_with_non_probe = {row.expected_mega_category_id for row in non_probe_positive_cases}
        self.assertEqual(categories_with_non_probe, _STAGE7A_REQUIRED_CATEGORIES)

    def test_bridge_sourced_blind_cases_are_included(self) -> None:
        bridge_cases = [row for row in self.cases if row.should_match and row.source.startswith("taxonomy_bridge+")]
        self.assertGreater(len(bridge_cases), 0)
        categories = {row.expected_mega_category_id for row in bridge_cases}
        self.assertEqual(categories, _STAGE7A_REQUIRED_CATEGORIES)

    def test_stage7d_single_token_blind_coverage_minimums(self) -> None:
        single_positive = [row for row in self.cases if row.should_match and len(row.query.split()) == 1]
        single_generated = [row for row in single_positive if row.variant_type != "exact_canonical"]
        self.assertGreaterEqual(len(single_positive), 20)
        self.assertGreaterEqual(len(single_generated), 10)

    def test_stage7d_single_token_acceptance_probes_and_safety(self) -> None:
        expected = {
            "watch": "jewelry_watches_bags_fashion_accessories",
            "wach": "jewelry_watches_bags_fashion_accessories",
            "mixer": "kitchen_cooking_household",
            "mixr": "kitchen_cooking_household",
        }
        from picwise_search_memory.index_lookup import lookup_offline_search_index

        for query, category in expected.items():
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "match")
                self.assertIsNotNone(result.matched_entry)
                self.assertEqual(result.matched_entry.mega_category_id, category)
                self.assertGreaterEqual(result.score, 0.84)

        for query in ("bank", "charger", "apple", "nike", "bosch", "insurance", "loan", "erp", "crm", "accounting software"):
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "no_match")
                self.assertIsNone(result.matched_entry)


def categories_in_categories_sorted(values: set[str]) -> list[str]:
    return sorted(value for value in values if value)


if __name__ == "__main__":
    unittest.main()
