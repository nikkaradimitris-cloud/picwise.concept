"""What each shop's feed brings in, measured for the deployment's public note.

`src/picwise_providers/feed_intake.py`. Owner, 2026-10-18: first many more shops,
"with whatever each one's feed sends". Shops differ in what they send, and the rules
that keep a product off the page apply to all alike, so the build says per shop how
many rows a search can show, how many only when asked for, and why the others are held
back. Pinned here: the counts per shop and in all, every reason counted, and that the
note carries them without anything of the feed's link. Owner, 2026-10-23: also what
each shop writes in `product_type`, and how much of it on rows with no category.

Owner, 2026-10-25, with every Google-format shop on the server (about 532,000 of
1,123,857 rows with no category): of the rows held for that alone, how many could be
shown by their own product type, or by their title alone, and read as what kind; pinned
too.

Every row is local test data: fictional brands, `.invalid` URLs.
"""
from __future__ import annotations

import csv
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
from picwise_providers.state import (  # noqa: E402
    clear_provider_feed_pipeline_cache,
    measure_configured_feed_intake,
    prepare_feed_catalogue,
)

_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "merchant_category", "aw_deep_link",
    "aw_image_url", "search_price", "currency", "in_stock", "stock_status", "merchant_name",
    "condition", "product_type",
)


def _row(pid: str, shop: str, *, category: str = "Kettles", image: bool = True, url: str = "",
         stock: str = "", condition: str = "", price: str = "20.00", product_type: str = "",
         title: str = "") -> list[str]:
    return [
        pid, title or f"Fixturon Electric Kettle {pid}", "Fixturon", category,
        url or f"https://fixture.example.invalid/out/{pid}",
        f"https://fixture.example.invalid/img/{pid}.jpg" if image else "",
        price, "GBP", "1", stock, shop, condition, product_type,
    ]


_LONG_TYPE = "Office Supplies > " + " > ".join(f"Shelf {number}" for number in range(1, 20))


def _use_feed(case: unittest.TestCase, rows: list[list[str]]) -> Path:
    """Write the rows as the configured feed for this test, and restore after it."""
    feed = Path(tempfile.mkdtemp()) / "feed.csv"
    with feed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(_COLUMNS)
        writer.writerows(rows)
    saved = os.environ.get("AWIN_FEED_FILE")
    os.environ["AWIN_FEED_FILE"] = str(feed)
    clear_awin_feed_parse_cache()
    clear_provider_feed_pipeline_cache()

    def restore() -> None:
        if saved is None:
            os.environ.pop("AWIN_FEED_FILE", None)
        else:
            os.environ["AWIN_FEED_FILE"] = saved
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    case.addCleanup(restore)
    return feed


class FeedIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        rows = [
            _row("a1", "Fixture Store One", product_type="Small Appliances > Kettles"),
            _row("a2", "Fixture Store One", product_type="Small Appliances > Kettles"),
            _row("a3", "Fixture Store One", condition="Refurbished"),
            _row("a4", "Fixture Store One", stock="Out of stock", product_type="Kettles"),
            _row("b1", "Fixture Store Two", category="", product_type="Office > Kettles"),
            _row("b2", "Fixture Store Two", category=""),
            _row("b3", "Fixture Store Two", image=False, product_type=_LONG_TYPE),
            _row("b4", "Fixture Store Two", url="not-a-link"),
            _row("b5", "Fixture Store Two", category="", image=False, product_type="Office > Kettles"),
            _row("b6", "Fixture Store Two", product_type="  Office   >  Kettles "),
        ]
        self.feed = _use_feed(self, rows)

    def test_each_shop_says_what_it_brings_and_why_the_rest_is_held(self) -> None:
        intake = measure_configured_feed_intake()
        one, two = intake["shops"][1], intake["shops"][0]
        self.assertEqual((two["shop"], one["shop"]), ("Fixture Store Two", "Fixture Store One"))
        self.assertEqual(
            {key: one[key] for key in ("rows", "shown", "not_new", "held")},
            {"rows": 4, "shown": 2, "not_new": 1, "held": 1},
        )
        # The reasons are the card gate's own codes, as it gives them.
        self.assertEqual(
            one["held_reasons"], {"availability_out_of_stock": 1, "purchasability_out_of_stock": 1}
        )
        self.assertEqual(
            {key: two[key] for key in ("rows", "shown", "not_new", "held")},
            {"rows": 6, "shown": 1, "not_new": 0, "held": 5},
        )
        # A shop that sends no category loses those rows at the feed gate; a row held
        # back for two reasons counts under both.
        self.assertEqual(
            two["held_reasons"],
            {"missing_category_text": 3, "missing_image_url": 2, "invalid_product_url": 1},
        )

    def test_the_totals_add_up(self) -> None:
        intake = measure_configured_feed_intake()
        self.assertEqual(
            {key: intake[key] for key in ("rows", "shown", "not_new", "held")},
            {"rows": 10, "shown": 3, "not_new": 1, "held": 6},
        )
        self.assertEqual(intake["shown"] + intake["not_new"] + intake["held"], intake["rows"])
        for shop in intake["shops"]:
            self.assertEqual(shop["shown"] + shop["not_new"] + shop["held"], shop["rows"])
        self.assertEqual(intake["held_reasons"]["missing_category_text"], 3)
        self.assertNotIn("fixture.example.invalid", repr(intake))

    def test_each_shop_says_what_its_product_type_carries(self) -> None:
        # Measured, not read: a row with no category stays held whatever its type says.
        intake = measure_configured_feed_intake()
        one, two = intake["shops"][1], intake["shops"][0]
        self.assertEqual(
            one["product_type"],
            {
                "filled": 3,
                "filled_without_category": 0,
                "examples": [
                    {"value": "Small Appliances > Kettles", "rows": 2},
                    {"value": "Kettles", "rows": 1},
                ],
            },
        )
        # The most frequent value first, spaces as one, a long value cut to 100.
        self.assertEqual(two["product_type"]["filled"], 4)
        self.assertEqual(two["product_type"]["filled_without_category"], 2)
        self.assertEqual(two["held_reasons"]["missing_category_text"], 3)
        examples = two["product_type"]["examples"]
        self.assertEqual(examples[0], {"value": "Office > Kettles", "rows": 3})
        self.assertEqual(examples[1]["rows"], 1)
        self.assertEqual(len(examples[1]["value"]), 100)
        self.assertTrue(examples[1]["value"].endswith("..."))
        self.assertTrue(_LONG_TYPE.startswith(examples[1]["value"][:-3]))

    def test_no_feed_no_intake(self) -> None:
        os.environ["AWIN_FEED_FILE"] = str(self.feed.parent / "no-such-feed.csv")
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        self.assertIsNone(measure_configured_feed_intake())


