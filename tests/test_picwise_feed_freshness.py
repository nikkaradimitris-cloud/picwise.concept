"""How fresh a feed's listings are, measured for the deployment's public note.

`src/picwise_providers/feed_freshness.py`. Owner, 2026-10-18: most products the live
site shows are out of stock on the shop's page, old listings at old prices. Before a
rule removes any, the build measures what `last_updated` and `stock_quantity` would
remove. Pinned here: the counts, the ages, what is unreadable, the per-shop table, and
that the note carries them without anything of the feed's link.

Every row is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.feed_freshness import measure_feed_freshness  # noqa: E402

TODAY = date(2026, 10, 18)


def _product(pid: str, shop: str, **raw: str) -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=pid,
        title=f"Fixturon Kettle {pid}",
        brand="Fixturon",
        category_text="Kettles",
        product_url=f"https://fixture.example.invalid/out/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg",
        price_text="20.00",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": shop, "in_stock": "1", **raw},
    )


def _days_ago(days: int) -> str:
    return f"{(TODAY - timedelta(days=days)).isoformat()} 10:23:45"


class FreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            _product("a", "Fixture Store One", last_updated=_days_ago(3), stock_quantity="5",
                     stock_status="In Stock"),
            _product("b", "Fixture Store One", last_updated=_days_ago(40), stock_quantity="0",
                     stock_status="Out of stock"),
            _product("c", "Fixture Store One", last_updated=_days_ago(100), stock_quantity="-1"),
            _product("d", "Fixture Store Two", last_updated=_days_ago(400), stock_quantity="n/a"),
            _product("e", "Fixture Store Two", last_updated="17/05/2024"),
            _product("f", "Fixture Store Two", last_updated=""),
            _product("g", "Fixture Store Two", last_updated=(TODAY + timedelta(days=2)).isoformat()),
        ]
        self.result = measure_feed_freshness(self.products, today=TODAY)

    def test_listing_ages(self) -> None:
        listed = self.result["last_updated"]
        self.assertEqual(self.result["products"], 7)
        self.assertEqual((listed["dated"], listed["no_date"], listed["unreadable"]), (5, 1, 1))
        self.assertEqual(listed["unreadable_examples"], ["17/05/2024"])
        # Ages 3, 40, 100, 400 and 0 (a date after today counts as today).
        self.assertEqual(listed["median_age_days"], 40)
        self.assertEqual(
            listed["older_than_days"], {"7": 3, "30": 3, "90": 2, "180": 1, "365": 1}
        )

    def test_stock_quantities(self) -> None:
        self.assertEqual(
            self.result["stock_quantity"],
            {"filled": 4, "zero_or_less": 2, "positive": 1, "unreadable": 1},
        )

    def test_what_the_stock_columns_say(self) -> None:
        values = self.result["stock_values"]
        self.assertEqual(values["in_stock"], [["1", 7]])
        self.assertEqual(sorted(values["stock_status"]), [["in stock", 1], ["out of stock", 1]])

    def test_per_shop(self) -> None:
        shops = self.result["shops"]
        self.assertEqual([shop["shop"] for shop in shops], ["Fixture Store Two", "Fixture Store One"])
        two, one = shops
        self.assertEqual(
            one,
            {"shop": "Fixture Store One", "products": 3, "dated": 3, "median_age_days": 40,
             "older_than_90_days": 1, "stock_quantity_zero": 2, "stock_status_filled": 2},
        )
        self.assertEqual((two["products"], two["dated"], two["older_than_90_days"]), (4, 2, 1))

    def test_nothing_of_a_link_is_measured(self) -> None:
        text = repr(self.result)
        self.assertNotIn("fixture.example.invalid", text)

    def test_an_empty_feed(self) -> None:
        result = measure_feed_freshness((), today=TODAY)
        self.assertEqual(result["products"], 0)
        self.assertIsNone(result["last_updated"]["median_age_days"])
        self.assertEqual(result["shops"], [])


if __name__ == "__main__":
    unittest.main()
