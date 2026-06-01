from __future__ import annotations

import io
import os
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402
from picwise_surface.reference import (  # noqa: E402
    _SAFE_DISCLAIMER_BY_STATE,
    _provider_feed_ui_display_allowed,
    render_picwise_reference_surface,
)

_REAL_FEED_ENV = "AWIN_FEED_FILE"
_REAL_FEED_DEFAULT = Path(r"C:\Users\User\Desktop\picwise-private-feeds\geekbuying_feed.csv.gz")

_FEED_CARD_QUERIES = ("monitor", "gaming monitor", "smartphone")
_SAFE_NO_CARD_QUERIES = ("bank", "insurance", "bots")
_FAKE_MARKERS = (
    "pw-rating",
    "pw-reviews",
    "pw-stars",
    "fake discount",
    "fake savings",
    "★",
    "☆",
)


def _real_feed_path() -> Path:
    return Path(os.environ.get(_REAL_FEED_ENV, str(_REAL_FEED_DEFAULT)))


def _call_wsgi(path: str, query_string: str = "") -> tuple[str, dict[str, str], str]:
    status_holder: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        status_holder["headers"] = {key: value for key, value in headers}

    environ: dict[str, object] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "wsgi.url_scheme": "https",
    }
    body_chunks = deployment_app(environ, start_response)
    body = b"".join(body_chunks).decode("utf-8")
    headers = status_holder.get("headers") or {}
    return str(status_holder.get("status") or ""), dict(headers), body


def _card_titles(body: str) -> list[str]:
    return re.findall(r'<h2 class="pw-card-title">([^<]+)</h2>', body)


def _recommended_titles(body: str) -> list[str]:
    recommended_blocks = re.findall(
        r'<article class="pw-card pw-card-recommended"[^>]*>(.*?)</article>',
        body,
        flags=re.DOTALL,
    )
    titles: list[str] = []
    for block in recommended_blocks:
        match = re.search(r'<h2 class="pw-card-title">([^<]+)</h2>', block)
        if match:
            titles.append(match.group(1))
    return titles


def _card_count(body: str) -> int:
    return len(re.findall(r'<article class="pw-card', body))


def _extract_prices(body: str) -> list[str]:
    return re.findall(r'<p class="pw-price">([^<]+)</p>', body)


def _extract_availability_meta_lines(body: str) -> list[str]:
    return re.findall(r'<p class="pw-meta">([^<]+)</p>', body)


def _extract_image_urls(body: str) -> list[str]:
    return re.findall(r'<img class="pw-product-image" src="([^"]+)"', body)


def _extract_product_hrefs(body: str) -> list[str]:
    return re.findall(
        r'<a class="pw-card-cta pw-card-cta-link" href="([^"]+)" rel="nofollow sponsored noopener">View product</a>',
        body,
    )


