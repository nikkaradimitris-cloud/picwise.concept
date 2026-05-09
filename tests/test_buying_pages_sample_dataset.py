from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.fixtures import load_seed_buying_pages  # noqa: E402
from picwise_buying_pages.models import PRICE_BAND_MAX_EUR, PRICE_BAND_MIN_EUR  # noqa: E402
from picwise_buying_pages.repository import BuyingPagesRepository  # noqa: E402


class BuyingPagesSampleDatasetTests(unittest.TestCase):
    def test_dataset_has_expected_page_and_slot_counts(self) -> None:
        pages = load_seed_buying_pages()
        self.assertEqual(len(pages), 100)
        self.assertEqual(sum(len(page.products) for page in pages), 400)

    def test_alias_count_is_near_1000_and_each_page_has_up_to_10(self) -> None:
        pages = load_seed_buying_pages()
        alias_total = sum(len(page.keyword_aliases) for page in pages)
        self.assertGreaterEqual(alias_total, 900)
        self.assertLessEqual(alias_total, 1000)
        self.assertEqual(alias_total, 1000)
        self.assertTrue(all(len(page.keyword_aliases) <= 10 for page in pages))

    def test_every_page_has_exactly_4_products_and_1_valid_recommended_product(self) -> None:
        for page in load_seed_buying_pages():
            self.assertEqual(len(page.products), 4)
            product_ids = {product.product_id for product in page.products}
            self.assertIn(page.recommended_product_id, product_ids)

    def test_repository_lookup_by_slug_and_alias_works(self) -> None:
        repository = BuyingPagesRepository(load_seed_buying_pages())
        by_slug = repository.get_by_slug("power-bank-20000mah-for-iphone")
        self.assertIsNotNone(by_slug)
        self.assertEqual(by_slug.main_keyword, "power bank 20000mah for iphone")

        by_alias = repository.get_by_keyword(
            "power bank 20000mah for iphone comparison sample-001"
        )
        self.assertIsNotNone(by_alias)
        self.assertEqual(by_alias.slug, "power-bank-20000mah-for-iphone")

    def test_slugs_and_aliases_are_unique_and_conflict_free(self) -> None:
        pages = load_seed_buying_pages()
        self.assertEqual(len({page.slug for page in pages}), len(pages))
        repository = BuyingPagesRepository(pages)
        self.assertEqual(len(repository.list_pages()), 100)

    def test_category_coverage_matches_required_scope(self) -> None:
        pages = load_seed_buying_pages()
        categories = {page.category for page in pages}
        self.assertEqual(
            categories,
            {
                "electronics/gadgets",
                "home/appliances",
                "car/taxi/accessories",
                "tools/DIY",
                "beauty/fitness/lifestyle",
                "baby/pet",
                "software/programs",
                "insurance/lead-gen",
            },
        )

    def test_physical_pages_respect_price_band_and_non_physical_skip_it(self) -> None:
        pages = load_seed_buying_pages()
        for page in pages:
            if page.price_band_applicable:
                for product in page.products:
                    self.assertGreaterEqual(product.price, PRICE_BAND_MIN_EUR)
                    self.assertLessEqual(product.price, PRICE_BAND_MAX_EUR)
            else:
                self.assertIsNone(page.target_price_min_eur)
                self.assertIsNone(page.target_price_max_eur)


if __name__ == "__main__":
    unittest.main()
