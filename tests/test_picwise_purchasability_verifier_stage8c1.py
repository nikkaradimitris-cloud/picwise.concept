"""Stage 8C-1: background purchasability page verifier foundation (mocked/static HTML)."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import (  # noqa: E402
    build_feed_availability_context,
    evaluate_product_eligibility,
    offer_health_blocks_card_eligibility,
)
from picwise_providers.purchasability_verifier import (  # noqa: E402
    analyze_product_page_content,
    merge_verification_into_product_raw,
    verify_product_page_purchasability,
)
from picwise_providers.search_selection import provider_product_to_backend_dict  # noqa: E402

_PRODUCT_URL = "https://merchant.example/products/sku-8c1-1"


def _sample_product(**overrides: object) -> ProviderProduct:
    raw: dict[str, object] = {
        "product_type": "Laptops",
        "description": (
            "A full description with enough detail to pass the minimal quality threshold "
            "for stage eight c one purchasability verifier tests."
        ),
        "in_stock": "in stock",
    }
    base: dict[str, object] = {
        "provider_key": "awin",
        "provider_product_id": "SKU-8C1-1",
        "title": "Dell Latitude Laptop 15 inch",
        "brand": "Dell",
        "category_text": "Laptops",
        "product_url": _PRODUCT_URL,
        "image_url": "https://cdn.example/img.jpg",
        "price_text": "899.99",
        "availability_text": "in stock",
        "currency": "USD",
    }
    raw_override = overrides.pop("raw", None)
    if isinstance(raw_override, dict):
        raw.update(raw_override)
    base.update(overrides)
    base["raw"] = raw
    return ProviderProduct(**base)  # type: ignore[arg-type]


def _analyze_html(html: str, *, final_url: str = _PRODUCT_URL, http_status: int = 200) -> object:
    return analyze_product_page_content(
        url=_PRODUCT_URL,
        html=html,
        http_status=http_status,
        final_url=final_url,
    )


def _product_with_verification(verification: object) -> ProviderProduct:
    raw = merge_verification_into_product_raw({}, verification)
    return _sample_product(raw=raw)


class PurchasabilityVerifierSignalTests(unittest.TestCase):
    def test_add_to_cart_page_confirms_purchasable(self) -> None:
        verification = _analyze_html(
            "<html><body><button>Add to Cart</button><p>Dell laptop</p></body></html>"
        )
        self.assertTrue(verification.buy_button_seen)
        self.assertEqual(verification.purchasability_state, "purchasable")
        self.assertIn(verification.verification_confidence, {"verified", "high", "strong"})

    def test_out_of_stock_page_blocks(self) -> None:
        verification = _analyze_html(
            "<html><body><h1>Widget</h1><p>This item is out of stock</p></body></html>"
        )
        self.assertTrue(verification.out_of_stock_seen)
        self.assertEqual(verification.purchasability_state, "out_of_stock")
        product = _product_with_verification(verification)
        ctx = build_feed_availability_context((product,))
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("purchasability_out_of_stock", result.reason_codes)

    def test_temporarily_unavailable_maps_to_out_of_stock(self) -> None:
        verification = _analyze_html(
            "<html><body><p>Temporarily unavailable</p></body></html>"
        )
        self.assertTrue(verification.out_of_stock_seen)
        self.assertEqual(verification.purchasability_state, "out_of_stock")

    def test_discontinued_page_blocks(self) -> None:
        verification = _analyze_html(
            "<html><body><p>Product discontinued</p></body></html>"
        )
        self.assertEqual(verification.purchasability_state, "discontinued")
        product = _product_with_verification(verification)
        ctx = build_feed_availability_context((product,))
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("purchasability_discontinued", result.reason_codes)

    def test_missing_buy_button_not_verified(self) -> None:
        verification = _analyze_html(
            "<html><body><h1>Specs</h1><p>Detailed specifications only.</p></body></html>"
        )
        self.assertFalse(verification.buy_button_seen)
        self.assertEqual(verification.purchasability_state, "missing_buy_button")
        payload = provider_product_to_backend_dict(_product_with_verification(verification))
        self.assertFalse(payload["verified_purchasable"])

    def test_invalid_http_status_is_invalid_page(self) -> None:
        verification = _analyze_html("<html><body>error</body></html>", http_status=404)
        self.assertEqual(verification.purchasability_state, "invalid_page")
        product = _product_with_verification(verification)
        ctx = build_feed_availability_context((product,))
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("purchasability_invalid_page", result.reason_codes)

    def test_redirect_to_search_page_is_redirect_suspect(self) -> None:
        verification = _analyze_html(
            "<html><body><a href='/search'>Search</a></body></html>",
            final_url="https://merchant.example/search?q=laptop",
        )
        self.assertEqual(verification.purchasability_state, "redirect_suspect")
        product = _product_with_verification(verification)
        ctx = build_feed_availability_context((product,))
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("purchasability_redirect_suspect", result.reason_codes)

    def test_ambiguous_page_stays_unknown_and_not_verified(self) -> None:
        verification = _analyze_html(
            "<html><body><p>Check availability for this model.</p></body></html>"
        )
        self.assertEqual(verification.purchasability_state, "purchasability_unknown")
        payload = provider_product_to_backend_dict(_product_with_verification(verification))
        self.assertFalse(payload["verified_purchasable"])

    def test_verified_purchasable_requires_positive_verifier_evidence(self) -> None:
        verification = _analyze_html(
            "<html><body><button>Buy Now</button></body></html>"
        )
        payload = provider_product_to_backend_dict(_product_with_verification(verification))
        self.assertEqual(verification.verification_source, "page_verifier")
        self.assertTrue(payload["verified_purchasable"])


class PurchasabilityVerifierOfferHealthIntegrationTests(unittest.TestCase):
    def test_offer_health_blocks_for_negative_verifier_states(self) -> None:
        from picwise_providers.offer_health import evaluate_offer_health

        cases = (
            ("out_of_stock", "<p>Sold out</p>"),
            ("discontinued", "<p>No longer available</p>"),
            ("missing_buy_button", "<p>Specifications only</p>"),
        )
        for expected_state, html in cases:
            with self.subTest(state=expected_state):
                verification = _analyze_html(html)
                self.assertEqual(verification.purchasability_state, expected_state)
                product = _product_with_verification(verification)
                ctx = build_feed_availability_context((product,))
                offer_health = evaluate_offer_health(product, feed_ctx=ctx)
                blocked = offer_health_blocks_card_eligibility(offer_health)
                self.assertTrue(blocked)

    def test_no_fake_review_rating_stock_fields_in_backend_dict(self) -> None:
        verification = _analyze_html("<html><body><button>Add to Cart</button></body></html>")
        payload = provider_product_to_backend_dict(_product_with_verification(verification))
        forbidden = (
            "review_count",
            "rating",
            "star_rating",
            "popularity",
            "delivery_estimate",
            "cart_status",
            "store_trust",
            "revenue",
        )
        for field in forbidden:
            self.assertNotIn(field, payload)


class PurchasabilityVerifierHttpMockTests(unittest.TestCase):
    def test_verify_product_page_uses_mocked_http_response(self) -> None:
        html = b"<html><body><button>Add to basket</button></body></html>"

        class _FakeResponse:
            def __init__(self) -> None:
                self._buffer = io.BytesIO(html)

            def read(self, size: int = -1) -> bytes:
                return self._buffer.read(size)

            def getcode(self) -> int:
                return 200

            def geturl(self) -> str:
                return _PRODUCT_URL

            def __enter__(self) -> "_FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        def _fake_open(request, timeout=0):  # noqa: ARG001
            return _FakeResponse()

        verification = verify_product_page_purchasability(
            _PRODUCT_URL,
            opener=_fake_open,
        )
        self.assertTrue(verification.buy_button_seen)
        self.assertEqual(verification.purchasability_state, "purchasable")

    def test_http_error_maps_to_invalid_page(self) -> None:
        def _raising_open(request, timeout=0):  # noqa: ARG001
            raise HTTPError(
                _PRODUCT_URL,
                503,
                "Service Unavailable",
                hdrs=None,
                fp=None,
            )

        verification = verify_product_page_purchasability(
            _PRODUCT_URL,
            opener=_raising_open,
        )
        self.assertEqual(verification.purchasability_state, "invalid_page")
        self.assertEqual(verification.http_status, 503)


if __name__ == "__main__":
    unittest.main()
