from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search.index_resolver_adapter import resolve_query_with_search_index  # noqa: E402
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402
from picwise_search_memory import (  # noqa: E402
    build_broad_query_suggestions,
    build_canonical_vocabulary_registry,
    build_offline_search_index,
    lookup_offline_search_index,
)


class PicWiseBroadQuerySuggestionsStage7FTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = build_canonical_vocabulary_registry()
        cls.index = build_offline_search_index(cls.registry)

    def test_suggestions_are_built_from_canonical_records_not_maps(self) -> None:
        suggestions = build_broad_query_suggestions(self.registry, "power")
        self.assertGreaterEqual(len(suggestions), 2)
        sources = {row.source for row in suggestions}
        self.assertTrue(sources.issubset({"taxonomy_bridge", "offline_canonical_vocabulary_coverage", "taxonomy_clean_vocabulary"}))
        for row in suggestions:
            self.assertIn("power", row.canonical_term.split())
            self.assertTrue(row.mega_category_id)
            record_hits = [
                rec
                for rec in self.registry.records
                if rec.normalized_term == row.canonical_term and rec.mega_category_id == row.mega_category_id
            ]
            self.assertEqual(len(record_hits), 1)

    def test_unsafe_broad_queries_return_no_suggestions(self) -> None:
        for query in ("bank", "insurance", "apple", "nike", "bosch"):
            with self.subTest(query=query):
                self.assertEqual(build_broad_query_suggestions(self.registry, query), ())

    def test_product_broad_queries_use_broad_suggestion_state_without_cards(self) -> None:
        for query in ("power", "charger", "speaker"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.resolver_state, "broad_query_suggestions")
                self.assertFalse(resolution.result_allowed)
                self.assertEqual(resolution.provider_status, "not_connected")
                self.assertGreaterEqual(len(resolution.suggestions), 2)

    def test_definite_product_tokens_stay_understood_not_broad(self) -> None:
        for query in ("shoes", "jewellery", "bluetooth", "baby monitor"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
                self.assertFalse(resolution.result_allowed)

    def test_power_bank_and_bots_regressions(self) -> None:
        power_bank = resolve_live_search("power bank")
        self.assertEqual(power_bank.resolver_state, "connected_provider_results")
        self.assertTrue(power_bank.result_allowed)

        bots = resolve_live_search("bots")
        self.assertEqual(bots.resolver_state, "not_understood")
        self.assertFalse(bots.result_allowed)

    def test_offline_index_does_not_force_match_for_generated_broad_roots(self) -> None:
        for query in ("power", "tool", "phone"):
            with self.subTest(query=query):
                result = lookup_offline_search_index(query, self.index)
                self.assertEqual(result.status, "no_match")


if __name__ == "__main__":
    unittest.main()
