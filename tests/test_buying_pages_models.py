from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.models import (  # noqa: E402
    BuyingPage,
    BuyingPageValidationError,
    FAQItem,
    IndexStatus,
    ProductSlot,
    RefreshMetadata,
    RefreshStatus,
)
from picwise_buying_pages.slugging import slugify_keyword  # noqa: E402


def build_product(product_id: str, price: float = 99.0, currency: str = "EUR") -> ProductSlot:
    return ProductSlot(
        product_id=product_id,
        title=f"Product {product_id}",
        brand="Brand",
        price=price,
        currency=currency,
        image_url=f"https://img.example.com/{product_id}.jpg",
        product_url=f"https://example.com/{product_id}",
        affiliate_url=f"https://aff.example.com/{product_id}",
        rating=4.4,
        reviews_count=120,
        availability="in_stock",
        reason_summary="Strong value and balanced features.",
        buying_reason="Good fit for most buyers in this intent.",
    )


def build_page(
    *,
    keyword_aliases: tuple[str, ...] = ("alias one", "alias two"),
    products: tuple[ProductSlot, ...] | None = None,
    recommended_product_id: str = "p2",
    price_band_applicable: bool = True,
    target_min: float | None = 80.0,
    target_max: float | None = 250.0,
) -> BuyingPage:
    resolved_products = products or (
        build_product("p1", price=90.0),
        build_product("p2", price=110.0),
        build_product("p3", price=135.0),
        build_product("p4", price=199.0),
    )
    return BuyingPage(
        slug=slugify_keyword("best widgets for office"),
        main_keyword="best widgets for office",
        keyword_aliases=keyword_aliases,
        category="office_tools",
        products=resolved_products,
        recommended_product_id=recommended_product_id,
        faq_items=(FAQItem(question="Q1?", answer="A1"), FAQItem(question="Q2?", answer="A2")),
        related_searches=("widgets for remote work",),
        index_status=IndexStatus.INDEXABLE,
        last_updated=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
        refresh_metadata=RefreshMetadata(
            refresh_status=RefreshStatus.FRESH,
            refresh_interval_hours=48,
            next_refresh_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
            last_refresh_at=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
            refresh_reason="scheduled_refresh",
        ),
        price_band_applicable=price_band_applicable,
        target_price_min_eur=target_min,
        target_price_max_eur=target_max,
    )


class BuyingPagesModelTests(unittest.TestCase):
    def test_valid_buying_page_passes(self) -> None:
        page = build_page()
        self.assertEqual(page.slug, "best-widgets-for-office")
        self.assertEqual(len(page.products), 4)

    def test_more_than_10_aliases_fails(self) -> None:
        aliases = tuple(f"alias-{i}" for i in range(11))
        with self.assertRaises(BuyingPageValidationError):
            build_page(keyword_aliases=aliases)

    def test_fewer_or_more_than_4_products_fail(self) -> None:
        with self.assertRaises(BuyingPageValidationError):
            build_page(products=(build_product("p1"), build_product("p2"), build_product("p3")))

        with self.assertRaises(BuyingPageValidationError):
            build_page(
                products=(
                    build_product("p1"),
                    build_product("p2"),
                    build_product("p3"),
                    build_product("p4"),
                    build_product("p5"),
                )
            )

    def test_recommended_product_missing_fails(self) -> None:
        with self.assertRaises(BuyingPageValidationError):
            build_page(recommended_product_id="missing-id")

    def test_duplicate_aliases_after_normalization_fails(self) -> None:
        with self.assertRaises(BuyingPageValidationError):
            build_page(keyword_aliases=("Power-Bank", "power bank"))

    def test_price_band_validation_applies_when_enabled(self) -> None:
        products = (
            build_product("p1", price=70.0),
            build_product("p2", price=90.0),
            build_product("p3", price=120.0),
            build_product("p4", price=150.0),
        )
        with self.assertRaises(BuyingPageValidationError):
            build_page(products=products, price_band_applicable=True)

    def test_price_band_is_skipped_when_not_applicable(self) -> None:
        products = (
            build_product("p1", price=40.0, currency="USD"),
            build_product("p2", price=60.0, currency="USD"),
            build_product("p3", price=75.0, currency="USD"),
            build_product("p4", price=300.0, currency="USD"),
        )
        page = build_page(
            products=products,
            price_band_applicable=False,
            target_min=None,
            target_max=None,
        )
        self.assertFalse(page.price_band_applicable)

    def test_refresh_due_is_not_valid_index_status(self) -> None:
        with self.assertRaises(BuyingPageValidationError):
            BuyingPage(
                slug=slugify_keyword("best widgets for office"),
                main_keyword="best widgets for office",
                keyword_aliases=("alias one",),
                category="office_tools",
                products=(
                    build_product("p1", price=90.0),
                    build_product("p2", price=110.0),
                    build_product("p3", price=135.0),
                    build_product("p4", price=199.0),
                ),
                recommended_product_id="p2",
                faq_items=(FAQItem(question="Q1?", answer="A1"),),
                related_searches=("widgets for remote work",),
                index_status="refresh_due",
                last_updated=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
                refresh_metadata=RefreshMetadata(
                    refresh_status=RefreshStatus.REFRESH_DUE,
                    refresh_interval_hours=48,
                    next_refresh_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
                    last_refresh_at=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
                    refresh_reason="scheduled_refresh",
                ),
                price_band_applicable=True,
                target_price_min_eur=80.0,
                target_price_max_eur=250.0,
            )


if __name__ == "__main__":
    unittest.main()
