from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages.fixtures import load_seed_buying_pages  # noqa: E402
from picwise_buying_pages.models import RefreshStatus  # noqa: E402
from picwise_buying_pages.models import SellerReliabilityStatus  # noqa: E402
from picwise_buying_pages.refresh import (  # noqa: E402
    RefreshTransition,
    choose_recommended_product_id,
    determine_refresh_status,
    refresh_page_products,
    transition_refresh_status,
)


class BuyingPagesRefreshLogicTests(unittest.TestCase):
    def test_refresh_keeps_slug_and_updates_products_and_affiliate_urls(self) -> None:
        page = load_seed_buying_pages()[0]
        now = datetime(2026, 5, 9, 10, 0, tzinfo=timezone.utc)
        refreshed_products = tuple(
            replace(
                product,
                affiliate_url=f"https://affiliate.example.com/new/{page.slug}/{idx}",
                rating=3.6 + idx * 0.35,
            )
            for idx, product in enumerate(page.products, start=1)
        )
        refreshed_page = refresh_page_products(
            page,
            refreshed_products=refreshed_products,
            now=now,
            refresh_reason="scheduled_refresh",
        )
        self.assertEqual(refreshed_page.slug, page.slug)
        self.assertEqual(refreshed_page.main_keyword, page.main_keyword)
        self.assertEqual(len(refreshed_page.products), 4)
        self.assertTrue(
            all("/new/" in str(product.affiliate_url) for product in refreshed_page.products)
        )

    def test_refresh_recalculates_recommended_product_id_deterministically(self) -> None:
        page = load_seed_buying_pages()[1]
        now = datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc)
        refreshed_products = (
            replace(page.products[0], availability="limited", rating=3.9, reviews_count=30),
            replace(page.products[1], availability="preorder", rating=4.9, reviews_count=180),
            replace(page.products[2], availability="in_stock", rating=4.1, reviews_count=80),
            replace(page.products[3], availability="in_stock", rating=4.8, reviews_count=320),
        )
        chosen = choose_recommended_product_id(page, refreshed_products)
        refreshed_page = refresh_page_products(page, refreshed_products=refreshed_products, now=now)
        self.assertEqual(refreshed_page.recommended_product_id, chosen)
        self.assertEqual(refreshed_page.recommended_product_id, page.products[3].product_id)

    def test_refresh_status_transitions_cover_all_required_states(self) -> None:
        page = load_seed_buying_pages()[2]
        now = datetime(2026, 5, 9, 15, 0, tzinfo=timezone.utc)
        success = transition_refresh_status(
            page, transition=RefreshTransition.SUCCESS, now=now, refresh_reason="ok"
        )
        due = transition_refresh_status(
            page, transition=RefreshTransition.DUE, now=now, refresh_reason="clock_due"
        )
        failed = transition_refresh_status(
            page, transition=RefreshTransition.FAILED, now=now, refresh_reason="feed_unavailable"
        )
        manual = transition_refresh_status(
            page, transition=RefreshTransition.MANUAL, now=now, refresh_reason="policy_check"
        )
        self.assertEqual(success.refresh_metadata.refresh_status, RefreshStatus.FRESH)
        self.assertEqual(due.refresh_metadata.refresh_status, RefreshStatus.REFRESH_DUE)
        self.assertEqual(failed.refresh_metadata.refresh_status, RefreshStatus.REFRESH_FAILED)
        self.assertEqual(manual.refresh_metadata.refresh_status, RefreshStatus.MANUAL_REQUIRED)

    def test_determine_refresh_status_uses_due_and_failed_manual_flags(self) -> None:
        page = load_seed_buying_pages()[3]
        now = datetime(2026, 5, 9, 11, 0, tzinfo=timezone.utc)
        due_page = replace(
            page,
            refresh_metadata=replace(
                page.refresh_metadata,
                refresh_status=RefreshStatus.FRESH,
                next_refresh_at=now - timedelta(hours=1),
            ),
        )
        self.assertEqual(determine_refresh_status(due_page, now), RefreshStatus.REFRESH_DUE)

        failed_page = replace(
            page,
            refresh_metadata=replace(page.refresh_metadata, refresh_status=RefreshStatus.REFRESH_FAILED),
        )
        self.assertEqual(determine_refresh_status(failed_page, now), RefreshStatus.REFRESH_FAILED)

        manual_page = replace(
            page,
            refresh_metadata=replace(
                page.refresh_metadata, refresh_status=RefreshStatus.MANUAL_REQUIRED
            ),
        )
        self.assertEqual(determine_refresh_status(manual_page, now), RefreshStatus.MANUAL_REQUIRED)

    def test_recommendation_prefers_in_band_products_when_price_band_applies(self) -> None:
        page = next(item for item in load_seed_buying_pages() if item.price_band_applicable)
        refreshed_products = (
            replace(page.products[0], price=79.99, availability="in_stock", rating=5.0, reviews_count=999),
            replace(page.products[1], price=95.0, availability="in_stock", rating=4.3, reviews_count=120),
            replace(page.products[2], price=140.0, availability="preorder", rating=4.1, reviews_count=100),
            replace(page.products[3], price=220.0, availability="limited", rating=4.0, reviews_count=90),
        )
        chosen = choose_recommended_product_id(page, refreshed_products)
        self.assertEqual(chosen, refreshed_products[1].product_id)

    def test_recommendation_ignores_public_ineligible_products(self) -> None:
        page = next(item for item in load_seed_buying_pages() if item.price_band_applicable)
        refreshed_products = (
            replace(page.products[0], seller_reliability_status=SellerReliabilityStatus.BLOCKED, rating=5.0),
            replace(page.products[1], rating=4.2, reviews_count=180),
            replace(page.products[2], rating=4.1, reviews_count=170),
            replace(page.products[3], rating=4.0, reviews_count=160),
        )
        chosen = choose_recommended_product_id(page, refreshed_products)
        self.assertNotEqual(chosen, refreshed_products[0].product_id)

    def test_refresh_rejects_invalid_replacement_products(self) -> None:
        page = load_seed_buying_pages()[0]
        now = datetime(2026, 5, 9, 10, 0, tzinfo=timezone.utc)
        invalid_products = (
            replace(page.products[0], availability="out_of_stock"),
            page.products[1],
            page.products[2],
            page.products[3],
        )
        with self.assertRaises(ValueError):
            refresh_page_products(page, refreshed_products=invalid_products, now=now)


if __name__ == "__main__":
    unittest.main()
