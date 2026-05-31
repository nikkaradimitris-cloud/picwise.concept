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
from picwise_providers.offer_health import (  # noqa: E402
    build_feed_availability_context,
    evaluate_product_eligibility,
    evaluate_recommendation_confidence,
)
from picwise_providers.search_selection import (  # noqa: E402
    decide_recommended_provider_product,
    select_provider_products_for_query,
)
from picwise_providers.state import resolve_search_provider_feed_product_selection  # noqa: E402

_BTO_FEED_ENV = "AWIN_FEED_FILE"
_BTO_FEED_DEFAULT = Path(
    r"C:\Users\User\Desktop\picwise-private-feeds\back_to_office_clean_full_columns.csv.gz"
)

_BLOCKED_LAPTOP_TYPES = (
    "Laptop Stands",
    "Straps",
    "Laptop Cases",
    "Power Adapters & Inverters",
    "Mobile Device Chargers",
)
_BLOCKED_MOUSE_TYPES = ("Mouse Pads", "Wrist Rests")
_BLOCKED_HEADPHONE_TYPES = ("Mobile Device Chargers",)
_BLOCKED_MONITOR_TYPES = ("Display Privacy Filters",)
_BLOCKED_CHAIR_TYPES = (
    "Chair Back Supports",
    "Video Game Chairs",
    "Seat Cushions",
    "Backrests",
)


def _bto_feed_path() -> Path:
    return Path(os.environ.get(_BTO_FEED_ENV, str(_BTO_FEED_DEFAULT)))


def _bto_feed_config() -> ProviderFeedConfig:
    return ProviderFeedConfig(provider_key="awin", feed_file=str(_bto_feed_path()))