class ProviderRealFeedUiExposureStage8ETests(unittest.TestCase):
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

    def _require_real_feed(self) -> None:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")

    def _assert_no_fake_commerce_markers(self, body: str) -> None:
        grid_match = re.search(r'<section class="pw-grid"[^>]*>(.*?)</section>', body, flags=re.DOTALL)
        grid_html = grid_match.group(1) if grid_match else body
        lowered = grid_html.lower()
        for marker in _FAKE_MARKERS:
            self.assertNotIn(marker, lowered, msg=f"unexpected fake marker: {marker}")
        self.assertNotRegex(grid_html, r"class=\"pw-(?:rating|reviews|stars)\"")
        self.assertNotRegex(grid_html, r"(?i)\d+\s*(?:reviews?|ratings?)\b")

    def test_feed_queries_render_four_real_cards(self) -> None:
        self._require_real_feed()
        for query in _FEED_CARD_QUERIES:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertTrue(_provider_feed_ui_display_allowed(resolution))
                html = render_picwise_reference_surface(query=query, resolution=resolution)
                self.assertEqual(_card_count(html), 4)
                self.assertIn("Showing 4 selected real products for:", html)
                self.assertIn("Selected real products from a connected provider feed", html)

    def test_exactly_one_recommended_badge(self) -> None:
        self._require_real_feed()
        resolution = resolve_live_search("gaming monitor")
        html = render_picwise_reference_surface(query="gaming monitor", resolution=resolution)
        self.assertEqual(len(_recommended_titles(html)), 1)
        self.assertEqual(html.count('class="pw-rec-note"'), 1)
        self.assertEqual(len(re.findall(r'<div class="pw-rec-badge">', html)), 1)

    def test_recommended_product_is_inside_selected_four(self) -> None:
        self._require_real_feed()
        resolution = resolve_live_search("monitor")
        html = render_picwise_reference_surface(query="monitor", resolution=resolution)
        recommended_titles = _recommended_titles(html)
        self.assertEqual(len(recommended_titles), 1)
        card_titles = _card_titles(html)
        self.assertIn(recommended_titles[0], card_titles)
        self.assertIn(
            resolution.provider_feed_recommended_product_id,
            {
                product["provider_product_id"]
                for product in resolution.provider_feed_selected_products
            },
        )

    def test_real_price_availability_image_and_outbound_link(self) -> None:
        self._require_real_feed()
        resolution = resolve_live_search("smartphone")
        html = render_picwise_reference_surface(query="smartphone", resolution=resolution)
        prices = _extract_prices(html)
        availability = _extract_availability_meta_lines(html)
        images = _extract_image_urls(html)
        hrefs = _extract_product_hrefs(html)
        self.assertEqual(len(prices), 4)
        self.assertEqual(len(availability), 4)
        self.assertEqual(len(images), 4)
        self.assertEqual(len(hrefs), 4)
        for price in prices:
            self.assertTrue(price.strip())
            self.assertNotEqual(price.strip().lower(), "see amazon details")
        for line in availability:
            self.assertTrue(line.strip())
            self.assertNotRegex(line, r"Availability:\s*\d+\b")
            self.assertIn("Availability not verified", line)
        for image in images:
            self.assertTrue(image.lower().startswith("http"))
        for href in hrefs:
            self.assertTrue(href.lower().startswith("http"))
            self.assertNotIn("example.com", href.lower())
            self.assertNotIn("product-3.svg", href.lower())
        self._assert_no_fake_commerce_markers(html)

    def test_power_bank_still_uses_manual_amazon_path(self) -> None:
        resolution = resolve_live_search("power bank")
        html = render_picwise_reference_surface(query="power bank", resolution=resolution)
        self.assertTrue(resolution.result_allowed)
        self.assertIn("View on Amazon", html)
        self.assertIn("/out/amazon?", html)
        self.assertNotIn("View product", html)
        self.assertNotIn("REAL FEED", html)

    def test_unsafe_queries_do_not_render_feed_cards(self) -> None:
        self._require_real_feed()
        for query in _SAFE_NO_CARD_QUERIES:
            with self.subTest(query=query):
                resolution = resolve_live_search(query)
                self.assertFalse(_provider_feed_ui_display_allowed(resolution))
                html = render_picwise_reference_surface(query=query, resolution=resolution)
                self.assertEqual(_card_count(html), 0)
                self.assertIn("pw-empty-state", html)

    def test_no_feed_configured_does_not_render_fake_cards(self) -> None:
        saved = os.environ.pop(_REAL_FEED_ENV, None)
        try:
            resolution = resolve_live_search("monitor")
            self.assertFalse(_provider_feed_ui_display_allowed(resolution))
            html = render_picwise_reference_surface(query="monitor", resolution=resolution)
            self.assertEqual(_card_count(html), 0)
            self.assertIn("pw-empty-state", html)
        finally:
            if saved is not None:
                os.environ[_REAL_FEED_ENV] = saved

    def test_insufficient_selected_products_do_not_render_cards(self) -> None:
        self._require_real_feed()
        resolution = resolve_live_search("air fryer")
        self.assertFalse(_provider_feed_ui_display_allowed(resolution))
        html = render_picwise_reference_surface(query="air fryer", resolution=resolution)
        self.assertEqual(_card_count(html), 0)

    def test_no_price_band_filtering_in_resolver(self) -> None:
        self._require_real_feed()
        resolution = resolve_live_search("monitor")
        joined_reasons = " ".join(resolution.provider_feed_recommendation_reason_codes)
        self.assertNotIn("price_band_filter", joined_reasons)
        self.assertNotIn("80", joined_reasons)
        self.assertNotIn("250", joined_reasons)

    def test_existing_safe_states_remain_unchanged(self) -> None:
        self._require_real_feed()
        blocked = resolve_live_search("bank")
        blocked_html = render_picwise_reference_surface(query="bank", resolution=blocked)
        self.assertEqual(_card_count(blocked_html), 0)
        self.assertIn("pw-empty-state", blocked_html)
        self.assertIn(
            _SAFE_DISCLAIMER_BY_STATE.get(
                blocked.resolver_state,
                "PicWise could not understand this search safely.",
            ),
            blocked_html,
        )

        broad = resolve_live_search("charger")
        broad_html = render_picwise_reference_surface(query="charger", resolution=broad)
        self.assertIn("pw-empty-state", broad_html)

        disconnected = resolve_live_search("laptop")
        disconnected_html = render_picwise_reference_surface(
            query="laptop",
            resolution=disconnected,
        )
        if not _provider_feed_ui_display_allowed(disconnected):
            self.assertIn("pw-empty-state", disconnected_html)


class ProviderRealFeedUiExposureRuntimeStage8ETests(unittest.TestCase):
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

    def _require_real_feed(self) -> None:
        feed_path = _real_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"real feed not present at {feed_path}")

    def test_search_route_runtime_queries(self) -> None:
        self._require_real_feed()
        runtime_cases = (
            ("monitor", True),
            ("gaming monitor", True),
            ("smartphone", True),
            ("power bank", False),
            ("bank", False),
            ("insurance", False),
        )
        for query, expect_feed_cards in runtime_cases:
            with self.subTest(query=query):
                status, _headers, body = _call_wsgi("/search", f"q={quote(query)}")
                self.assertTrue(status.startswith("200"))
                card_count = _card_count(body)
                if expect_feed_cards:
                    self.assertEqual(card_count, 4, body)
                    self.assertEqual(len(_recommended_titles(body)), 1)
                    self.assertIn("Geekbuying via Awin", body)
                elif query == "power bank":
                    self.assertGreater(card_count, 0)
                    self.assertIn("View on Amazon", body)
                else:
                    self.assertEqual(card_count, 0)
                    self.assertIn("pw-empty-state", body)


if __name__ == "__main__":
    unittest.main()
