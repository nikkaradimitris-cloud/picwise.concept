from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402


class LiveSearchResolverTests(unittest.TestCase):
    def test_power_bank_variants_resolve_connected_provider(self) -> None:
        variants = (
            "παουερ μπανκ",
            "πάουερ μπανκ",
            "παουερμπανκ",
            "φορητός φορτιστής",
            "εξωτερική μπαταρία",
            "μπαταρία κινητού",
            "φορτιστής χωρίς πρίζα",
            "power bank",
            "powerbank",
            "portable charger",
            "battery pack",
            "powr bank",
            "powerbnk",
            "power pank",
            "pwer bank",
            "power bankk",
            "portable chrger",
            "batery pack",
            "battery pak",
            "externe batterie",
            "tragbares ladegerät",
            "handy akku",
            "akku pack",
            "powerbank fürs handy",
            "externe baterie",
            "tragbares ladegerat",
            "handyakku",
            "akku pak",
            "powerbank fur handy",
            "POWER BANK",
            "PowerBank",
            "power-bank",
            "power_bank",
            "power.bank",
            "10000mahpowerbank",
            "usbc powerbank",
        )
        for query in variants:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.canonical_category, "power_banks")
                self.assertEqual(resolution.canonical_query, "power bank")
                self.assertEqual(resolution.provider_key, "manual_amazon_affiliate")
                self.assertEqual(resolution.provider_status, "connected")
                self.assertTrue(resolution.result_allowed)

    def test_unrelated_queries_stay_safe_and_no_result(self) -> None:
        unrelated_queries = (
            "laptop",
            "παπούτσια",
            "ασφάλεια αυτοκινήτου",
            "car insurance",
            "versicherung",
            "travel adapter",
            "wall charger",
            "cable",
            "charging station",
            "phone case",
        )
        for query in unrelated_queries:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertFalse(resolution.result_allowed)
                self.assertIn("manual_review_required", resolution.reason_codes)

    def test_understood_but_not_connected_category(self) -> None:
        resolution = resolve_live_search("goodyear tyres 195/65 r15")
        self.assertEqual(resolution.canonical_category, "car_tyres")
        self.assertEqual(resolution.provider_status, "not_connected")
        self.assertFalse(resolution.result_allowed)
        self.assertIn("provider_not_connected", resolution.reason_codes)


if __name__ == "__main__":
    unittest.main()
