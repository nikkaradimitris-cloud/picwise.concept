from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderFeedConfig, ProviderProduct, SearchProviderFeedMetadata  # noqa: E402
from picwise_providers.search_selection import (  # noqa: E402
    mask_provider_product_url,
    select_provider_products_for_query,
)
from picwise_providers.state import (  # noqa: E402
    load_eligible_provider_feed_products,
    resolve_search_provider_feed_product_selection,
)
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402

_REAL_FEED_ENV = "AWIN_FEED_FILE"
_REAL_FEED_DEFAULT = Path(r"C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz")

_REAL_FEED_QUERIES = (
    "monitor",
    "gaming monitor",
    "portable monitor",
    "tv box",
    "vacuum cleaner",
    "printer",
    "speaker",
    "projector",
    "cycling",
    "power adapter",
    "laptop",
)


def _real_feed_path() -> Path:
    return Path(os.environ.get(_REAL_FEED_ENV, str(_REAL_FEED_DEFAULT)))


def _sample_products() -> tuple[ProviderProduct, ...]:
    rows = [
        {
            "provider_key": "awin",
            "provider_product_id": "SKU-1",
            "title": "Curved Gaming Monitor 27 inch QHD",
            "brand": "KTC",
            "category_text": "Monitors",
            "product_url": "https://merchant.example/products/sku-1",
            "image_url": "https://cdn.example/img-1.jpg",
            "price_text": "199.99",
            "availability_text": "in stock",
            "currency": "USD",
            "raw": {
                "product_name": "Curved Gaming Monitor 27 inch QHD",
                "category_name": "Monitors",
                "merchant_category": "Computer Monitors",
                "keywords": "gaming monitor qhd",
            },
        },
        {
            "provider_key": "awin",
            "provider_product_id": "SKU-2",
            "title": "Portable Monitor 15.6 inch",
            "brand": "AOSIMAN",
            "category_text": "Monitors",
            "product_url": "https://merchant.example/products/sku-2",
            "image_url": "https://cdn.example/img-2.jpg",
            "price_text": "129.99",
            "availability_text": "in stock",
            "currency": "USD",
            "raw": {
                "product_name": "Portable Monitor 15.6 inch",
                "category_name": "Monitors",
                "merchant_category": "Portable Monitors",
                "keywords": "portable monitor",
            },
        },
        {
            "provider_key": "awin",
            "provider_product_id": "SKU-3",
            "title": "Android TV Box 4GB RAM",
            "brand": "G96",
            "category_text": "TV Boxes",
            "product_url": "https://merchant.example/products/sku-3",
            "image_url": "https://cdn.example/img-3.jpg",
            "price_text": "59.99",
            "availability_text": "in stock",
            "currency": "USD",
            "raw": {
                "product_name": "Android TV Box 4GB RAM",
                "category_name": "TV Boxes",
                "merchant_category": "Streaming Devices",
                "keywords": "tv box android",
            },
        },
        {
            "provider_key": "awin",
            "provider_product_id": "SKU-4",
            "title": "Wireless Bluetooth Speaker",
            "brand": "Tronsmart",
            "category_text": "Speakers",
            "product_url": "https://merchant.example/products/sku-4",
            "image_url": "https://cdn.example/img-4.jpg",
            "price_text": "39.99",
            "availability_text": "in stock",
            "currency": "USD",
            "raw": {
                "product_name": "Wireless Bluetooth Speaker",
                "category_name": "Speakers",
                "merchant_category": "Audio",
                "keywords": "speaker bluetooth",
            },
        },
        {
            "provider_key": "awin",
            "provider_product_id": "SKU-5",
            "title": "Curved Gaming Monitor 27 inch QHD",
            "brand": "KTC",
            "category_text": "Monitors",
            "product_url": "https://merchant.example/products/sku-5-dup",
            "image_url": "https://cdn.example/img-5.jpg",
            "price_text": "199.99",
            "availability_text": "in stock",
            "currency": "USD",
            "raw": {
                "product_name": "Curved Gaming Monitor 27 inch QHD",
                "category_name": "Monitors",
                "merchant_category": "Computer Monitors",
                "keywords": "gaming monitor qhd",
            },
        },
    ]
    return tuple(ProviderProduct(**row) for row in rows)


class ProviderSearchSelectionUnitTests(unittest.TestCase):
    def test_selects_exactly_four_when_enough_relevant_products_exist(self) -> None:
        products = _sample_products() + tuple(
            ProviderProduct(
                provider_key="awin",
                provider_product_id=f"SKU-EXTRA-{index}",
                title=f"Gaming Monitor Extra {index}",
                brand="Brand",
                category_text="Monitors",
                product_url=f"https://merchant.example/products/extra-{index}",
                image_url=f"https://cdn.example/img-extra-{index}.jpg",
                price_text="149.99",
                availability_text="in stock",
                currency="USD",
                raw={"keywords": "gaming monitor"},
            )
            for index in range(3)
        )
        result = select_provider_products_for_query("gaming monitor", products)
        self.assertEqual(result.status, "selected")
        self.assertGreaterEqual(result.matched_count, 4)
        self.assertEqual(len(result.selected_products), 4)
        self.assertEqual(
            len({product.provider_product_id for product in result.selected_products}),
            4,
        )

    def test_dedupes_near_identical_titles(self) -> None:
        result = select_provider_products_for_query("gaming monitor", _sample_products())
        self.assertEqual(result.status, "insufficient_relevant_products")
        self.assertEqual(result.matched_count, 1)

    def test_returns_insufficient_when_fewer_than_four_matches(self) -> None:
        result = select_provider_products_for_query("tv box", _sample_products())
        self.assertEqual(result.status, "insufficient_relevant_products")
        self.assertEqual(result.matched_count, 1)
        self.assertEqual(result.selected_products, tuple())

    def test_empty_query_is_safe_no_selection(self) -> None:
        result = select_provider_products_for_query("", _sample_products())
        self.assertEqual(result.status, "no_query_tokens")
        self.assertEqual(result.selected_products, tuple())
        self.assertIn("empty_query", result.reason_codes)

    def test_masked_urls_hide_query_parameters(self) -> None:
        masked = mask_provider_product_url(
            "https://merchant.example/products/sku-1?affid=123&clickref=abc"
        )
        self.assertEqual(masked, "https://merchant.example/products/sku-1")
        self.assertNotIn("?", masked)
        self.assertNotIn("&", masked)


