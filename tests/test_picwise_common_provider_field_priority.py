from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.normalization import normalize_feed_row_to_provider_product  # noqa: E402
from picwise_providers.search_selection import (  # noqa: E402
    _product_search_fields,
    _resolve_allowed_product_types,
    _score_product_for_tokens,
    select_provider_products_for_query,
)
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402


def _sample_product(**overrides) -> ProviderProduct:
    base = {
        "provider_key": "awin",
        "provider_product_id": "P-1",
        "title": "Sample Product",
        "brand": "",
        "category_text": "Computers",
        "product_url": "https://merchant.example/products/p-1",
        "image_url": "https://cdn.example/p-1.jpg",
        "price_text": "99.99",
        "availability_text": "in stock",
        "currency": "GBP",
        "raw": {},
    }
    base.update(overrides)
    return ProviderProduct(**base)


class CommonProviderBrandNormalizationTests(unittest.TestCase):
    def test_official_brand_name_maps_to_provider_product_brand(self) -> None:
        product = normalize_feed_row_to_provider_product(
            {
                "product_name": "Dell Latitude Laptop",
                "brand_name": "Dell",
                "category_name": "Computers",
                "aw_deep_link": "https://merchant.example/products/dell-1",
            },
            provider_key="awin",
        )
        assert product is not None
        self.assertEqual(product.brand, "Dell")

    def test_existing_brand_field_takes_precedence_over_brand_name(self) -> None:
        product = normalize_feed_row_to_provider_product(
            {
                "product_name": "Wireless Mouse",
                "brand": "Logitech",
                "brand_name": "Other Brand",
                "category_name": "Mice",
                "aw_deep_link": "https://merchant.example/products/mouse-1",
            },
            provider_key="awin",
        )
        assert product is not None
        self.assertEqual(product.brand, "Logitech")

    def test_missing_brand_name_remains_unknown(self) -> None:
        product = normalize_feed_row_to_provider_product(
            {
                "product_name": "HP EliteBook Laptop",
                "category_name": "Computers",
                "aw_deep_link": "https://merchant.example/products/hp-1",
            },
            provider_key="awin",
        )
        assert product is not None
        self.assertEqual(product.brand, "")

    def test_brand_is_not_inferred_from_title(self) -> None:
        product = normalize_feed_row_to_provider_product(
            {
                "product_name": "Logitech MX Master Mouse",
                "category_name": "Mice",
                "aw_deep_link": "https://merchant.example/products/mx-1",
            },
            provider_key="awin",
        )
        assert product is not None
        self.assertEqual(product.brand, "")
        self.assertIn("Logitech", product.title)


class CommonProviderFieldPrioritySearchTests(unittest.TestCase):
    def test_product_type_is_included_in_search_fields(self) -> None:
        product = _sample_product(
            title="Business Laptop 14 inch",
            raw={"product_type": "Laptops", "category_name": "Computers"},
        )
        fields = _product_search_fields(product)
        self.assertIn("laptops", fields["product_type"])

    def test_flat_category_name_has_reduced_influence(self) -> None:
        products = []
        for index in range(4):
            products.append(
                _sample_product(
                    provider_product_id=f"L-{index}",
                    title=f"Business Laptop {index} 14 inch",
                    raw={"product_type": "Laptops", "category_name": "Computers"},
                )
            )
        products.append(
            _sample_product(
                provider_product_id="S-1",
                title="Business Laptop Stand Adjustable",
                raw={"product_type": "Laptop Stands", "category_name": "Computers"},
            )
        )
        selection = select_provider_products_for_query("laptop", tuple(products))
        self.assertEqual(selection.status, "selected")
        for product in selection.selected_products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            self.assertEqual(raw.get("product_type"), "Laptops")

    def test_product_type_alignment_excludes_conflicting_accessory_types(self) -> None:
        products = []
        for index in range(4):
            products.append(
                _sample_product(
                    provider_product_id=f"M-{index}",
                    title=f"Office mouse wireless {index}",
                    brand="Acme",
                    raw={"product_type": "Mice", "brand_name": "Acme"},
                )
            )
        products.append(
            _sample_product(
                provider_product_id="P-2",
                title="Office mouse pad large",
                raw={"product_type": "Mouse Pads"},
            )
        )
        selection = select_provider_products_for_query("mouse", tuple(products))
        self.assertEqual(selection.status, "selected")
        for product in selection.selected_products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            self.assertEqual(raw.get("product_type"), "Mice")

    def test_description_is_unstructured_search_evidence_only(self) -> None:
        product = _sample_product(
            title="Universal Dock Pro",
            raw={
                "description": "Supports charging and monitor output for workstations",
            },
        )
        ranking = _score_product_for_tokens(
            product,
            ("charging", "monitor"),
            normalized_query="charging monitor",
            query_seeks_accessory=False,
        )
        self.assertIsNotNone(ranking)

    def test_feeds_without_product_type_fall_back_to_title_and_category(self) -> None:
        products = []
        for index in range(4):
            products.append(
                _sample_product(
                    provider_product_id=f"MON-{index}",
                    title=f"Gaming Monitor {index} 27 inch QHD",
                    category_text="Monitors",
                    raw={"category_name": "Monitors", "merchant_category": "Display Monitors"},
                )
            )
        selection = select_provider_products_for_query("gaming monitor", tuple(products))
        self.assertEqual(selection.status, "selected")

    def test_no_fake_reviews_or_ratings_in_selection_payload(self) -> None:
        product = _sample_product(
            title="Headphones Wireless",
            raw={"product_type": "Headphones & Headsets"},
        )
        selection = select_provider_products_for_query("headphones", tuple(product for _ in range(4)))
        payload = selection.to_dict()
        for row in payload["selected_products"]:
            self.assertNotIn("rating", row)
            self.assertNotIn("review_count", row)
            self.assertNotIn("stars", row)

    def test_manual_amazon_power_banks_regression_unchanged(self) -> None:
        resolution = resolve_live_search("power bank")
        self.assertEqual(resolution.provider_key, "manual_amazon_affiliate")
        self.assertTrue(resolution.result_allowed)
        self.assertIsNone(resolution.provider_feed_selection_status)


class CommonProviderIntentResolutionTests(unittest.TestCase):
    def test_monitor_intent_resolves_to_computer_monitors(self) -> None:
        allowed = _resolve_allowed_product_types("computer monitor", ("computer", "monitor"))
        self.assertIn("computer monitors", allowed)

    def test_office_chair_intent_is_strict(self) -> None:
        allowed = _resolve_allowed_product_types("office chair", ("office", "chair"))
        self.assertEqual(allowed, ("office & computer chairs",))


if __name__ == "__main__":
    unittest.main()
