"""A Google-format feed (Awin's "Enhanced" feeds) read like an Awin-format one.

Owner, 2026-10-20: PicWise turns to Google-format feeds. The first real files (owner,
2026-10-21 and 2026-10-22) carry the category only in `google_product_category` and the
currency only inside the price ("39.99 GBP"), so the reader took neither and held every
row back. Owner, 2026-10-22: read both, and hide a price of 0 (one shop lists 159
products in stock at £0.00, "(100% off)"). Pinned here: the row read, the gates, the
per-shop intake, a search page and the redirect target, and that an Awin-format row
reads as before.

Every row is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
import gzip
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.normalization import normalize_feed_row_to_provider_product  # noqa: E402
from picwise_providers.offer_health import (  # noqa: E402
    build_feed_availability_context,
    evaluate_product_eligibility,
)
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    measure_configured_feed_intake,
    resolve_card_eligible_provider_feed_product_by_id,
)
from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402
from picwise_surface import provider_feed_cards_will_render  # noqa: E402

# The columns of Awin's Google-format download, in its order.
_GOOGLE_COLUMNS = (
    "advertiser_id", "advertiser_name", "id", "title", "description", "link", "image_link",
    "additional_image_link", "mobile_link", "virtual_model_link", "aw_deep_link",
    "aw_mobile_link", "google_product_category", "product_type", "gtin", "mpn", "brand",
    "identifier_exists", "availability", "availability_date", "expiration_date", "price",
    "sale_price", "sale_price_effective_date", "unit_pricing_measure",
    "unit_pricing_base_measure", "installment", "subscription_cost", "loyalty_program",
    "condition", "adult", "multipack", "is_bundle", "energy_efficiency_class",
    "min_energy_efficiency_class", "max_energy_efficiency_class", "age_group", "color",
    "gender", "material", "pattern", "size", "size_type", "size_system", "item_group_id",
    "product_weight", "product_height", "product_width", "product_length", "product_detail",
    "product_highlight", "certification", "lifestyle_image_link", "shipping",
    "shipping_weight", "shipping_height", "shipping_width", "shipping_length",
    "min_handling_time", "max_handling_time", "ships_from_country", "tax",
)
_KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"


def _google_row(pid: str, shop_id: str, shop: str, *, price: str, stock: str = "in_stock",
                category: str = _KETTLES) -> dict[str, str]:
    own = f"https://shop{shop_id}.example.invalid/products/{pid}"
    return {
        "advertiser_id": shop_id,
        "advertiser_name": shop,
        "id": pid,
        "title": f"Fixturon 1.7L Electric Kettle {pid}",
        "description": "A fictional cordless electric kettle for local tests.",
        "link": own,
        "image_link": f"https://cdn.example.invalid/{pid}.jpg",
        "aw_deep_link": f"https://track.example.invalid/cread.php?awinmid={shop_id}&ued={own}",
        "google_product_category": category,
        "brand": "Fixturon",
        "availability": stock,
        "price": price,
        "condition": "new",
    }


def _awin_row(**overrides: str) -> dict[str, str]:
    row = {
        "aw_product_id": "w1",
        "product_name": "Fixturon Kettle",
        "category_name": "Kettles",
        "aw_deep_link": "https://track.example.invalid/w1",
        "search_price": "20.00",
        "currency": "GBP",
        "merchant_name": "Fixture Awin Shop",
    }
    row.update(overrides)
    return row


class GoogleFormatRowTests(unittest.TestCase):
    def test_category_and_currency_are_read(self) -> None:
        product = normalize_feed_row_to_provider_product(
            _google_row("g1", "101", "Fixture Shop One", price="24.99 GBP"), provider_key="awin"
        )
        self.assertEqual(product.category_text, _KETTLES)
        self.assertEqual((product.price_text, product.currency), ("24.99", "GBP"))
        # The tracked link is the product's link; the shop's own stays in the row.
        self.assertTrue(product.product_url.startswith("https://track.example.invalid/"))
        self.assertEqual(product.raw["link"], "https://shop101.example.invalid/products/g1")

    def test_a_code_before_the_amount_is_read_too(self) -> None:
        product = normalize_feed_row_to_provider_product(
            _google_row("g1", "101", "Fixture Shop One", price="GBP 1,299.00"), provider_key="awin"
        )
        self.assertEqual((product.price_text, product.currency), ("1,299.00", "GBP"))

    def test_a_price_without_a_code_stays_as_written(self) -> None:
        for price in ("24.99", "£24.99", "24.99GBP", "24.99 gbp", "24.99 GBP extra"):
            with self.subTest(price=price):
                product = normalize_feed_row_to_provider_product(
                    _google_row("g1", "101", "Fixture Shop One", price=price), provider_key="awin"
                )
                self.assertEqual((product.price_text, product.currency), (price, ""))

    def test_an_awin_format_row_reads_as_before(self) -> None:
        product = normalize_feed_row_to_provider_product(_awin_row(), provider_key="awin")
        self.assertEqual(
            (product.category_text, product.price_text, product.currency), ("Kettles", "20.00", "GBP")
        )
        # A currency column wins: the price is not split even when it carries a code.
        product = normalize_feed_row_to_provider_product(
            _awin_row(search_price="20.00 EUR"), provider_key="awin"
        )
        self.assertEqual((product.price_text, product.currency), ("20.00 EUR", "GBP"))
        # The Awin category comes before the Google one.
        product = normalize_feed_row_to_provider_product(
            _awin_row(google_product_category=_KETTLES), provider_key="awin"
        )
        self.assertEqual(product.category_text, "Kettles")


class ZeroPriceTests(unittest.TestCase):
    def _product(self, price: str) -> ProviderProduct:
        return ProviderProduct(
            provider_key="awin",
            provider_product_id="z1",
            title="Fixturon Electric Kettle",
            brand="Fixturon",
            category_text="Kettles",
            product_url="https://shop.example.invalid/z1",
            image_url="https://cdn.example.invalid/z1.jpg",
            price_text=price,
            availability_text="in_stock",
            currency="GBP",
            raw={"availability": "in_stock", "price": price},
        )

    def _eligibility(self, price: str):
        product = self._product(price)
        return evaluate_product_eligibility(
            product, feed_ctx=build_feed_availability_context([product, self._product("9.99")])
        )

    def test_a_price_of_zero_or_below_is_never_shown(self) -> None:
        for price in ("0.00", "0", "£0.00", "-5.00"):
            with self.subTest(price=price):
                result = self._eligibility(price)
                self.assertFalse(result.card_eligible)
                self.assertIn("price_zero_or_negative", result.reason_codes)
                self.assertNotIn("missing_or_unparseable_price", result.reason_codes)

    def test_a_low_real_price_is_shown(self) -> None:
        self.assertTrue(self._eligibility("0.01").card_eligible)

    def test_an_unreadable_price_keeps_its_own_reason(self) -> None:
        result = self._eligibility("call for price")
        self.assertIn("missing_or_unparseable_price", result.reason_codes)
        self.assertNotIn("price_zero_or_negative", result.reason_codes)


class GoogleFormatFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = Path(tempfile.mkdtemp())
        self.feed = folder / "google.csv.gz"
        rows = [
            _google_row("g1", "101", "Fixture Shop One", price="24.99 GBP"),
            _google_row("g2", "101", "Fixture Shop One", price="9.99 GBP", stock="out_of_stock"),
            _google_row("g3", "101", "Fixture Shop One", price="14.99 GBP", category=""),
            _google_row("g4", "101", "Fixture Shop One", price="0.00 GBP"),
            _google_row("g5", "202", "Fixture Shop Two", price="19.99 GBP"),
        ]
        # Awin's file starts with a byte order mark.
        with gzip.open(self.feed, "wt", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=_GOOGLE_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        saved = {name: os.environ.get(name) for name in ("AWIN_FEED_FILE", "AWIN_FEED_URL",
                                                         "PICWISE_PREPARED_CATALOGUE_FILE")}
        os.environ["AWIN_FEED_FILE"] = str(self.feed)
        os.environ.pop("AWIN_FEED_URL", None)
        os.environ.pop("PICWISE_PREPARED_CATALOGUE_FILE", None)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def test_each_shop_says_what_it_brings_and_why_the_rest_is_held(self) -> None:
        intake = measure_configured_feed_intake()
        self.assertEqual(
            {key: intake[key] for key in ("rows", "shown", "not_new", "held")},
            {"rows": 5, "shown": 2, "not_new": 0, "held": 3},
        )
        self.assertEqual(
            intake["held_reasons"],
            {
                "availability_out_of_stock": 1,
                "purchasability_out_of_stock": 1,
                "missing_category_text": 1,
                "price_zero_or_negative": 1,
            },
        )
        self.assertEqual({shop["shop"]: shop["shown"] for shop in intake["shops"]},
                         {"Fixture Shop One": 1, "Fixture Shop Two": 1})

    def test_a_search_shows_the_kettles_in_stock_cheapest_first(self) -> None:
        resolution = resolve_live_search("kettle")
        self.assertTrue(provider_feed_cards_will_render(resolution))
        cards = [
            (card.get("provider_product_id"), card.get("price_text"))
            for card in resolution.provider_feed_selected_products
        ]
        self.assertEqual(cards, [("g5", "19.99"), ("g1", "24.99")])

    def test_a_click_goes_to_the_tracked_link(self) -> None:
        product = resolve_card_eligible_provider_feed_product_by_id("g1")
        self.assertIsNotNone(product)
        self.assertEqual(product.product_url,
                         "https://track.example.invalid/cread.php?awinmid=101"
                         "&ued=https://shop101.example.invalid/products/g1")
        self.assertIsNone(resolve_card_eligible_provider_feed_product_by_id("g4"))


if __name__ == "__main__":
    unittest.main()