class RowsWithoutCategoryTests(unittest.TestCase):
    def setUp(self) -> None:
        shop = "Fixture Store Three"
        _use_feed(
            self,
            [
                # Its own type names a kind, and the card gate passes it.
                _row("c1", shop, category="", product_type="Kitchen > Kettles"),
                # Out of stock: held anyway.
                _row("c2", shop, category="", product_type="Kitchen > Kettles", stock="Out of stock"),
                # No type: the title alone, a kind, nothing, an accessory, doubtful.
                _row("c3", shop, category=""),
                _row("c4", shop, category="", title="Fixturon Thing 4"),
                _row("c5", shop, category="", stock="Out of stock"),
                # Held for a missing image too: not counted as held for the category alone.
                _row("c6", shop, category="", image=False),
                # A type naming no kind PicWise knows: doubtful.
                _row("c7", shop, category="", product_type="Gift Ideas"),
                _row("c8", shop, category="", title="Fixturon Chocolate Mice 225g"),
                _row("c9", shop, category="", title="Fixturon Kettle Descaler Tablets"),
                _row("c10", shop, category="", title="Fixturon Hoover Paperback"),
                _row("d1", "Fixture Store Four"),
            ],
        )

    def test_how_many_could_be_shown_by_type_or_title_and_read_as_what(self) -> None:
        intake = measure_configured_feed_intake()
        three = next(shop for shop in intake["shops"] if shop["shop"] == "Fixture Store Three")
        without = dict(three["without_category"])
        # Where else a category may hide: `HintsTests` below.
        self.assertEqual(without.pop("hints")["address"]["rows"], 5)
        self.assertEqual(
            without,
            {
                "rows": 10,
                "only_this": 9,
                "with_product_type": 3,
                "shown_by_type": 2,
                "shown_by_title": 5,
                "kinds_by_type": {"kind": 1, "accessory": 0, "doubtful": 1, "none": 0},
                "kinds_by_title": {"kind": 2, "accessory": 1, "doubtful": 1, "none": 1},
                "types": [{"value": "Gift Ideas", "rows": 1}, {"value": "Kitchen > Kettles", "rows": 1}],
                # A title read as a kind by itself is the search's risk: chocolate mice.
                "titles": ["Fixturon Electric Kettle c3 -> kettle", "Fixturon Chocolate Mice 225g -> mouse"],
            },
        )
        # Still held: measured, not read.
        self.assertEqual(three["shown"], 0)

    def test_a_shop_with_a_category_on_every_row_and_the_totals(self) -> None:
        intake = measure_configured_feed_intake()
        four = next(shop for shop in intake["shops"] if shop["shop"] == "Fixture Store Four")
        self.assertEqual(
            {key: four["without_category"][key] for key in ("rows", "only_this", "shown_by_type", "shown_by_title")},
            {"rows": 0, "only_this": 0, "shown_by_type": 0, "shown_by_title": 0},
        )
        self.assertEqual(four["without_category"]["types"], [])
        totals = dict(intake["without_category"])
        for place in ("address", "barcode"):
            self.assertEqual(totals.pop(place)["rows"], 5)
        self.assertEqual(totals.pop("description")["title_gives_none"], 3)
        self.assertEqual(
            totals,
            {
                "rows": 10,
                "only_this": 9,
                "with_product_type": 3,
                "shown_by_type": 2,
                "shown_by_title": 5,
                "kinds_by_type": {"kind": 1, "accessory": 0, "doubtful": 1, "none": 0},
                "kinds_by_title": {"kind": 2, "accessory": 1, "doubtful": 1, "none": 1},
            },
        )
        self.assertNotIn("fixture.example.invalid", repr(intake))


_GOOGLE_COLUMNS = (
    "id", "title", "link", "image_link", "price", "availability", "google_product_category",
    "custom_label_0", "advertiser_name", "gtin", "description",
)


def _google_row(pid: str, title: str, link: str, label: str = "", category: str = "", gtin: str = "",
                description: str = "", shop: str = "Fixture Store Five") -> list[str]:
    return [
        pid, title, link, f"https://fixture.example.invalid/img/{pid}.jpg", "20.00 GBP", "in stock", category,
        label, shop, gtin, description,
    ]


