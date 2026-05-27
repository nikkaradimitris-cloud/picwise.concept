from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402
from picwise_providers.search_selection import (  # noqa: E402
    select_provider_products_for_query,
)
from picwise_providers.state import (  # noqa: E402
    resolve_search_provider_feed_product_selection,
)
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402

_REAL_FEED_ENV = "AWIN_FEED_FILE"
_REAL_FEED_DEFAULT = Path(r"C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz")

_ACCESSORY_MARKERS = (
    "bag",
    "filter",
    "cloth",
    "mop",
    "replacement",
    "spare",
    "parts",
    "tool kit",
    "nozzle",
    "filament",
    "docking station",
    "lens",
    "accessories set",
    "accessory set",
)


def _real_feed_path() -> Path:
    return Path(os.environ.get(_REAL_FEED_ENV, str(_REAL_FEED_DEFAULT)))


def _feed_config() -> ProviderFeedConfig:
    return ProviderFeedConfig(provider_key="awin", feed_file=str(_real_feed_path()))


def _title_blob(products: tuple) -> str:
    return " | ".join(str(product.title or "").lower() for product in products)


class FeedOpportunityGateStage8CPatchTests(unittest.TestCase):
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

    def _require_real_feed(self) -> ProviderFeedConfig:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")
        return ProviderFeedConfig(provider_key="awin", feed_file=str(feed_path))

    def test_feed_opportunity_gate_queries_can_reach_selection(self) -> None:
        config = self._require_real_feed()
        for query in ("tv box", "projector", "portable monitor"):
            with self.subTest(query=query):
                selection = resolve_search_provider_feed_product_selection(
                    query=query,
                    feed_config=config,
                )
                resolution = resolve_live_search(query)
                self.assertEqual(selection.status, "selected")
                self.assertGreaterEqual(selection.strong_matched_count, 4)
                self.assertEqual(resolution.provider_feed_selection_status, "selected")
                self.assertEqual(resolution.provider_feed_selected_count, 4)
                self.assertEqual(len(resolution.provider_feed_selected_products), 4)
                self.assertFalse(resolution.result_allowed)
                self.assertIn(
                    "provider_feed_opportunity_gate",
                    resolution.reason_codes,
                )

    def test_tablet_feed_opportunity_is_reported_honestly(self) -> None:
        config = self._require_real_feed()
        selection = resolve_search_provider_feed_product_selection(
            query="tablet",
            feed_config=config,
        )
        resolution = resolve_live_search("tablet")
        self.assertIn(
            resolution.provider_feed_selection_status,
            {"selected", "insufficient_relevant_products"},
        )
        if selection.status == "selected" and selection.strong_matched_count >= 4:
            self.assertEqual(resolution.provider_feed_selection_status, "selected")
            self.assertEqual(resolution.provider_feed_selected_count, 4)
        else:
            self.assertEqual(
                resolution.provider_feed_selection_status,
                "insufficient_relevant_products",
            )
            self.assertEqual(resolution.provider_feed_selected_count, 0)


class FeedSelectionQualityStage8CPatchTests(unittest.TestCase):
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

    def _require_real_feed(self) -> ProviderFeedConfig:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")
        return _feed_config()

    def test_main_product_queries_prefer_main_products_over_accessories(self) -> None:
        config = self._require_real_feed()
        cases = (
            ("vacuum cleaner", ("vacuum cleaner",), _ACCESSORY_MARKERS[:6]),
            ("printer", ("printer", "3d printer"), ("tool kit", "nozzle", "filament")),
            ("laptop", ("laptop",), ("docking station",)),
            ("smartphone", ("smartphone",), ("lens", "macro lens")),
        )
        for query, required_terms, blocked_terms in cases:
            with self.subTest(query=query):
                selection = resolve_search_provider_feed_product_selection(
                    query=query,
                    feed_config=config,
                )
                self.assertEqual(selection.status, "selected")
                titles = _title_blob(selection.selected_products)
                self.assertTrue(any(term in titles for term in required_terms))
                for blocked in blocked_terms:
                    self.assertNotIn(blocked, titles)

    def test_accessory_focused_queries_remain_valid(self) -> None:
        config = self._require_real_feed()
        for query, marker in (("vacuum filter", "filter"), ("printer filament", "filament")):
            with self.subTest(query=query):
                selection = resolve_search_provider_feed_product_selection(
                    query=query,
                    feed_config=config,
                )
                self.assertEqual(selection.status, "selected")
                self.assertIn(marker, _title_blob(selection.selected_products))


class FeedSelectionSafetyStage8CPatchTests(unittest.TestCase):
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

    def test_unsafe_queries_remain_without_feed_selection(self) -> None:
        for query in ("bank", "insurance", "bots"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertIsNone(resolution.provider_feed_selection_status)
                self.assertFalse(resolution.result_allowed)

    def test_highly_ambiguous_broad_query_skips_feed_selection(self) -> None:
        resolution = resolve_live_search("charger")
        self.assertEqual(resolution.resolver_state, "broad_query_suggestions")
        self.assertIsNone(resolution.provider_feed_selection_status)
        self.assertIsNone(resolution.provider_feed_status)

    def test_no_price_band_filtering_in_selection(self) -> None:
        config = _feed_config()
        if not _real_feed_path().is_file():
            self.skipTest("real feed not present")
        from picwise_providers.state import load_eligible_provider_feed_products  # noqa: WPS433
        from picwise_providers.search_selection import _tokenize_query, _score_product_for_tokens  # noqa: WPS433

        products = load_eligible_provider_feed_products(feed_config=config)
        tokens = _tokenize_query("monitor")
        matched = [
            product
            for product in products
            if _score_product_for_tokens(
                product,
                tokens,
                normalized_query="monitor",
                query_seeks_accessory=False,
            )
            is not None
        ]
        outside_band = []
        for product in matched:
            price_text = str(product.price_text or "").strip().replace(",", "")
            if not price_text:
                continue
            price = float(price_text)
            if price < 80 or price > 250:
                outside_band.append(product)
        self.assertGreaterEqual(len(outside_band), 4, "expected monitor matches outside 80-250")

        off_band_selection = select_provider_products_for_query(
            "monitor",
            tuple(outside_band),
        )
        self.assertEqual(off_band_selection.status, "selected")
        self.assertEqual(len(off_band_selection.selected_products), 4)


if __name__ == "__main__":
    unittest.main()
