"""The shop's own site checks its feed's stock (owner, 2026-11-12: «να διαβάζει το bot
το απόθεμα από τα sites τους και γενικά να επαληθεύει»).

Six shops gave no product on 12/11, their feeds calling every row out of stock in the
`availability` column. The shops' catalogue bot reads each shop's own catalogue; what it
saw within the last days (`shop_catalogue.STOCK_DAYS`) decides a row's stock before the
feed, either way. Pinned here:

- the shop's "sold out" holds a row the feed calls in stock, and its "in stock" shows a
  row the feed calls out of stock, each said as the shop's site's reading;
- with no reading of the shop's site, the feed decides as before;
- the bot asks every shop the public note names, not only those with rows held for no
  category; never InStock UK, never a shop the owner left out.

The ends of the rule (a reading too old is not used; a variant sold out) are pinned in
`tests/test_picwise_shop_catalogue.py`. Every row is local test data.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.offer_health import build_feed_availability_context, interpret_availability_state  # noqa: E402


def _product(pid: str, feed_says: str, shop_says: str = "") -> ProviderProduct:
    raw = {"merchant_name": "Fixture Shop", "availability": feed_says, "in_stock": "1" if feed_says == "in stock" else "0"}
    if shop_says:
        raw["shop_stock"] = shop_says
    return ProviderProduct(
        provider_key="awin", provider_product_id=pid, title=f"Fixturon Kettle {pid}", brand="Fixturon",
        category_text="Kettles", product_url=f"https://fixture.example.invalid/products/{pid}",
        image_url=f"https://fixture.example.invalid/img/{pid}.jpg", price_text="20.00",
        availability_text=feed_says, currency="GBP", raw=raw,
    )


class ShopSiteStockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            _product("a", "out of stock", "in stock"),
            _product("b", "in stock", "sold out"),
            _product("c", "out of stock"),
            _product("d", "in stock"),
        ]
        self.context = build_feed_availability_context(tuple(self.products))

    def _read(self, index: int) -> tuple[str, str, str]:
        return interpret_availability_state(self.products[index], feed_ctx=self.context)

    def test_the_shops_site_decides_either_way(self) -> None:
        self.assertEqual(self._read(0), ("trusted", "shop_stock", "shop_site_in_stock"))
        self.assertEqual(self._read(1), ("out_of_stock", "shop_stock", "shop_site_sold_out"))

    def test_without_a_reading_of_the_site_the_feed_decides(self) -> None:
        self.assertEqual(self._read(2)[0], "out_of_stock")
        self.assertNotEqual(self._read(2)[1], "shop_stock")
        self.assertIn(self._read(3)[0], {"trusted", "weak"})


class BotAsksEveryShopTests(unittest.TestCase):
    def test_every_shop_the_note_names_but_instock_uk_and_the_left_out(self) -> None:
        spec = importlib.util.spec_from_file_location("shop_catalogue_bot_under_test", ROOT / "deployment" / "bot" / "shop_catalogue_bot.py")
        bot = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = bot
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(bot)
        note = {
            "intake": {
                "shops": [
                    {"shop": "Fixture Silent Shop", "rows": 300, "shown": 0, "without_category": {}},
                    {"shop": "Fixture Full Shop", "rows": 50, "shown": 50, "without_category": {}},
                    {"shop": "InStock UK", "rows": 900, "shown": 100, "without_category": {}},
                    {"shop": "So Divine", "rows": 81, "shown": 0, "without_category": {}},
                    {"shop": "Fixture Empty Shop", "rows": 0, "shown": 0, "without_category": {}},
                ]
            }
        }
        path = Path(tempfile.mkdtemp()) / "prepared.json"
        path.write_text(json.dumps(note), encoding="utf-8")
        self.assertEqual(
            bot.shops_to_ask(str(path), {"Fixture Known Shop": {}}),
            ["Fixture Full Shop", "Fixture Known Shop", "Fixture Silent Shop"],
        )


if __name__ == "__main__":
    unittest.main()
