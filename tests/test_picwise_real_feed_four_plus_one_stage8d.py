from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderFeedConfig, ProviderProduct  # noqa: E402
from picwise_providers.search_selection import (  # noqa: E402
    decide_recommended_provider_product,
    mask_provider_product_url,
    provider_product_to_backend_dict,
    select_provider_products_for_query,
)
from picwise_providers.state import (  # noqa: E402
    resolve_search_provider_feed_product_selection,
    resolve_search_provider_feed_selection_with_recommendation,
)
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402

_REAL_FEED_ENV = "AWIN_FEED_FILE"
_REAL_FEED_DEFAULT = Path(r"C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz")

_STAGE8D_QUERIES = (
    "monitor",
    "gaming monitor",
    "portable monitor",
    "tv box",
    "speaker",
    "projector",
    "tablet",
    "vacuum cleaner",
    "printer",
    "laptop",
    "smartphone",
)


def _real_feed_path() -> Path:
    return Path(os.environ.get(_REAL_FEED_ENV, str(_REAL_FEED_DEFAULT)))


def _feed_config() -> ProviderFeedConfig:
    return ProviderFeedConfig(provider_key="awin", feed_file=str(_real_feed_path()))


def _sample_four_monitor_products() -> tuple[ProviderProduct, ...]:
    rows = []
    for index in range(4):
        rows.append(
            ProviderProduct(
                provider_key="awin",
                provider_product_id=f"MON-{index + 1}",
                title=f"Gaming Monitor {index + 1} inch QHD",
                brand="Brand",
                category_text="Monitors",
                product_url=f"https://merchant.example/products/mon-{index + 1}",
                image_url=f"https://cdn.example/img-{index + 1}.jpg",
                price_text=f"{149.99 + index}",
                availability_text="in stock",
                currency="USD",
                raw={
                    "category_name": "Monitors",
                    "merchant_category": "Computer Monitors",
                    "keywords": "gaming monitor qhd",
                },
            )
        )
    return tuple(rows)


class ProviderFeedRecommendationUnitTests(unittest.TestCase):
    def test_recommends_one_of_four_selected_products(self) -> None:
        products = _sample_four_monitor_products()
        selection = select_provider_products_for_query("gaming monitor", products)
        decision = decide_recommended_provider_product("gaming monitor", selection.selected_products)

        self.assertEqual(selection.status, "selected")
        self.assertEqual(len(selection.selected_products), 4)
        self.assertEqual(decision.decision_status, "recommended")
        self.assertTrue(decision.recommended_product_id)
        self.assertGreater(len(decision.recommendation_reason_codes), 0)
        selected_ids = {product.provider_product_id for product in selection.selected_products}
        self.assertIn(decision.recommended_product_id, selected_ids)

    def test_insufficient_selected_products_has_no_recommendation(self) -> None:
        decision = decide_recommended_provider_product("gaming monitor", tuple())
        self.assertEqual(decision.decision_status, "no_selection")
        self.assertIsNone(decision.recommended_product_id)
        self.assertIn("no_feed_selection", decision.recommendation_reason_codes)

        partial = _sample_four_monitor_products()[:2]
        decision = decide_recommended_provider_product("gaming monitor", partial)
        self.assertEqual(decision.decision_status, "insufficient_selected_products")
        self.assertIsNone(decision.recommended_product_id)
        self.assertIn("insufficient_selected_products", decision.recommendation_reason_codes)

    def test_recommendation_is_deterministic(self) -> None:
        products = _sample_four_monitor_products()
        selection = select_provider_products_for_query("gaming monitor", products)
        first = decide_recommended_provider_product("gaming monitor", selection.selected_products)
        second = decide_recommended_provider_product("gaming monitor", selection.selected_products)
        self.assertEqual(first, second)


