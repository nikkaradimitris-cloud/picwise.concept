"""A product's sizes and colours on one card (owner, 2026-11-24).

«υπάρχουν καταστήματα όπως το fila που ενώ έχουν καταχώρηση μεγεθών σε μία καταχώρηση ... στη
δική μας κάρτα δεν φαίνεται συγκεντρωτικά ... τα νούμερα και τα χρώματα να εμφανίζονται
συγκεντρωτικά και στη δική μας κάρτα ... σε όποια άλλη κατηγορία υπάρχει διαχωρισμός ... watt
διαστάσεις χρώματα ... για να μην έχουμε θόρυβο στην αναζήτηση». Asked, he chose: the title
without the size, «Από £32,50 και το χρώμα» when a shop's listings differ in price, «Μόνο τα
διαθέσιμα», and «Φτιάξε κατευθείαν».

Pinned here:
- the shop's own page (Shopify's JSON) gives its options and the values in stock;
- the checks' bot keeps them a product passed with, for 3 days, in its decisions; the
  preparation writes them on the row (`shop_options`);
- the card names them: a one-row product's sizes ("Sizes at the shop: XS, S, M"), one size
  left too; the title without the size at its end; "From £32.50 (Vintage Indigo)" when the
  shop's listings of the product differ in price;
- a row of Awin's own format is on its page by `merchant_deep_link`, so one shop's rows of
  one page are one card;
- a product alone under its head key is asked about with the others of its model, so that
  the AI can join a shop's colours named in words no list holds ("Vintage Indigo", "Grey Marl").

Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fixture_support import fixture_description  # noqa: E402
from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.page_reader import options_in_stock, read_shopify_product  # noqa: E402
from picwise_checks.verdicts import PASSED, Row, ShopNight, Verdict  # noqa: E402
from picwise_providers import checks_applied as applied  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.product_variants import page_key  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from picwise_providers.variant_families import doubtful_sets  # noqa: E402
from test_picwise_design_2026_10_31 import _COLUMNS, _call, _cards, _ean13, _text  # noqa: E402

NIGHT = date(2026, 12, 1)

# Shopify's own JSON of a hoodie in eight sizes, three of them in stock.
_JS = {
    "title": "Fixturon Indigo Tenconi Zip Up Hoodie",
    "options": [{"name": "Size", "position": 1, "values": ["XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL"]}],
    "variants": [
        {"id": 100 + index, "price": 3250, "available": size in ("XS", "S", "M"), "options": [size],
         "barcode": f"50000000000{index}", "sku": f"T-{size}"}
        for index, size in enumerate(["XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL"])
    ],
}


class ShopPageOptionsTests(unittest.TestCase):
    def test_a_shopify_page_s_options_in_stock(self) -> None:
        read = read_shopify_product(_JS, pence=True)
        self.assertEqual(read.option_names, ("Size",))
        self.assertEqual(json.loads(options_in_stock(read)), [["Size", ["XS", "S", "M"]]])

    def test_a_catalogue_product_s_options_by_their_place(self) -> None:
        product = {
            "title": "Fixturon Runner",
            "options": [{"name": "Colour", "position": 1}, {"name": "Shoe Size", "position": 2}],
            "variants": [
                {"id": 1, "price": "50.00", "available": True, "option1": "Black", "option2": "8"},
                {"id": 2, "price": "50.00", "available": False, "option1": "Black", "option2": "9"},
                {"id": 3, "price": "50.00", "available": True, "option1": "White", "option2": "9"},
            ],
        }
        self.assertEqual(json.loads(options_in_stock(read_shopify_product(product, pence=False))),
                         [["Colour", ["Black", "White"]], ["Shoe Size", ["8", "9"]]])

    def test_a_product_with_no_variants_names_none(self) -> None:
        product = {"title": "Fixturon Kettle", "options": [{"name": "Title"}],
                   "variants": [{"id": 1, "price": 2499, "available": True, "options": ["Default Title"]}]}
        self.assertEqual(options_in_stock(read_shopify_product(product, pence=True)), "")


class LedgerOptionsTests(unittest.TestCase):
    def _rows(self) -> dict[str, Row]:
        key = "Fixture Sport\x1f1"
        return {key: Row(key=key, shop="Fixture Sport", product_id="1", address="https://sport.invalid/p/1",
                         title="Fixturon Hoodie - L", price=32.5, feed_stock="in stock")}

    def _night(self, ledger: L.Ledger, night: date, rows: dict[str, Row], options: str) -> None:
        readings = {key: L.Reading(page=Verdict(PASSED, by="by code"), options=options) for key in rows}
        L.record_night(ledger, night, rows, readings,
                       {"Fixture Sport": ShopNight(requests=1, answers=1, pages_200=1, pages_read=1)}, shown=set(rows))

    def test_options_read_tonight_are_in_the_decisions_for_3_days(self) -> None:
        ledger, rows = L.Ledger(), self._rows()
        options = json.dumps([["Size", ["XS", "S", "M"]]])
        self._night(ledger, NIGHT, rows, options)
        key = next(iter(rows))
        self.assertEqual(L.decisions(ledger, NIGHT, rows, shown=rows.keys())["options"],
                         {key: [options, NIGHT.isoformat()]})
        self.assertIn(key, L.decisions(ledger, NIGHT + timedelta(days=3), rows, shown=rows.keys())["options"])
        self.assertEqual(L.decisions(ledger, NIGHT + timedelta(days=4), rows, shown=rows.keys())["options"], {})

    def test_a_ledger_written_before_the_options_reads_as_before(self) -> None:
        ledger, rows = L.Ledger(), self._rows()
        self._night(ledger, NIGHT, rows, "")
        path = Path(tempfile.mkdtemp()) / "ledger.json.gz"
        L.save(ledger, path)
        import gzip

        with gzip.open(path, "rt", encoding="utf-8") as handle:
            document = json.load(handle)
        for values in document["products"].values():
            del values[-2:]
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(document, handle)
        self.assertEqual(next(iter(L.load(path).products.values())).options, "")


class AppliedOptionsTests(unittest.TestCase):
    def setUp(self) -> None:
        applied.reset_for_tests()

    def test_the_preparation_writes_them_on_the_row(self) -> None:
        product = ProviderProduct(
            provider_key="awin", provider_product_id="row-1", title="Fixturon Hoodie - L", brand="Fixturon",
            category_text="", product_url="https://sport.invalid/p/1", image_url="https://sport.invalid/i/1.jpg",
            price_text="32.50", availability_text="in stock", currency="GBP",
            raw={"merchant_name": "Fixture Sport", "availability": "in stock"},
        )
        key = applied._key(product)
        options = json.dumps([["Size", ["XS", "S", "M"]]])
        decisions = {"format": applied.DECISIONS_FORMAT, "version": 1, "night": "2026-12-01", "shops_out": {},
                     "cut": {}, "enter": [], "prices": {}, "stock": {}, "returning": [],
                     "options": {key: [options, "2026-12-01"]}}
        done = applied.apply_checks((product,), decisions=decisions, switch=True)
        self.assertEqual(done[0].raw[applied.OPTIONS_COLUMN], options)
        self.assertEqual(applied.last_checks_note()["options_from_page"], 1)


def _serve(test: unittest.TestCase, rows: list[dict[str, str]]) -> None:
    columns = _COLUMNS + ("shop_options", "merchant_deep_link")
    path = Path(tempfile.mkdtemp()) / "feed.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            pid = row["pid"]
            writer.writerow(
                [pid, row["title"], "Fixturon", "Hoodies", "Clothing", f"https://fixture.example.invalid/out/{pid}",
                 f"https://fixture.example.invalid/img/{pid}.jpg", row["price"], "GBP", "1",
                 row.get("shop", "Fixture Sport"), fixture_description(), "local_test_fixture",
                 row.get("ean", ""), "", row.get("options", ""), row.get("page", "")]
            )
    previous = os.environ.get("AWIN_FEED_FILE")
    os.environ["AWIN_FEED_FILE"] = str(path)
    clear_awin_feed_parse_cache()
    clear_provider_feed_pipeline_cache()

    def restore() -> None:
        if previous is None:
            os.environ.pop("AWIN_FEED_FILE", None)
        else:
            os.environ["AWIN_FEED_FILE"] = previous
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    test.addCleanup(restore)


def _card_of(page: str, words: str) -> str:
    return next(card for card in _cards(page) if words in _text(card))


class CardTests(unittest.TestCase):
    def setUp(self) -> None:
        # Six hoodies of one shop, each its own model; the first sold in its sizes on one page
        # (one row), the last two one model in two colours at two prices.
        sizes = json.dumps([["Size", ["XS", "S", "M"]]])
        self.rows = [
            {"pid": "h1", "title": "Fixturon Indigo Tenconi Zip Up Hoodie - L", "price": "32.50",
             "options": sizes, "ean": _ean13("710000000001")},
            {"pid": "h2", "title": "Fixturon Jorie Crew Hoodie Grey", "price": "25.00", "ean": _ean13("710000000002")},
            {"pid": "h3", "title": "Fixturon Sestri Wide Hoodie Blue", "price": "30.00", "ean": _ean13("710000000003")},
            {"pid": "h4", "title": "Fixturon Italo Velour Hoodie Navy", "price": "80.00", "ean": _ean13("710000000004")},
            {"pid": "h5", "title": "Fixturon Rolando Zip Hoodie - Black", "price": "45.00", "ean": _ean13("710000000005"),
             "options": json.dumps([["Size", ["M"]]]), "page": "https://sport.invalid/products/rolando"},
            {"pid": "h6", "title": "Fixturon Rolando Zip Hoodie - White", "price": "75.00", "ean": _ean13("710000000006"),
             "options": json.dumps([["Size", ["S", "L"]]]), "page": "https://sport.invalid/products/rolando"},
            # One page, two listings told apart by a use, not a colour.
            {"pid": "h7", "title": "Fixturon Lounge Hoodie Relaxed", "price": "20.00", "ean": _ean13("710000000007"),
             "page": "https://sport.invalid/products/lounge"},
            {"pid": "h8", "title": "Fixturon Lounge Hoodie Classic", "price": "28.00", "ean": _ean13("710000000008"),
             "page": "https://sport.invalid/products/lounge"},
        ]
        _serve(self, self.rows)
        self.page = _call("/search", {"q": "hoodie", "shown": "8"})

    def test_a_one_row_product_names_its_sizes_in_stock_and_its_title_loses_the_size(self) -> None:
        card = _card_of(self.page, "Tenconi")
        self.assertIn("Sizes at the shop: XS, S, M", _text(card))
        title = _text(re.search(r'class="pw-card-title"[^>]*>(.*?)</', card, re.S).group(1))
        self.assertEqual(title, "Fixturon Indigo Tenconi Zip Up Hoodie")

    def test_one_page_s_colours_are_one_card_from_its_cheapest_with_its_colour(self) -> None:
        rolando = [card for card in _cards(self.page) if "Rolando" in _text(card)]
        self.assertEqual(len(rolando), 1)
        text = _text(rolando[0])
        self.assertIn("From £45.00 (Black)", text)
        self.assertIn("Sizes at the shop: S, M, L", text)
        self.assertIn("Colours at the shop: Black, White", text)

    def test_words_that_name_no_colour_are_not_put_in_brackets(self) -> None:
        # Owner, 2026-11-24, of "From £34.99 (Bedroom)": «Ναι» to the brackets only for a colour.
        text = _text(_card_of(self.page, "Lounge"))
        self.assertIn("From £20.00", text)
        self.assertNotIn("(Relaxed)", text)

    def test_a_card_at_one_price_reads_as_before(self) -> None:
        self.assertNotIn("From", _text(_card_of(self.page, "Sestri")))


class PageOfAnAwinRowTests(unittest.TestCase):
    def test_merchant_deep_link_is_the_page(self) -> None:
        raw = {"merchant_name": "Fixture Sport", "merchant_deep_link": "https://sport.invalid/products/rolando?variant=2"}
        self.assertEqual(page_key(raw), "Fixture Sport\x1fsport.invalid/products/rolando")
        self.assertEqual(page_key({**raw, "link": "https://sport.invalid/products/other"}),
                         "Fixture Sport\x1fsport.invalid/products/other")


class ModelSetsTests(unittest.TestCase):
    def test_a_shop_s_colours_named_before_the_model_are_asked_together(self) -> None:
        def product(pid: str, title: str, price: str) -> ProviderProduct:
            return ProviderProduct(
                provider_key="awin", provider_product_id=pid, title=title, brand="Fixturon", category_text="",
                product_url=f"https://x.invalid/{pid}", image_url="", price_text=price, availability_text="in stock",
                currency="GBP", raw={"merchant_name": "Fixture Sport", "merchant_deep_link": f"https://sport.invalid/p/{pid}"},
            )

        products = [
            product("1", "Vintage Indigo Tenconi Zip Up Hoodie - XS", "32.50"),
            product("2", "Black Tenconi Zip Up Hoodie - L", "65.00"),
            product("3", "Fixture Navy Tenconi Zip Up Hoodie - M", "65.00"),
            product("4", "Grey Marl Tenconi Zip Up Hoodie - M", "65.00"),
            product("5", "Fixture Navy Jorie Wide Crew Neck Sweatshirt - L", "25.00"),
        ]
        sets = doubtful_sets(products)
        self.assertEqual(len(sets), 1)
        self.assertEqual(sorted(listing["products"][0].split("\x1f")[-1] for listing in sets[0]["listings"]),
                         ["1", "2", "3", "4"])


if __name__ == "__main__":
    unittest.main()
