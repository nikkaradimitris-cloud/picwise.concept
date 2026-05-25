from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import SearchProviderFeedMetadata  # noqa: E402
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402


class ProviderResolverWiringStage8BTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_env = {
            "AWIN_FEED_FILE": os.environ.pop("AWIN_FEED_FILE", None),
            "AWIN_FEED_URL": os.environ.pop("AWIN_FEED_URL", None),
        }

    def tearDown(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_recognized_category_without_feed_is_safe_no_card(self) -> None:
        for query in ("running shoes", "ebike"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
                self.assertEqual(resolution.provider_feed_status, "provider_feed_not_configured")
                self.assertFalse(resolution.result_allowed)
                self.assertIn("provider_feed_status_provider_feed_not_configured", resolution.reason_codes)

    def test_feed_ready_metadata_does_not_allow_cards(self) -> None:
        ready_metadata = SearchProviderFeedMetadata(
            provider_feed_status="provider_feed_ready",
            provider_feed_reason_codes=("feed_loaded",),
            provider_feed_eligible_count=3,
        )
        with patch(
            "picwise_search.live_search_resolver.resolve_search_provider_feed_metadata",
            return_value=ready_metadata,
        ):
            resolution = resolve_live_search("running shoes")

        self.assertEqual(resolution.provider_feed_status, "provider_feed_ready")
        self.assertEqual(resolution.provider_feed_eligible_count, 3)
        self.assertFalse(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
        self.assertNotEqual(resolution.resolver_state, "connected_provider_results")

    def test_feed_parse_failed_is_safe_no_card(self) -> None:
        invalid_path = Path(tempfile.gettempdir()) / "picwise_stage8b_invalid_feed.json"
        invalid_path.write_text("{not valid json", encoding="utf-8")
        os.environ["AWIN_FEED_FILE"] = str(invalid_path)

        try:
            resolution = resolve_live_search("running shoes")
            self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
            self.assertEqual(resolution.provider_feed_status, "provider_feed_parse_failed")
            self.assertFalse(resolution.result_allowed)
            self.assertIn("provider_feed_status_provider_feed_parse_failed", resolution.reason_codes)
        finally:
            invalid_path.unlink(missing_ok=True)

    def test_feed_empty_is_safe_no_card(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump([], handle)
            feed_path = handle.name

        os.environ["AWIN_FEED_FILE"] = feed_path
        try:
            resolution = resolve_live_search("ebike")
            self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
            self.assertEqual(resolution.provider_feed_status, "provider_feed_empty")
            self.assertFalse(resolution.result_allowed)
        finally:
            os.unlink(feed_path)

    def test_feed_no_eligible_products_is_safe_no_card(self) -> None:
        csv_text = (
            "product_id,product_name,brand,category_name,deeplink,image_url,current_price,in_stock,currency\n"
            "SKU-BLOCKED,,AcmeBrand,Power Banks,"
            "https://merchant.example/products/sku-blocked,https://cdn.example/img.jpg,29.99,in stock,USD\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as handle:
            handle.write(csv_text)
            feed_path = handle.name

        os.environ["AWIN_FEED_FILE"] = feed_path
        try:
            resolution = resolve_live_search("running shoes")
            self.assertEqual(resolution.resolver_state, "understood_provider_not_connected")
            self.assertEqual(resolution.provider_feed_status, "provider_feed_no_eligible_products")
            self.assertFalse(resolution.result_allowed)
        finally:
            os.unlink(feed_path)

    def test_manual_amazon_power_banks_regression(self) -> None:
        resolution = resolve_live_search("power bank")
        self.assertEqual(resolution.provider_key, "manual_amazon_affiliate")
        self.assertEqual(resolution.provider_status, "connected")
        self.assertTrue(resolution.result_allowed)
        self.assertEqual(resolution.resolver_state, "connected_provider_results")
        self.assertIsNone(resolution.provider_feed_status)

    def test_broad_negatives_remain_safe_not_understood(self) -> None:
        for query in ("bank", "insurance", "bots"):
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertEqual(resolution.resolver_state, "not_understood")
                self.assertFalse(resolution.result_allowed)
                self.assertIsNone(resolution.provider_feed_status)

    def test_broad_query_suggestions_skip_provider_feed_lookup(self) -> None:
        resolution = resolve_live_search("charger")
        self.assertEqual(resolution.resolver_state, "broad_query_suggestions")
        self.assertFalse(resolution.result_allowed)
        self.assertIsNone(resolution.provider_feed_status)
        self.assertGreaterEqual(len(resolution.suggestions), 2)


if __name__ == "__main__":
    unittest.main()
