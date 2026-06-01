"""Stage 8C-0: runtime truth alignment guard — backend dict and UI must not overclaim."""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.search_selection import provider_product_to_backend_dict  # noqa: E402
from picwise_search.live_search_resolver import LiveSearchResolution  # noqa: E402
from picwise_surface.reference import (  # noqa: E402
    _build_provider_feed_result_cards,
    _provider_feed_ui_display_allowed,
    render_picwise_reference_surface,
)

_BTO_FEED_DEFAULT = Path(
    r"C:\Users\User\Desktop\picwise-private-feeds\back_to_office_clean_full_columns.csv.gz"
)

_UI_BLOCKING_PURCHASABILITY = (
    "out_of_stock",
    "discontinued",
    "missing_buy_button",
    "invalid_page",
    "redirect_suspect",
)


def _sample_product(**overrides: object) -> ProviderProduct:
    raw: dict[str, object] = {
        "product_type": "Laptops",
        "description": (
            "A full description with enough detail to pass the minimal quality threshold "
            "for card eligibility evaluation in stage eight c zero tests."
        ),
        "in_stock": "in stock",
    }
    base: dict[str, object] = {
        "provider_key": "awin",
        "provider_product_id": "SKU-TRUTH-1",
        "title": "Dell Latitude Laptop 15 inch",
        "brand": "Dell",
        "category_text": "Laptops",
        "product_url": "https://merchant.example/products/sku-truth-1",
        "image_url": "https://cdn.example/img.jpg",
        "price_text": "899.99",
        "availability_text": "1",
        "currency": "USD",
    }
    raw_override = overrides.pop("raw", None)
    if isinstance(raw_override, dict):
        raw.update(raw_override)
    base.update(overrides)
    base["raw"] = raw
    return ProviderProduct(**base)  # type: ignore[arg-type]


def _complete_feed_product_dict(**overrides: object) -> dict[str, object]:
    product = provider_product_to_backend_dict(_sample_product(**overrides))
    product.setdefault("provider_key", "awin")
    product.setdefault("provider_product_id", "SKU-TRUTH-1")
    product.setdefault("title", "Dell Latitude Laptop 15 inch")
    product.setdefault("price_text", "899.99")
    product.setdefault("availability_text", "1")
    product.setdefault("image_url", "https://cdn.example/img.jpg")
    product.setdefault("product_url", "https://merchant.example/products/sku-truth-1")
    return product


def _resolution_from_products(
    products: list[dict[str, object]],
    *,
    recommended_id: str | None = None,
    recommendation_confidence: str = "limited",
) -> LiveSearchResolution:
    normalized: list[dict[str, object]] = []
    for index, row in enumerate(products):
        clone = dict(row)
        clone["provider_product_id"] = str(
            clone.get("provider_product_id") or f"SKU-TRUTH-{index + 1}"
        )
        normalized.append(clone)
    while len(normalized) < 4:
        clone = dict(normalized[0])
        clone["provider_product_id"] = f"{clone.get('provider_product_id')}-dup{len(normalized)}"
        normalized.append(clone)
    products = normalized
    rec_id = recommended_id or str(products[0].get("provider_product_id") or "")
    return LiveSearchResolution(
        raw_query="laptop",
        display_query="laptop",
        normalized_query="laptop",
        canonical_query="laptop",
        canonical_category="laptop",
        mega_category_id="laptop",
        display_name="Laptop",
        lower_level_provider_category=None,
        intent="laptop",
        query_type="product",
        confidence=0.9,
        status="connected",
        needs_review=False,
        provider_key="awin",
        provider_status="connected",
        result_allowed=False,
        resolver_state="understood_provider_not_connected",
        reason_codes=(),
        provider_feed_selection_status="selected",
        provider_feed_decision_status="recommended",
        provider_feed_recommended_product_id=rec_id,
        provider_feed_recommendation_reason_codes=("strong_query_title_fit",),
        provider_feed_recommendation_confidence=recommendation_confidence,
        provider_feed_selected_products=tuple(products[:4]),
        provider_feed_selected_count=4,
    )


