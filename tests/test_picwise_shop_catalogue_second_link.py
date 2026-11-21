"""A row of the second Awin link takes what its shop's own site says, as a first-link row does.

`shop_catalogue.apply_shop_catalogues` finds a row's product in the bot's file by the
name in its shop's own address. A row of the second link (Awin's own format, since
2026-11-19) links through Awin's "pclick.php", which carries no address, so until 21/11
none of its rows met a reading of its shop's site: the owner's rules, every shop's own
site checks its feed's stock (2026-11-12) and the first feed's rules hold for the second
(2026-11-20), held for the first link alone. Its shop's own address is the row's
`merchant_deep_link` (`shop_catalogue.own_address`, which the bot reads too). Pinned here,
through the same pipeline the night's preparation runs: the shop's "sold out" holds a
second-link row (also one variant of it), its "in stock" stands, a row with no address of
its own is left to its feed's word, and the note counts them as a first-link row's.

Every row is local test data: fictional brands, `.invalid` hosts. Nothing is opened.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import shop_catalogue  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache, prepare_feed_catalogue  # noqa: E402

FIRST = ("aw_product_id", "product_name", "brand_name", "merchant_category", "aw_deep_link", "aw_image_url",
         "search_price", "currency", "in_stock", "merchant_name")
SECOND = ("aw_product_id", "product_name", "brand_name", "merchant_id", "merchant_name", "search_price", "currency",
          "aw_deep_link", "merchant_deep_link", "merchant_image_url", "in_stock", "merchant_category")
OFFICE = "https://office.example.invalid"
TOOLS = "https://tools.example.invalid"
TOOLS_SHOP = "Fixture Tools Shop"


def _write(path: Path, header: tuple[str, ...], rows: list[list[str]]) -> str:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return str(path)


def _second(pid: str, own: str) -> list[str]:
    return [pid, f"Fixturon Glass Kettle {pid}", "Fixturon", "7", TOOLS_SHOP, "20.00", "GBP",
            f"https://www.awin1.com/pclick.php?p={pid}&a=2&m=7", own, f"https://fixture.example.invalid/img/{pid}.jpg",
            "1", "Kettles"]


class SecondLinkStockTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = Path(tempfile.mkdtemp())
        first = _write(folder / "first.csv", FIRST, [
            ["o1", "Fixturon Steel Kettle o1", "Fixturon", "Kettles", f"{OFFICE}/products/o1",
             "https://fixture.example.invalid/img/o1.jpg", "25.00", "GBP", "1", "Fixture Office Shop"],
        ])
        second = _write(folder / "second.csv", SECOND, [
            _second("t1", f"{TOOLS}/products/t1"),
            _second("t2", f"{TOOLS}/products/t2?variant=55"),
            _second("t3", f"{TOOLS}/products/t2?variant=66"),
            _second("t4", f"{TOOLS}/products/t4"),
            _second("t5", ""),
        ])
        today = date.today().isoformat()
        catalogues = folder / "catalogues.json.gz"
        with gzip.open(catalogues, "wt", encoding="utf-8") as handle:
            json.dump({"version": 1, "written_at": f"{today}T03:55:00+00:00", "shops": {TOOLS_SHOP: {
                "status": "read", "read_at": f"{today}T03:50:00+00:00", "products": {
                    "t1": ["Kettles", 0, today, []],
                    "t2": ["Kettles", 1, today, ["55"]],
                    "t4": ["Kettles", 1, today, []],
                    "t5": ["Kettles", 0, today, []],
                }}}}, handle)
        env = {key: value for key, value in os.environ.items() if not key.startswith("AWIN_FEED_")}
        env.update({"AWIN_FEED_FILE": first, "AWIN_FEED_FILE_AWIN": second,
                    shop_catalogue.CATALOGUES_ENV: str(catalogues)})
        patch = mock.patch.dict(os.environ, env, clear=True)
        patch.start()
        self.addCleanup(patch.stop)
        for clear in (clear_awin_feed_parse_cache, clear_provider_feed_pipeline_cache):
            clear()
            self.addCleanup(clear)

    def test_the_shops_own_site_decides_a_second_link_rows_stock(self) -> None:
        shown = {product.provider_product_id: product for product in prepare_feed_catalogue().products}
        # The first link's row, of a shop the bot's file does not hold: as before.
        self.assertIn("o1", shown)
        # Sold out by the shop's site, the whole product or the variant its address names.
        self.assertNotIn("t1", shown)
        self.assertNotIn("t2", shown)
        # Another variant of the same product, not sold out.
        self.assertIn("t3", shown)
        self.assertEqual(shown["t3"].raw["shop_stock"], "in stock")
        self.assertEqual(shown["t4"].raw["shop_stock"], "in stock")
        # No address of its own: its feed's word stands (the file's "t5" is never met).
        self.assertIn("t5", shown)
        self.assertNotIn("shop_stock", shown["t5"].raw)
        note = {entry["shop"]: entry for entry in shop_catalogue.last_shop_catalogue_note()["shops"]}
        tools = note[TOOLS_SHOP]
        self.assertEqual((tools["rows"], tools["matched"], tools["sold_out"], tools["in_stock"]), (5, 4, 2, 2))
        self.assertEqual(tools["sold_out_feed_in_stock"], 2)


class OwnAddressTests(unittest.TestCase):
    def test_the_links_own_else_the_rows_merchant_deep_link_never_an_awin_link(self) -> None:
        own = shop_catalogue.own_address
        pclick = "https://www.awin1.com/pclick.php?p=1&a=2&m=7"
        self.assertEqual(own(f"{OFFICE}/products/o1", {"merchant_deep_link": f"{TOOLS}/products/t1"}),
                         f"{OFFICE}/products/o1")
        self.assertEqual(own(pclick, {"merchant_deep_link": f"{TOOLS}/products/t1?variant=5"}),
                         f"{TOOLS}/products/t1?variant=5")
        self.assertEqual(shop_catalogue.product_address_name(own(pclick, {"merchant_deep_link": f"{TOOLS}/products/T1?variant=5"})),
                         ("t1", "5"))
        self.assertEqual(own(pclick, {}), "")
        self.assertEqual(own(pclick, {"merchant_deep_link": pclick}), "")
        self.assertEqual(own(pclick, {"merchant_deep_link": "javascript:void(0)"}), "")


if __name__ == "__main__":
    unittest.main()