class ProviderRealFeedSearchActivationStage8CTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_feed_file = os.environ.get(_REAL_FEED_ENV)
        feed_path = _real_feed_path()
        if feed_path.is_file():
            os.environ[_REAL_FEED_ENV] = str(feed_path)

    def tearDown(self) -> None:
        if self._saved_feed_file is None:
            os.environ.pop(_REAL_FEED_ENV, None)
        else:
            os.environ[_REAL_FEED_ENV] = self._saved_feed_file

    def test_real_feed_loads_eligible_products_when_present(self) -> None:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")

        products = load_eligible_provider_feed_products(
            ProviderFeedConfig(provider_key="awin", feed_file=str(feed_path))
        )
        self.assertGreaterEqual(len(products), 4)

    def test_real_feed_generic_queries(self) -> None:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")

        config = ProviderFeedConfig(provider_key="awin", feed_file=str(feed_path))
        report_rows: list[dict[str, object]] = []
        selected_query_count = 0

        for query in _REAL_FEED_QUERIES:
            with self.subTest(query=query):
                selection = resolve_search_provider_feed_product_selection(
                    query=query,
                    feed_config=config,
                )
                row = {
                    "query": query,
                    "matched_count": selection.matched_count,
                    "selected_count": len(selection.selected_products),
                    "status": selection.status,
                    "products": selection.to_dict()["selected_products"],
                }
                report_rows.append(row)
                if selection.status == "selected":
                    selected_query_count += 1
                    self.assertEqual(len(selection.selected_products), 4)
                    for product in selection.selected_products:
                        self.assertTrue(product.title)
                        self.assertTrue(product.price_text)
                        self.assertTrue(product.availability_text)
                        self.assertTrue(product.product_url)

        self.assertGreaterEqual(selected_query_count, 3, report_rows)

        power_adapter = next(row for row in report_rows if row["query"] == "power adapter")
        self.assertEqual(power_adapter["status"], "insufficient_relevant_products")
        self.assertEqual(power_adapter["selected_count"], 0)

        self._report_rows = report_rows

    def test_resolver_exposes_backend_selection_without_allowing_cards(self) -> None:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")

        os.environ[_REAL_FEED_ENV] = str(feed_path)
        resolution = resolve_live_search("gaming monitor")

        self.assertEqual(resolution.provider_feed_status, "provider_feed_ready")
        self.assertEqual(resolution.provider_feed_selection_status, "selected")
        self.assertEqual(resolution.provider_feed_selected_count, 4)
        self.assertEqual(len(resolution.provider_feed_selected_products), 4)
        self.assertFalse(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
        self.assertNotEqual(resolution.provider_key, "manual_amazon_affiliate")

        for product in resolution.provider_feed_selected_products:
            self.assertIn("title", product)
            self.assertIn("price_text", product)
            self.assertIn("availability_text", product)
            self.assertIn("product_url_masked", product)
            self.assertNotIn("?", product["product_url_masked"])

    def test_resolver_insufficient_selection_is_safe_no_cards(self) -> None:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")

        os.environ[_REAL_FEED_ENV] = str(feed_path)
        resolution = resolve_live_search("air fryer")

        self.assertEqual(resolution.provider_feed_status, "provider_feed_ready")
        self.assertEqual(
            resolution.provider_feed_selection_status,
            "insufficient_relevant_products",
        )
        self.assertEqual(resolution.provider_feed_matched_count, 3)
        self.assertEqual(resolution.provider_feed_selected_count, 0)
        self.assertEqual(resolution.provider_feed_selected_products, tuple())
        self.assertFalse(resolution.result_allowed)

    def test_manual_amazon_power_banks_regression(self) -> None:
        resolution = resolve_live_search("power bank")
        self.assertEqual(resolution.provider_key, "manual_amazon_affiliate")
        self.assertTrue(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "connected_provider_results")
        self.assertIsNone(resolution.provider_feed_status)
        self.assertIsNone(resolution.provider_feed_selection_status)

    def test_mocked_feed_ready_metadata_still_does_not_allow_cards(self) -> None:
        ready_metadata = SearchProviderFeedMetadata(
            provider_feed_status="provider_feed_ready",
            provider_feed_reason_codes=("feed_loaded",),
            provider_feed_eligible_count=100,
        )
        with patch(
            "picwise_search.live_search_resolver.resolve_search_provider_feed_metadata",
            return_value=ready_metadata,
        ):
            resolution = resolve_live_search("running shoes")

        self.assertFalse(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")

    def test_broad_negatives_and_suggestions_skip_feed_selection(self) -> None:
        for query in ("bank", "insurance", "bots"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertIsNone(resolution.provider_feed_selection_status)

        resolution = resolve_live_search("charger")
        self.assertEqual(resolution.resolver_state, "broad_query_suggestions")
        self.assertIsNone(resolution.provider_feed_selection_status)


if __name__ == "__main__":
    unittest.main()