class RuntimeTruthAlignmentBackendTests(unittest.TestCase):
    def test_backend_dict_exports_truth_fields(self) -> None:
        payload = provider_product_to_backend_dict(_sample_product())
        for field in (
            "brand",
            "currency",
            "product_type",
            "category_evidence",
            "card_eligible",
            "availability_state",
            "purchasability_state",
            "recommendation_confidence",
            "recommendation_confidence_ceiling",
            "verified_purchasable",
        ):
            self.assertIn(field, payload, f"missing truth field: {field}")
        self.assertEqual(payload["brand"], "Dell")
        self.assertEqual(payload["currency"], "USD")
        self.assertEqual(payload["product_type"], "Laptops")

    def test_purchasability_unknown_is_not_verified_purchasable(self) -> None:
        payload = provider_product_to_backend_dict(_sample_product())
        self.assertEqual(payload["purchasability_state"], "purchasability_unknown")
        self.assertFalse(payload["verified_purchasable"])

    def test_verified_purchasable_requires_verifier_evidence(self) -> None:
        payload = provider_product_to_backend_dict(
            _sample_product(
                raw={
                    "purchasability_state": "purchasable",
                    "buy_button_seen": True,
                    "verification_confidence": "verified",
                    "verification_source": "page_verification",
                }
            )
        )
        self.assertEqual(payload["purchasability_state"], "purchasable")
        self.assertTrue(payload["verified_purchasable"])


class RuntimeTruthAlignmentUiTests(unittest.TestCase):
    def test_weak_availability_not_shown_as_trusted_stock(self) -> None:
        product = _complete_feed_product_dict()
        product["availability_state"] = "weak"
        product["purchasability_state"] = "purchasability_unknown"
        resolution = _resolution_from_products(
            [{**product, "provider_product_id": f"SKU-A{i}"} for i in range(4)]
        )
        _cards, live, _disc, _note = _build_provider_feed_result_cards(resolution=resolution)
        self.assertTrue(live)
        html = render_picwise_reference_surface(query="laptop", resolution=resolution)
        self.assertIn("Availability not verified", html)
        self.assertNotIn("in stock", html.lower())
        self.assertNotRegex(html, r"Availability:\s*1\b")

    def test_raw_availability_one_not_rendered(self) -> None:
        product = _complete_feed_product_dict(availability_text="1")
        resolution = _resolution_from_products(
            [{**product, "provider_product_id": f"SKU-B{i}"} for i in range(4)]
        )
        html = render_picwise_reference_surface(query="laptop", resolution=resolution)
        self.assertNotRegex(html, r"Availability:\s*1\b")
        meta_lines = re.findall(r'<p class="pw-meta">([^<]+)</p>', html)
        for line in meta_lines:
            self.assertNotIn("Availability: 1", line)

    def test_limited_recommendation_confidence_wording(self) -> None:
        product = _complete_feed_product_dict()
        resolution = _resolution_from_products(
            [{**product, "provider_product_id": f"SKU-C{i}"} for i in range(4)],
            recommendation_confidence="limited",
        )
        html = render_picwise_reference_surface(query="laptop", resolution=resolution)
        self.assertIn("Suggested pick from these 4 (limited confidence).", html)
        self.assertIn("Suggested by PicWise", html)
        self.assertNotIn("&#9733; Recommended by PicWise", html)

    def test_blocking_purchasability_states_hide_feed_cards(self) -> None:
        for state in _UI_BLOCKING_PURCHASABILITY:
            with self.subTest(state=state):
                product = _complete_feed_product_dict()
                product["purchasability_state"] = state
                product["card_eligible"] = False
                resolution = _resolution_from_products(
                    [{**product, "provider_product_id": f"SKU-D-{state}-{i}"} for i in range(4)]
                )
                self.assertFalse(_provider_feed_ui_display_allowed(resolution))
                _cards, live, _, _ = _build_provider_feed_result_cards(resolution=resolution)
                self.assertFalse(live)
                html = render_picwise_reference_surface(query="laptop", resolution=resolution)
                self.assertEqual(html.count('<article class="pw-card'), 0)


class RuntimeTruthAlignmentFeedIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not os.environ.get("AWIN_FEED_FILE") and _BTO_FEED_DEFAULT.is_file():
            os.environ["AWIN_FEED_FILE"] = str(_BTO_FEED_DEFAULT)

    def test_bto_laptop_selection_exports_truth_without_overclaim(self) -> None:
        if not _BTO_FEED_DEFAULT.is_file():
            self.skipTest("BTO feed required")
        from picwise_providers.state import (  # noqa: WPS433
            resolve_search_provider_feed_product_selection,
        )

        selection = resolve_search_provider_feed_product_selection(query="laptop")
        if selection.status != "selected":
            self.skipTest("laptop selection unavailable")
        for product in selection.selected_products:
            payload = provider_product_to_backend_dict(product)
            self.assertFalse(payload["verified_purchasable"])
            self.assertEqual(payload["purchasability_state"], "purchasability_unknown")


if __name__ == "__main__":
    unittest.main()
