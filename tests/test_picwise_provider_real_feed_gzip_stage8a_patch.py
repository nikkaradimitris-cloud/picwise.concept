from __future__ import annotations

import gzip
import os
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.awin_adapter import load_awin_provider_feed  # noqa: E402
from picwise_providers.contracts import ProviderFeedConfig  # noqa: E402
from picwise_providers.eligibility import evaluate_provider_product_eligibility  # noqa: E402
from picwise_providers.state import resolve_provider_feed_pipeline  # noqa: E402

_REAL_FEED_ENV = "AWIN_FEED_FILE"
_REAL_FEED_DEFAULT = Path(r"C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz")


def _mask_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return "<invalid-url>"
    path = parsed.path or "/"
    if len(path) > 24:
        path = f"{path[:20]}...{path[-1]}"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


class ProviderGzipFeedPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_feed_file = os.environ.pop(_REAL_FEED_ENV, None)

    def tearDown(self) -> None:
        if self._saved_feed_file is None:
            os.environ.pop(_REAL_FEED_ENV, None)
        else:
            os.environ[_REAL_FEED_ENV] = self._saved_feed_file

    def test_no_feed_still_returns_not_configured(self) -> None:
        config = ProviderFeedConfig(provider_key="awin")
        pipeline = resolve_provider_feed_pipeline(config)
        self.assertEqual(pipeline.feed_status.status, "provider_feed_not_configured")
        self.assertEqual(pipeline.parse_result.status, "provider_feed_not_configured")
        self.assertIn("no_feed_file_or_url", pipeline.feed_status.reason_codes)

    def test_invalid_csv_inside_gzip_returns_parse_failed(self) -> None:
        with tempfile.NamedTemporaryFile("wb", suffix=".csv.gz", delete=False) as handle:
            handle.write(gzip.compress(b"{not valid json"))
            feed_path = handle.name

        try:
            config = ProviderFeedConfig(provider_key="awin", feed_file=feed_path)
            result = load_awin_provider_feed(config)
            self.assertEqual(result.status, "provider_feed_parse_failed")
            self.assertIn("json_decode_failed", result.parse_errors)
        finally:
            os.unlink(feed_path)

    def test_real_geekbuying_gzip_feed_parses_when_present(self) -> None:
        feed_path = Path(os.environ.get(_REAL_FEED_ENV, str(_REAL_FEED_DEFAULT)))
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")

        config = ProviderFeedConfig(provider_key="awin", feed_file=str(feed_path))
        pipeline = resolve_provider_feed_pipeline(config)

        self.assertEqual(pipeline.parse_result.status, "provider_feed_loaded")
        self.assertGreater(len(pipeline.parse_result.products), 0)
        self.assertNotIn(
            pipeline.feed_status.status,
            {"provider_feed_not_configured", "provider_feed_parse_failed"},
        )

        eligibility = tuple(
            evaluate_provider_product_eligibility(product)
            for product in pipeline.parse_result.products
        )
        eligible = sum(1 for row in eligibility if row.status == "eligible")
        review = sum(1 for row in eligibility if row.status == "needs_review")
        blocked = sum(1 for row in eligibility if row.status == "blocked")

        self.assertEqual(pipeline.feed_status.eligible_count, eligible)
        self.assertEqual(pipeline.feed_status.review_count, review)
        self.assertEqual(pipeline.feed_status.blocked_count, blocked)

        categories = Counter(
            product.category_text for product in pipeline.parse_result.products if product.category_text
        )
        self.assertTrue(categories)

        sample = pipeline.parse_result.products[0]
        self.assertEqual(sample.brand, sample.brand.strip())
        self.assertNotEqual(sample.title, "")

        masked_samples = [
            {
                "provider_product_id": product.provider_product_id,
                "title": product.title[:80],
                "brand": product.brand,
                "category_text": product.category_text,
                "product_url": _mask_url(product.product_url),
                "image_url": _mask_url(product.image_url),
            }
            for product in pipeline.parse_result.products[:5]
        ]
        self.assertEqual(len(masked_samples), min(5, len(pipeline.parse_result.products)))
        for row in masked_samples:
            self.assertNotIn("?", row["product_url"])
            self.assertNotIn("&", row["product_url"])
            self.assertNotIn("?", row["image_url"])
            self.assertNotIn("&", row["image_url"])


if __name__ == "__main__":
    unittest.main()
