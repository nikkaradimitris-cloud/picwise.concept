"""The words search builds each product's text once per catalogue, not on every search.

The debugging's server measure (2026-11-08) found the unsure path 8 to 9 s on 597,270
products: `_select_products_by_words` built every product's text on each search.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import search_selection as ss  # noqa: E402


class CatalogueHaystackCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fields = tuple(
            {"title": f"Fixturon item {i}", "product_type": "Home > Things", "brand": "fixturon"}
            for i in range(50)
        )

    def test_built_once_per_catalogue(self) -> None:
        first = ss._catalogue_haystacks(self.fields)
        self.assertIs(first, ss._catalogue_haystacks(self.fields))
        self.assertEqual(len(first), 50)
        self.assertEqual(first[3][ss._FILTER_FIELDS], "Fixturon item 3 Home > Things fixturon")

    def test_another_catalogue_gets_its_own(self) -> None:
        other = tuple(dict(f, title="Other " + f["title"]) for f in self.fields)
        self.assertIsNot(ss._catalogue_haystacks(self.fields), ss._catalogue_haystacks(other))
        self.assertTrue(ss._catalogue_haystacks(other)[0][ss._FILTER_FIELDS].startswith("Other"))


if __name__ == "__main__":
    unittest.main()
