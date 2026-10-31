"""What the shops' own catalogues and the rows' barcodes give the feed's rows.

`src/picwise_providers/shop_catalogue.py`. Owner, 2026-10-26: «Θα κάνεις το 2 και το 3»
(the second, the bot for the shops whose rows carry no category: their Shopify type and
stock) and «Στα θέματα αντιστοίχισης ... barcode ... shopify, φτιάξε τους μηχανισμούς
σε αυτή τη βάση και ό,τι έρθει σωστό ήρθε»; InStock UK «συμμετέχει μόνο με τα προϊόντα
που έχει σωστά». Pinned here, through the same pipeline a search reads:

- a row without a category joins with its shop's type only when that type names its
  kind by itself (the title may narrow it); a type naming none, a title contradicting
  the type, no type and no product in the catalogue leave it held as before, and a row
  with a category keeps its own;
- the shop's sold-out holds a row the feed calls in stock (also one variant of it), not
  when what the bot saw is too old, and the shop's word never shows a row the feed
  calls out of stock;
- a row without a category takes, by its barcode, the category of another row, under
  the same rule, and not from a barcode on too many rows;
- the product's name read from the shop's address, also inside an Awin link, which is
  never opened;
- the note counts it all, and without the bot's file only the barcode applies.

Every row is local test data: fictional brands, `.invalid` hosts.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers import shop_catalogue  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    measure_configured_feed_intake,
    prepare_feed_catalogue,
)

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "stock_status", "merchant_name", "ean",
)
SHOP = "Fixture Office Shop"
OTHER = "Fixture Big Shop"
HOST = "https://office.example.invalid"


def _row(pid: str, title: str, *, shop: str = SHOP, category: str = "", url: str = "", ean: str = "",
         stock: str = "in stock") -> list[str]:
    return [
        pid, title, "Fixturon", category, url or f"{HOST}/products/{pid}",
        f"https://fixture.example.invalid/img/{pid}.jpg", "20.00", "GBP", "1" if stock == "in stock" else "0",
        stock, shop, ean,
    ]


def _today() -> str:
    return date.today().isoformat()


class _Feed:
    """A feed and a bot's file, configured for one test and restored after it."""

    def __init__(self, case: unittest.TestCase, rows: list[list[str]], catalogues: dict | None) -> None:
        folder = Path(tempfile.mkdtemp())
        feed = folder / "feed.csv"
        with feed.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            writer.writerows(rows)
        saved = {key: os.environ.get(key) for key in ("AWIN_FEED_FILE", shop_catalogue.CATALOGUES_ENV)}
        os.environ["AWIN_FEED_FILE"] = str(feed)
        if catalogues is None:
            os.environ.pop(shop_catalogue.CATALOGUES_ENV, None)
        else:
            path = folder / "catalogues.json.gz"
            if isinstance(catalogues, bytes):
                path.write_bytes(catalogues)
            else:
                with gzip.open(path, "wt", encoding="utf-8") as handle:
                    json.dump(catalogues, handle)
            os.environ[shop_catalogue.CATALOGUES_ENV] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        case.addCleanup(restore)

    @staticmethod
    def shown() -> dict[str, object]:
        """The products a card can show, as the server's preparation writes them."""
        return {product.provider_product_id: product for product in prepare_feed_catalogue().products}


def _catalogues(products: dict[str, list], *, shop: str = SHOP) -> dict:
    return {
        "version": 1,
        "written_at": "2026-10-26T03:55:00+00:00",
        "shops": {shop: {"status": "read", "read_at": "2026-10-26T03:50:00+00:00", "products": products}},
    }


class AddressNameTests(unittest.TestCase):
    def test_the_name_and_variant_come_from_the_shops_own_address(self) -> None:
        name = shop_catalogue.product_address_name
        self.assertEqual(name(f"{HOST}/products/Fixturon-Kettle"), ("fixturon-kettle", ""))
        self.assertEqual(name(f"{HOST}/collections/kettles/products/fixturon-kettle?variant=123"),
                         ("fixturon-kettle", "123"))
        awin = ("https://www.awin1.com/cread.php?awinmid=1&awinaffid=2&ued="
                + quote(f"{HOST}/products/fixturon-kettle?variant=456", safe=""))
        self.assertEqual(name(awin), ("fixturon-kettle", "456"))
        self.assertEqual(name("https://www.awin1.com/pclick.php?p=1&a=2&m=3"), ("", ""))
        self.assertEqual(name(f"{HOST}/kettles/fixturon-kettle"), ("", ""))
        self.assertEqual(name(f"{HOST}/products/fixturon-kettle?variant=x1"), ("fixturon-kettle", ""))


