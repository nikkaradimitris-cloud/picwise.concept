from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.fixtures import load_seed_buying_pages  # noqa: E402
from picwise_buying_pages.keyword_clusters import (  # noqa: E402
    MAX_ALIASES_PER_CANDIDATE,
    KeywordSeed,
    build_keyword_clusters,
    generate_keyword_aliases,
)
from picwise_buying_pages.repository import BuyingPagesRepository  # noqa: E402
from picwise_buying_pages.slugging import normalize_keyword_text  # noqa: E402


class BuyingPagesKeywordClusterTests(unittest.TestCase):
    def test_keyword_builder_caps_aliases_to_10(self) -> None:
        seed = KeywordSeed(
            category="electronics/gadgets",
            product="mirrorless camera",
            brand="Picwise",
            specs=("4k", "wifi", "stabilization", "travel", "creator"),
        )
        aliases = generate_keyword_aliases(seed)
        clusters = build_keyword_clusters((seed,))
        self.assertGreater(len(aliases), MAX_ALIASES_PER_CANDIDATE)
        self.assertEqual(len(clusters), 1)
        self.assertLessEqual(len(clusters[0].keyword_aliases), MAX_ALIASES_PER_CANDIDATE)

    def test_keyword_builder_normalizes_and_dedupes_aliases(self) -> None:
        seed = KeywordSeed(
            category="electronics",
            product="Power Bank",
            brand="Power-Bank",
            specs=("Fast Charge", "fast-charge"),
        )
        aliases = generate_keyword_aliases(seed)
        normalized = [normalize_keyword_text(alias) for alias in aliases]
        self.assertEqual(len(normalized), len(set(normalized)))
        self.assertTrue(all(alias == alias.strip() for alias in aliases))

    def test_keyword_builder_filters_conflicts_with_published_aliases(self) -> None:
        repository = BuyingPagesRepository(load_seed_buying_pages())
        conflict_seed = KeywordSeed(
            category="electronics/gadgets",
            product="power bank 20000mah for iphone",
            brand="Picwise",
            specs=("comparison sample-001",),
        )
        clusters = build_keyword_clusters((conflict_seed,), published_repository=repository)
        self.assertEqual(clusters, ())


if __name__ == "__main__":
    unittest.main()
