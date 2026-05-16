from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402


class Stage12BRetail18EnglishNLUActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture_path = ROOT / "tests" / "fixtures" / "stage12b_retail_18_english_nlu_matrix.json"
        cls.fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    def test_every_retail_mega_category_has_english_understanding_proof(self) -> None:
        rows = self.fixture["rows"]
        self.assertEqual(len(rows), 18)
        for row in rows:
            mega_category_id = row["mega_category_id"]
            for query_group in (
                "clean_english_queries",
                "noisy_english_queries",
                "joined_or_missing_letter_english_variants",
            ):
                for query in row.get(query_group, []):
                    with self.subTest(mega_category_id=mega_category_id, query=query, group=query_group):
                        resolution = resolve_live_search(query)
                        self.assertEqual(resolution.mega_category_id, mega_category_id)
                        self.assertEqual(resolution.provider_status, row["expected_provider_status"])
                        self.assertEqual(resolution.resolver_state, row["expected_state_under_current_provider_config"])
                        self.assertFalse(resolution.result_allowed)
                        self.assertIsNone(resolution.lower_level_provider_category)

    def test_negative_near_miss_queries_do_not_accidentally_connect_products(self) -> None:
        for row in self.fixture["rows"]:
            for query in row.get("negative_near_miss_queries", []):
                with self.subTest(query=query):
                    resolution = resolve_live_search(query)
                    self.assertNotEqual(resolution.resolver_state, "connected_provider_results")

    def test_power_banks_keep_connected_provider_behavior_and_fixed_asin_contract(self) -> None:
        row = self.fixture["provider_connected_row"]
        for query in row["clean_english_queries"] + row["noisy_english_queries"] + row["joined_or_missing_letter_english_variants"]:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.mega_category_id, "phones_mobile_accessories")
                self.assertEqual(resolution.lower_level_provider_category, "power_banks")
                self.assertEqual(resolution.provider_status, "connected")
                self.assertEqual(resolution.resolver_state, "connected_provider_results")
                self.assertTrue(resolution.result_allowed)

    def test_out_of_scope_non_retail_verticals_not_forced_into_retail_categories(self) -> None:
        for query in ("ERP", "CRM", "accounting software", "loan", "insurance"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertIsNone(resolution.mega_category_id)
                self.assertIn(resolution.resolver_state, {"not_understood", "low_confidence_manual_review"})

    def test_no_overmatch_guardrail_queries(self) -> None:
        for query in ("bank", "apple", "charger", "galaxy", "bosch", "nike", "insurance", "loan", "ERP", "CRM", "accounting software"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertNotEqual(resolution.resolver_state, "connected_provider_results")


if __name__ == "__main__":
    unittest.main()