class ShopTypeTests(unittest.TestCase):
    def setUp(self) -> None:
        today = _today()
        _Feed(
            self,
            [
                _row("k1", "Fixturon Glass Kettle"),
                _row("k2", "Fixturon Electric Kettle"),
                _row("k3", "Fixturon Steel Kettle"),
                _row("k4", "Fixturon Travel Kettle"),
                _row("k5", "Fixturon Retro Kettle", category="Kettles"),
                _row("k6", "Fixturon Toaster 2-Slice"),
                _row("v1", "Fixturon Robot Vacuum Cleaner"),
            ],
            _catalogues(
                {
                    "k1": ["Kettles", 1, today, []],
                    "k2": ["Designer", 1, today, []],
                    "k3": ["", 1, today, []],
                    "k5": ["Toasters", 1, today, []],
                    "k6": ["Kettles", 1, today, []],
                    "v1": ["Vacuum Cleaners", 1, today, []],
                }
            ),
        )

    def test_a_type_naming_the_kind_brings_the_row_in(self) -> None:
        shown = _Feed.shown()
        self.assertIn("k1", shown)
        self.assertEqual(shown["k1"].category_text, "Kettles")
        self.assertEqual(shown["k1"].raw["product_type"], "Kettles")
        # The title narrows the type's kind.
        self.assertIn("v1", shown)

    def test_the_title_never_decides_alone(self) -> None:
        shown = _Feed.shown()
        # "Designer" names no kind; the title names a kettle: held, as before.
        self.assertNotIn("k2", shown)
        # No type, and no product in the catalogue.
        self.assertNotIn("k3", shown)
        self.assertNotIn("k4", shown)
        # The type says kettles, the title a toaster: doubtful, held.
        self.assertNotIn("k6", shown)

    def test_a_row_with_a_category_keeps_its_own(self) -> None:
        shown = _Feed.shown()
        self.assertEqual(shown["k5"].category_text, "Kettles")
        self.assertNotIn("product_type", shown["k5"].raw)

    def test_the_note_counts_each_way(self) -> None:
        _Feed.shown()
        note = shop_catalogue.last_shop_catalogue_note()
        self.assertEqual(note["file"], "read")
        self.assertEqual(note["shops_known"], 1)
        shop = note["shops"][0]
        self.assertEqual(shop["shop"], SHOP)
        self.assertEqual(
            {key: shop[key] for key in ("rows", "matched", "without_category", "by_type", "type_no_kind",
                                        "no_type", "not_found", "sold_out")},
            {"rows": 7, "matched": 6, "without_category": 6, "by_type": 2, "type_no_kind": 2, "no_type": 1,
             "not_found": 1, "sold_out": 0},
        )
        self.assertEqual(note["types_no_kind"], [{"value": "Designer", "rows": 1}, {"value": "Kettles", "rows": 1}])
        intake = measure_configured_feed_intake()
        self.assertEqual(intake["shown"], 3)
        self.assertEqual(intake["held_reasons"].get("missing_category_text"), 4)


class ShopStockTests(unittest.TestCase):
    def test_the_shops_sold_out_holds_a_row_the_feed_calls_in_stock(self) -> None:
        today = _today()
        old = (date.today() - timedelta(days=shop_catalogue.STOCK_DAYS + 1)).isoformat()
        _Feed(
            self,
            [
                _row("s1", "Fixturon Glass Kettle", category="Kettles"),
                _row("s2", "Fixturon Glass Kettle 1.7L", category="Kettles", url=f"{HOST}/products/s2?variant=111"),
                _row("s3", "Fixturon Glass Kettle 1.5L", category="Kettles", url=f"{HOST}/products/s2?variant=222"),
                _row("s4", "Fixturon Steel Kettle", category="Kettles"),
                _row("s5", "Fixturon Retro Kettle", category="Kettles", stock="out of stock"),
                _row("s6", "Fixturon Plain Kettle", category="Kettles"),
            ],
            _catalogues(
                {
                    "s1": ["Kettles", 0, today, []],
                    "s2": ["Kettles", 1, today, ["111"]],
                    "s4": ["Kettles", 0, old, []],
                    "s5": ["Kettles", 1, today, []],
                    "s6": ["Kettles", 1, today, []],
                }
            ),
        )
        shown = _Feed.shown()
        self.assertNotIn("s1", shown)
        # Only the variant the shop sells out.
        self.assertNotIn("s2", shown)
        self.assertIn("s3", shown)
        # Seen too long ago: the feed's word stands.
        self.assertIn("s4", shown)
        # The shop's "in stock" never shows a row the feed calls out of stock.
        self.assertNotIn("s5", shown)
        self.assertIn("s6", shown)
        shop = shop_catalogue.last_shop_catalogue_note()["shops"][0]
        self.assertEqual((shop["sold_out"], shop["sold_out_feed_in_stock"], shop["stock_too_old"]), (2, 2, 1))
        intake = measure_configured_feed_intake()
        self.assertEqual(intake["held_reasons"].get("availability_out_of_stock"), 3)