def _sample_product(**overrides: object) -> ProviderProduct:
    description = (
        "A full description with enough detail to pass the minimal quality threshold "
        "for card eligibility evaluation in stage eight b foundation tests."
    )
    raw: dict[str, object] = {
        "product_type": "Laptops",
        "description": description,
        "in_stock": "in stock",
    }
    base: dict[str, object] = {
        "provider_key": "awin",
        "provider_product_id": "SKU-ELIG-1",
        "title": "Dell Latitude Laptop 15 inch",
        "brand": "Dell",
        "category_text": "Laptops",
        "product_url": "https://merchant.example/products/sku-elig-1",
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


class ProviderOfferHealthFoundationTests(unittest.TestCase):
    def _feed_ctx(self, *products: ProviderProduct):
        return build_feed_availability_context(products)

    def test_product_type_match_alone_is_not_enough_for_card_eligibility(self) -> None:
        product = _sample_product(
            price_text="",
            image_url="",
            product_url="",
            raw={"product_type": "Laptops", "description": ""},
        )
        ctx = self._feed_ctx(product)
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("missing_or_unparseable_price", result.reason_codes)
        self.assertIn("missing_image_url", result.reason_codes)
        self.assertIn("missing_product_url", result.reason_codes)

    def test_missing_price_rejects_card_eligibility(self) -> None:
        product = _sample_product(price_text="not-a-price")
        ctx = self._feed_ctx(product)
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("missing_or_unparseable_price", result.reason_codes)

    def test_missing_image_rejects_card_eligibility(self) -> None:
        product = _sample_product(image_url="")
        ctx = self._feed_ctx(product)
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("missing_image_url", result.reason_codes)

    def test_missing_product_url_rejects_card_eligibility(self) -> None:
        product = _sample_product(product_url="")
        ctx = self._feed_ctx(product)
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("missing_product_url", result.reason_codes)

    def test_constant_in_stock_across_feed_becomes_weak_availability(self) -> None:
        products = (
            _sample_product(provider_product_id="A", raw={"in_stock": "in stock"}),
            _sample_product(provider_product_id="B", raw={"in_stock": "in stock"}),
            _sample_product(provider_product_id="C", raw={"in_stock": "in stock"}),
        )
        ctx = build_feed_availability_context(products)
        self.assertFalse(ctx.has_meaningful_variation)
        result = evaluate_product_eligibility(products[0], feed_ctx=ctx)
        assert result.offer_health is not None
        self.assertEqual(result.offer_health.availability_state, "weak")
        self.assertEqual(result.offer_health.feed_availability_signal, "constant_feed_availability")

    def test_explicit_out_of_stock_rejects_card_eligibility(self) -> None:
        varied = (
            _sample_product(provider_product_id="A", raw={"in_stock": "in stock"}),
            _sample_product(
                provider_product_id="B",
                availability_text="out of stock",
                raw={"in_stock": "out of stock"},
            ),
        )
        ctx = build_feed_availability_context(varied)
        result = evaluate_product_eligibility(varied[1], feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("availability_out_of_stock", result.reason_codes)

    def test_missing_reviews_ratings_does_not_create_fake_recommendation_evidence(self) -> None:
        products = tuple(
            _sample_product(
                provider_product_id=f"P-{index}",
                title=f"Dell Latitude Laptop Model {index}",
            )
            for index in range(4)
        )
        decision = decide_recommended_provider_product("dell laptop", products)
        self.assertEqual(decision.decision_status, "recommended")
        joined = " ".join(decision.recommendation_reason_codes).lower()
        self.assertNotIn("review", joined)
        self.assertNotIn("rating", joined)
        self.assertNotIn("star", joined)
        self.assertNotIn("popularity", joined)

    def test_purchasability_unknown_limits_recommendation_confidence(self) -> None:
        product = _sample_product()
        ctx = self._feed_ctx(product)
        eligibility = evaluate_product_eligibility(product, feed_ctx=ctx)
        assert eligibility.offer_health is not None
        self.assertEqual(
            eligibility.offer_health.purchasability.purchasability_state,
            "purchasability_unknown",
        )
        confidence = evaluate_recommendation_confidence(
            card_eligible=True,
            offer_health=eligibility.offer_health,
            has_strong_feed_evidence=True,
        )
        self.assertIn(confidence, {"limited", "weak"})
        self.assertNotEqual(confidence, "strong")

        products = tuple(
            _sample_product(
                provider_product_id=f"UNK-{index}",
                title=f"Dell Latitude Laptop Variant {index}",
            )
            for index in range(4)
        )
        decision = decide_recommended_provider_product("dell laptop", products)
        self.assertNotEqual(decision.recommendation_confidence, "strong")

    def test_explicit_missing_buy_button_rejects_card_eligibility(self) -> None:
        product = _sample_product(
            raw={
                "product_type": "Laptops",
                "description": _sample_product().raw["description"],
                "buy_button_seen": False,
                "purchasability_state": "missing_buy_button",
            }
        )
        ctx = self._feed_ctx(product)
        result = evaluate_product_eligibility(product, feed_ctx=ctx)
        self.assertFalse(result.card_eligible)
        self.assertIn("purchasability_missing_buy_button", result.reason_codes)


class BackToOfficeSelectionRegressionStage8BTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_feed_file = os.environ.get(_BTO_FEED_ENV)
        feed_path = _bto_feed_path()
        if feed_path.is_file():
            os.environ[_BTO_FEED_ENV] = str(feed_path)

    def tearDown(self) -> None:
        if self._saved_feed_file is None:
            os.environ.pop(_BTO_FEED_ENV, None)
        else:
            os.environ[_BTO_FEED_ENV] = self._saved_feed_file

    def _require_bto_feed(self) -> ProviderFeedConfig:
        feed_path = _bto_feed_path()
        if not feed_path.is_file():
            self.skipTest(f"Back to the Office feed not present at {feed_path}")
        return _bto_feed_config()

    def _product_types(self, products: tuple) -> tuple[str, ...]:
        types: list[str] = []
        for product in products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            types.append(str(raw.get("product_type") or "").strip())
        return tuple(types)

    def _assert_selected_types(
        self,
        query: str,
        *,
        allowed_types: tuple[str, ...],
        blocked_types: tuple[str, ...] = (),
        min_count: int = 4,
    ) -> None:
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query=query,
            feed_config=config,
        )
        self.assertEqual(selection.status, "selected")
        self.assertGreaterEqual(len(selection.selected_products), min_count)
        for product_type in self._product_types(selection.selected_products):
            self.assertIn(product_type, allowed_types)
            self.assertNotIn(product_type, blocked_types)

    def test_laptop_prefers_actual_laptops(self) -> None:
        self._assert_selected_types(
            "laptop",
            allowed_types=("Laptops",),
            blocked_types=_BLOCKED_LAPTOP_TYPES,
        )

    def test_dell_laptop_prefers_dell_laptops(self) -> None:
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query="dell laptop",
            feed_config=config,
        )
        self.assertEqual(selection.status, "selected")
        self.assertEqual(len(selection.selected_products), 4)
        for product in selection.selected_products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            self.assertEqual(raw.get("product_type"), "Laptops")
            brand_blob = f"{product.brand} {product.title}".lower()
            self.assertIn("dell", brand_blob)

    def test_monitor_queries_prefer_computer_monitors(self) -> None:
        for query in ("monitor", "27 inch monitor", "computer monitor"):
            with self.subTest(query=query):
                self._assert_selected_types(
                    query,
                    allowed_types=("Computer Monitors", "Not Categorized"),
                    blocked_types=_BLOCKED_MONITOR_TYPES,
                )

    def test_mouse_prefers_mice_not_pads(self) -> None:
        self._assert_selected_types(
            "mouse",
            allowed_types=("Mice",),
            blocked_types=_BLOCKED_MOUSE_TYPES,
        )

    def test_headphones_prefers_headsets_not_chargers(self) -> None:
        self._assert_selected_types(
            "headphones",
            allowed_types=("Headphones & Headsets",),
            blocked_types=_BLOCKED_HEADPHONE_TYPES,
        )

    def test_printer_query(self) -> None:
        self._assert_selected_types(
            "printer",
            allowed_types=(
                "Multifunction Printers",
                "Laser Printers",
                "Inkjet Printers",
                "Label Printers",
                "Large Format Printers",
                "Photo Printers",
                "Dot Matrix Printers",
                "Plastic Card Printers",
                "3D Printers",
            ),
        )

    def test_toner_and_ink_cartridge_queries(self) -> None:
        self._assert_selected_types(
            "toner cartridge",
            allowed_types=("Toner Cartridges",),
        )
        self._assert_selected_types(
            "ink cartridge",
            allowed_types=("Ink Cartridges",),
        )

    def test_logitech_webcam(self) -> None:
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query="logitech webcam",
            feed_config=config,
        )
        self.assertEqual(selection.status, "selected")
        for product in selection.selected_products:
            raw = product.raw if isinstance(product.raw, dict) else {}
            self.assertEqual(raw.get("product_type"), "Webcams")
            brand_blob = f"{product.brand} {product.title}".lower()
            self.assertIn("logitech", brand_blob)

    def test_office_chair_safe_no_pass(self) -> None:
        config = self._require_bto_feed()
        selection = resolve_search_provider_feed_product_selection(
            query="office chair",
            feed_config=config,
        )
        self.assertEqual(selection.status, "insufficient_relevant_products")
        self.assertEqual(len(selection.selected_products), 0)
        self.assertLess(selection.matched_count, 4)

    def test_card_ineligible_products_are_skipped_during_selection(self) -> None:
        products = tuple(
            _sample_product(
                provider_product_id=f"STRONG-{index}",
                title=f"Dell Latitude Laptop Model {index}",
            )
            for index in range(3)
        ) + (
            _sample_product(
                provider_product_id="WEAK-1",
                title="Dell Latitude Laptop Lite",
                price_text="",
            ),
        )
        selection = select_provider_products_for_query(
            "dell laptop",
            products,
            max_products=4,
        )
        self.assertEqual(selection.status, "insufficient_relevant_products")
        self.assertEqual(len(selection.selected_products), 0)


if __name__ == "__main__":
    unittest.main()