class HintsTests(unittest.TestCase):
    """Owner, 2026-10-26: «Ο στόχος είναι να λύσεις αυτό το πρόβλημα», without the shops:
    where else a row without a category may name one."""

    def setUp(self) -> None:
        cread = "https://www.awin1.com/cread.php?awinmid=1&awinaffid=2&ued="
        feed = Path(tempfile.mkdtemp()) / "feed.csv"
        with feed.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_GOOGLE_COLUMNS)
            writer.writerows(
                [
                    # An Awin link carrying the shop's address, which names a kettles shelf.
                    _google_row("g1", "Fixturon Glass Electric Kettle",
                                cread + "https%3A%2F%2Fshop.example.invalid%2Fkitchen%2Fkettles%2Ffixturon-glass-kettle",
                                label="Kettles"),
                    # An Awin link carrying no address.
                    _google_row("g2", "Fixturon Steel Electric Kettle",
                                "https://www.awin1.com/pclick.php?p=123&a=2&m=1", label="Kettles"),
                    # The shop's own address, naming a shelf that is no kind.
                    _google_row("g3", "Fixturon Chocolate Mice 225g",
                                "https://shop.example.invalid/sweets/chocolate-mice-225g", label="Sweets"),
                    # With a category: not counted.
                    _google_row("g4", "Fixturon Toaster", "https://shop.example.invalid/kitchen/toasters/t",
                                category="Kitchen Appliances > Toasters"),
                    # Its barcode is sold by another shop with a category: since 2026-10-26 it takes
                    # that category (`shop_catalogue.py`), so it is no longer among these rows.
                    _google_row("g5", "Fixturon Rapid Boil 1.7L", "https://shop.example.invalid/products/rb",
                                gtin="05012345678900",
                                description="<p>This glass electric kettle boils 1.7 litres fast.</p> Free delivery."),
                    _google_row("o1", "Fixturon Rapid Boil 1.7L Glass Kettle", "https://other.example.invalid/k/o1",
                                category="Kitchen Appliances > Kettles", gtin="5012345678900",
                                shop="Fixture Store Six"),
                    # No barcode; its title names nothing, its description's first sentence does.
                    _google_row("g6", "Fixturon Rapid Boil 1.5L", "https://shop.example.invalid/products/rb6",
                                description="<p>This glass electric kettle boils 1.5 litres fast.</p> Free delivery."),
                ]
            )
        saved = os.environ.get("AWIN_FEED_FILE")
        os.environ["AWIN_FEED_FILE"] = str(feed)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

        def restore() -> None:
            if saved is None:
                os.environ.pop("AWIN_FEED_FILE", None)
            else:
                os.environ["AWIN_FEED_FILE"] = saved
            clear_awin_feed_parse_cache()
            clear_provider_feed_pipeline_cache()

        self.addCleanup(restore)

    def test_columns_labels_and_the_shops_address(self) -> None:
        intake = measure_configured_feed_intake()
        five = next(shop for shop in intake["shops"] if shop["shop"] == "Fixture Store Five")
        hints = five["without_category"]["hints"]
        self.assertEqual(
            {entry["column"]: entry["rows"] for entry in hints["columns"]}["custom_label_0"], 3
        )
        self.assertEqual(
            hints["values"]["custom_label_0"],
            [{"value": "Kettles", "rows": 2}, {"value": "Sweets", "rows": 1}],
        )
        self.assertEqual(
            hints["address"], {"rows": 4, "names_shelves": 3, "a_kind": 1, "title_kind_too": 1, "agrees": 1}
        )
        self.assertEqual(
            hints["address_shelves"],
            [{"value": "kitchen > kettles", "rows": 1}, {"value": "products", "rows": 1}, {"value": "sweets", "rows": 1}],
        )
        self.assertEqual(intake["without_category"]["address"], hints["address"])

    def test_another_rows_category_for_the_barcode_and_the_description(self) -> None:
        intake = measure_configured_feed_intake()
        five = next(shop for shop in intake["shops"] if shop["shop"] == "Fixture Store Five")
        hints = five["without_category"]["hints"]
        # g5's barcode, read without its leading zeros, is o1's, filed under kettles: g5 takes
        # that category and is shown, so none of the rows left without one has a barcode.
        self.assertEqual(
            hints["barcode"],
            {"rows": 4, "with_barcode": 0, "found_with_category": 0, "a_kind": 0, "title_kind_too": 0,
             "agrees": 0, "title_gives_none": 0},
        )
        # g4, with its own category, and now g5.
        self.assertEqual(five["shown"], 2)
        shown = {product.provider_product_id: product for product in prepare_feed_catalogue().products}
        self.assertEqual(shown["g5"].category_text, "Kitchen Appliances > Kettles")
        # g6's title names nothing; its description's first sentence names a kettle.
        self.assertEqual(hints["description"], {"title_gives_none": 1, "description_gives": 1})
        # Words only: no address, no Awin link, in the note.
        self.assertNotIn("example.invalid", repr(intake))
        self.assertNotIn("awin1", repr(intake))


if __name__ == "__main__":
    unittest.main()
