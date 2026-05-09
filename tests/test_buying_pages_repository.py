from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.fixtures import load_seed_buying_pages  # noqa: E402
from picwise_buying_pages.models import (  # noqa: E402
    BuyingPage,
    FAQItem,
    IndexStatus,
    ProductSlot,
    RefreshMetadata,
    RefreshStatus,
)
from picwise_buying_pages.repository import (  # noqa: E402
    BuyingPagesRepository,
    BuyingPagesRepositoryError,
)
from picwise_buying_pages.slugging import slugify_keyword  # noqa: E402


def make_product(product_id: str) -> ProductSlot:
    return ProductSlot(
        product_id=product_id,
        title=product_id,
        brand=None,
        price=99.0,
        currency="EUR",
        image_url=f"https://img.example.com/{product_id}.jpg",
        product_url=f"https://example.com/{product_id}",
        affiliate_url=None,
        rating=None,
        reviews_count=None,
        availability="in_stock",
        reason_summary="Useful summary",
        buying_reason="Useful reason",
    )


def make_page(main_keyword: str, aliases: tuple[str, ...], recommended_id: str) -> BuyingPage:
    return BuyingPage(
        slug=slugify_keyword(main_keyword),
        main_keyword=main_keyword,
        keyword_aliases=aliases,
        category="misc",
        products=(make_product("a"), make_product("b"), make_product("c"), make_product("d")),
        recommended_product_id=recommended_id,
        faq_items=(FAQItem(question="Q?", answer="A"),),
        related_searches=("related",),
        index_status=IndexStatus.INDEXABLE,
        last_updated=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
        refresh_metadata=RefreshMetadata(
            refresh_status=RefreshStatus.FRESH,
            refresh_interval_hours=24,
            next_refresh_at=datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc),
            last_refresh_at=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
            refresh_reason="repo_test",
        ),
        price_band_applicable=True,
        target_price_min_eur=80.0,
        target_price_max_eur=250.0,
    )


class BuyingPagesRepositoryTests(unittest.TestCase):
    def test_repository_lookup_by_slug_works(self) -> None:
        repository = BuyingPagesRepository(load_seed_buying_pages())
        page = repository.get_by_slug("power-bank-20000mah-for-iphone")
        self.assertIsNotNone(page)
        self.assertEqual(page.main_keyword, "power bank 20000mah for iphone")

    def test_repository_lookup_by_alias_works(self) -> None:
        repository = BuyingPagesRepository(load_seed_buying_pages())
        page = repository.get_by_keyword("Best Dash Cam For Taxi Drivers")
        self.assertIsNotNone(page)
        self.assertEqual(page.slug, "dash-cam-gia-taxi")

    def test_conflicting_alias_across_pages_is_rejected(self) -> None:
        page_a = make_page("keyword one", ("shared alias",), "a")
        page_b = make_page("keyword two", ("Shared-Alias",), "a")
        with self.assertRaises(BuyingPagesRepositoryError):
            BuyingPagesRepository((page_a, page_b))

    def test_duplicate_slug_is_rejected(self) -> None:
        page_a = make_page("keyword one", ("first alias",), "a")
        page_b = make_page("keyword one", ("second alias",), "a")
        with self.assertRaises(BuyingPagesRepositoryError):
            BuyingPagesRepository((page_a, page_b))

    def test_fixture_dataset_is_deterministic(self) -> None:
        first = BuyingPagesRepository(load_seed_buying_pages()).list_pages()
        second = BuyingPagesRepository(load_seed_buying_pages()).list_pages()
        self.assertEqual([page.slug for page in first], [page.slug for page in second])


if __name__ == "__main__":
    unittest.main()