class ProviderRealFeedFourPlusOneStage8DTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_feed_file = os.environ.get(_REAL_FEED_ENV)
        feed_path = _real_feed_path()
        if feed_path.is_file():
            os.environ[_REAL_FEED_ENV] = str(feed_path)
        self.report_rows: list[dict[str, object]] = []

    def tearDown(self) -> None:
        if self._saved_feed_file is None:
            os.environ.pop(_REAL_FEED_ENV, None)
        else:
            os.environ[_REAL_FEED_ENV] = self._saved_feed_file

    def _require_real_feed(self) -> ProviderFeedConfig:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")
        return _feed_config()

    def test_real_feed_four_plus_one_queries(self) -> None:
        config = self._require_real_feed()
        successful_queries = 0

        for query in _STAGE8D_QUERIES:
            with self.subTest(query=query):
                selection, decision = resolve_search_provider_feed_selection_with_recommendation(
                    query=query,
                    feed_config=config,
                )
                row: dict[str, object] = {
                    "query": query,
                    "selection_status": selection.status,
                    "selected_count": len(selection.selected_products),
                    "decision_status": decision.decision_status,
                    "recommended_product_id": decision.recommended_product_id,
                    "recommendation_reason_codes": list(decision.recommendation_reason_codes),
                    "selected_products": [
                        provider_product_to_backend_dict(product)
                        for product in selection.selected_products
                    ],
                }
                self.report_rows.append(row)

                if selection.status != "selected":
                    self.assertEqual(decision.decision_status, "insufficient_selected_products")
                    self.assertIsNone(decision.recommended_product_id)
                    continue

                successful_queries += 1
                self.assertEqual(len(selection.selected_products), 4)
                self.assertEqual(decision.decision_status, "recommended")
                self.assertTrue(decision.recommended_product_id)
                self.assertGreater(len(decision.recommendation_reason_codes), 0)

                selected_ids = {
                    product.provider_product_id for product in selection.selected_products
                }
                self.assertIn(decision.recommended_product_id, selected_ids)

                for product in selection.selected_products:
                    self.assertTrue(product.title)
                    self.assertTrue(product.price_text)
                    self.assertTrue(product.availability_text)
                    self.assertTrue(product.product_url)
                    self.assertNotIn("rating", product.raw)
                    self.assertNotIn("review_count", product.raw)

                for product_dict in row["selected_products"]:
                    masked = str(product_dict["product_url_masked"])
                    self.assertNotIn("?", masked)
                    self.assertNotIn("&", masked)
                    self.assertEqual(
                        masked,
                        mask_provider_product_url(
                            next(
                                p.product_url
                                for p in selection.selected_products
                                if p.provider_product_id == product_dict["provider_product_id"]
                            )
                        ),
                    )

        self.assertGreaterEqual(successful_queries, 3, self.report_rows)

    def test_resolver_exposes_recommendation_metadata_without_allowing_cards(self) -> None:
        config = self._require_real_feed()
        os.environ[_REAL_FEED_ENV] = str(config.feed_file or "")

        resolution = resolve_live_search("gaming monitor")
        self.assertEqual(resolution.provider_feed_selection_status, "selected")
        self.assertEqual(resolution.provider_feed_selected_count, 4)
        self.assertEqual(len(resolution.provider_feed_selected_products), 4)
        self.assertEqual(resolution.provider_feed_decision_status, "recommended")
        self.assertTrue(resolution.provider_feed_recommended_product_id)
        self.assertGreater(len(resolution.provider_feed_recommendation_reason_codes), 0)
        self.assertFalse(resolution.result_allowed)

        selected_ids = {
            product["provider_product_id"]
            for product in resolution.provider_feed_selected_products
        }
        self.assertIn(resolution.provider_feed_recommended_product_id, selected_ids)

    def test_insufficient_selection_reports_no_recommendation(self) -> None:
        config = self._require_real_feed()
        os.environ[_REAL_FEED_ENV] = str(config.feed_file or "")

        resolution = resolve_live_search("air fryer")
        self.assertEqual(
            resolution.provider_feed_selection_status,
            "insufficient_relevant_products",
        )
        self.assertEqual(resolution.provider_feed_decision_status, "insufficient_selected_products")
        self.assertIsNone(resolution.provider_feed_recommended_product_id)
        self.assertIn(
            "insufficient_selected_products",
            resolution.provider_feed_recommendation_reason_codes,
        )
        self.assertFalse(resolution.result_allowed)

    def test_no_price_band_filtering_in_recommendation(self) -> None:
        config = self._require_real_feed()
        from picwise_providers.state import load_eligible_provider_feed_products  # noqa: WPS433
        from picwise_providers.search_selection import _score_product_for_tokens, _tokenize_query  # noqa: WPS433

        products = load_eligible_provider_feed_products(feed_config=config)
        tokens = _tokenize_query("monitor")
        outside_band = [
            product
            for product in products
            if _score_product_for_tokens(
                product,
                tokens,
                normalized_query="monitor",
                query_seeks_accessory=False,
            )
            is not None
            and float(str(product.price_text or "0").replace(",", "")) not in range(80, 251)
        ]
        self.assertGreaterEqual(len(outside_band), 4)

        selection = select_provider_products_for_query("monitor", tuple(outside_band))
        decision = decide_recommended_provider_product("monitor", selection.selected_products)
        self.assertEqual(selection.status, "selected")
        self.assertEqual(decision.decision_status, "recommended")
        self.assertNotIn("price_band_filter", decision.recommendation_reason_codes)


class ProviderRealFeedFourPlusOneSafetyStage8DTests(unittest.TestCase):
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

    def test_manual_amazon_power_banks_regression(self) -> None:
        resolution = resolve_live_search("power bank")
        self.assertEqual(resolution.provider_key, "manual_amazon_affiliate")
        self.assertTrue(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "connected_provider_results")
        self.assertIsNone(resolution.provider_feed_status)
        self.assertIsNone(resolution.provider_feed_selection_status)
        self.assertIsNone(resolution.provider_feed_decision_status)
        self.assertIsNone(resolution.provider_feed_recommended_product_id)

    def test_unsafe_queries_remain_without_feed_decision(self) -> None:
        for query in ("bank", "insurance", "bots"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertIsNone(resolution.provider_feed_selection_status)
                self.assertIsNone(resolution.provider_feed_decision_status)

    def test_highly_ambiguous_broad_query_skips_feed_decision(self) -> None:
        resolution = resolve_live_search("charger")
        self.assertEqual(resolution.resolver_state, "broad_query_suggestions")
        self.assertIsNone(resolution.provider_feed_selection_status)
        self.assertIsNone(resolution.provider_feed_decision_status)


if __name__ == "__main__":
    unittest.main()
