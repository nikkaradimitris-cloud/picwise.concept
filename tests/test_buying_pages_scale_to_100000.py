from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages import (  # noqa: E402
    SCALE_100K_TOTAL_TARGET,
    build_100k_registry,
    get_100k_distribution,
)


class BuyingPagesScaleTo100000Tests(unittest.TestCase):
    def test_distribution_totals_exactly_100000(self) -> None:
        expected = get_100k_distribution()
        self.assertEqual(sum(expected.values()), 100000)
        self.assertEqual(
            expected,
            {
                "electronics/gadgets": 25000,
                "home/appliances": 20000,
                "car/taxi/accessories": 15000,
                "tools/DIY": 15000,
                "beauty/fitness/lifestyle": 10000,
                "baby/pet": 10000,
                "software/programs": 3000,
                "insurance/lead-gen": 2000,
            },
        )

    def test_registry_supports_100000_without_materializing_static_files(self) -> None:
        registry = build_100k_registry()
        self.assertEqual(registry.total_pages, SCALE_100K_TOTAL_TARGET)
        self.assertLessEqual(len(registry._ranges), 8)  # noqa: SLF001 - asserts virtual range storage

        counter: Counter[str] = Counter()
        seen_slugs: set[str] = set()
        for descriptor in registry.iter_descriptors():
            counter[descriptor.category] += 1
            slug = descriptor.main_keyword.replace(" ", "-")
            self.assertNotIn(slug, seen_slugs)
            seen_slugs.add(slug)

        self.assertEqual(counter, Counter(get_100k_distribution()))
        self.assertEqual(len(seen_slugs), 100000)

    def test_lookup_strategy_is_safe_and_deterministic(self) -> None:
        registry = build_100k_registry()
        first = registry.descriptor_at(0)
        again = registry.descriptor_at(0)
        self.assertEqual(first.main_keyword, again.main_keyword)
        self.assertEqual(first.category, "electronics/gadgets")
        self.assertTrue(registry.descriptor_at(10).candidate_only)
        self.assertFalse(registry.descriptor_at(11).candidate_only)
        with self.assertRaises(IndexError):
            registry.descriptor_at(100000)

    def test_price_band_flag_is_only_disabled_for_non_standard_categories(self) -> None:
        registry = build_100k_registry()
        exempt_categories = {"software/programs", "insurance/lead-gen"}
        for ordinal in (0, 24999, 25000, 60000, 95000, 99999):
            descriptor = registry.descriptor_at(ordinal)
            if descriptor.category in exempt_categories:
                self.assertFalse(descriptor.price_band_applicable)
            else:
                self.assertTrue(descriptor.price_band_applicable)


if __name__ == "__main__":
    unittest.main()