class BarcodeTests(unittest.TestCase):
    def test_a_row_takes_another_rows_category_by_its_barcode(self) -> None:
        _Feed(
            self,
            [
                _row("b1", "Fixturon Glass Kettle", shop=OTHER, ean="5012345678900", url="https://big.example.invalid/p/b1"),
                _row("c1", "Fixturon Glass Kettle 1.7L", shop="Fixture Kitchen Shop",
                     category="Home & Garden > Kitchen Appliances > Kettles", ean="05012345678900",
                     url="https://kitchen.example.invalid/p/c1"),
                _row("b2", "Fixturon Electric Kettle", shop=OTHER, ean="5098765432109", url="https://big.example.invalid/p/b2"),
                _row("c2", "Fixturon Electric Kettle", shop="Fixture Kitchen Shop", category="Gifts", ean="5098765432109",
                     url="https://kitchen.example.invalid/p/c2"),
                _row("b3", "Fixturon Steel Kettle", shop=OTHER, ean="", url="https://big.example.invalid/p/b3"),
            ],
            None,
        )
        shown = _Feed.shown()
        self.assertIn("b1", shown)
        self.assertEqual(shown["b1"].category_text, "Home & Garden > Kitchen Appliances > Kettles")
        # "Gifts" names no kind: the title would decide alone, so the row stays held.
        self.assertNotIn("b2", shown)
        self.assertNotIn("b3", shown)
        note = shop_catalogue.last_shop_catalogue_note()
        self.assertEqual(note["file"], "none")
        self.assertEqual(note["shops_known"], 0)
        self.assertEqual(
            note["barcode"],
            {"without_category": 3, "with_barcode": 2, "too_common": 0, "found": 2, "joined": 1, "no_kind": 1},
        )
        self.assertEqual(note["barcode_shops"], [{"shop": OTHER, "joined": 1}])

    def test_a_barcode_on_too_many_rows_names_no_product(self) -> None:
        rows = [
            _row("b1", "Fixturon Glass Kettle", shop=OTHER, ean="5012345678900", url="https://big.example.invalid/p/b1"),
            _row("c1", "Fixturon Glass Kettle", shop="Fixture Kitchen Shop", category="Kettles", ean="5012345678900",
                 url="https://kitchen.example.invalid/p/c1"),
            _row("c2", "Fixturon Glass Kettle", shop="Fixture Third Shop", category="Kettles", ean="5012345678900",
                 url="https://third.example.invalid/p/c2"),
        ]
        with mock.patch.object(shop_catalogue, "MAX_BARCODE_ROWS", 2):
            _Feed(self, rows, None)
            shown = _Feed.shown()
        self.assertNotIn("b1", shown)
        self.assertEqual(shop_catalogue.last_shop_catalogue_note()["barcode"]["too_common"], 1)


class FileTests(unittest.TestCase):
    def test_without_a_readable_file_only_the_barcode_applies(self) -> None:
        for catalogues, status in ((None, "none"), (b"not gzip", "unreadable"), ({"version": 2, "shops": {}}, "unreadable")):
            with self.subTest(status=status):
                _Feed(self, [_row("k1", "Fixturon Glass Kettle"), _row("k2", "Fixturon Kettle", category="Kettles")],
                      catalogues)
                shown = _Feed.shown()
                self.assertEqual(sorted(shown), ["k2"])
                note = shop_catalogue.last_shop_catalogue_note()
                self.assertEqual(note["file"], status)
                self.assertEqual(note["shops_known"], 0)

    def test_the_note_holds_no_address(self) -> None:
        _Feed(self, [_row("k1", "Fixturon Glass Kettle")], _catalogues({"k1": ["Kettles", 1, _today(), []]}))
        _Feed.shown()
        text = json.dumps(shop_catalogue.last_shop_catalogue_note())
        self.assertNotIn("example.invalid", text)
        self.assertNotIn("http", text)


if __name__ == "__main__":
    unittest.main()
