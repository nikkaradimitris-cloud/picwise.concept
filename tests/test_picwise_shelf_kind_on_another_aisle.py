"""A kind the shop's type or shelf names is read against the aisle too (owner, 2026-11-05).

«Πρώτα το 1 μετά το 2», then «Εντάξει, προχώρα με το βήμα 2». The main kind only
(`test_picwise_main_kind_only`) read a title's kind against the aisle the product is filed
in; a shelf can name a kind in another sense as well: "Toners & Astringents" names printer
toner, "Washers" washing machines, "Life Jackets" jackets, "Cake Servers" servers. Measured
on the server's catalogue of 2026-11-05 morning (run 41998750052, part 4): 491 products in
20 kinds. Pinned here (the decision contract, "The main kind only", points 6 and 7):

- a kind the type or the shelf names, on an aisle that may not hold it, gives way to the
  title's own kind when the aisle may hold that one, else the product is doubtful;
- the kinds their aisle holds stay, and riding gloves are gloves;
- the search: "tablet", "jacket" and "mouse" list their kind only, and a search whose
  other words no product of the kind carries finds the doubtful products by their words
  ("vitamin tablets", "life jacket", "sugar mice"); with none to find, the kind's
  products answer and the page says which word it could not match.

The titles are the shops' own from the server's lists, or written in the same shape with
fictional brands; every shop is fictional.
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_nlu.concept_understanding import (  # noqa: E402
    UNCERTAIN_MARKER,
    annotate_product_concepts,
    kinds_before_the_aisle_rule,
)
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from test_picwise_offers_first import _COLUMNS, _ean13  # noqa: E402

# (product type, Google's path, title, the kind the shelf or type gave before)
ANOTHER_SENSE = (
    ("", "Hardware > Hardware Accessories > Hardware Fasteners > Washers",
     "TIMCO Form A Washers – DIN125-A – A2 Stainless Steel – M6 (20 Pack)", "washing_machine"),
    ("Washers", "Hardware > Hardware Accessories > Hardware Fasteners > Washers",
     "TIMCO Form B Washers – DIN125-B – Silver - M16 / 100", "washing_machine"),
    ("", "Health & Beauty > Personal Care > Cosmetics > Skincare > Toners & Astringents",
     "MY PURE SKIN Normalizing Face Toner 150ml", "toner"),
    ("", "Sporting Goods > Outdoor Recreation > Boating & Water Sports > Boating & Water Sport Clothing > Life Jackets",
     "Fit & Float Buoyancy Aid 50N ISO Adult >90kg Red Life Jacket", "jacket"),
    ("", "Home & Garden > Kitchen & Dining > Kitchen Tools & Utensils > Cake Servers", "Cake Slice | Ovenlove", "server"),
    ("", "Media > DVDs & Videos > Film & Television Digital Downloads",
     "Sahaba Stories for Kids | Islamic Digital Learning Pack", "television"),
    ("", "Sporting Goods > Outdoor Recreation > Golf > Golf Ball Markers", "Dartboard Golf Poker Chip Marker", "marker"),
    ("", "Arts & Entertainment > Party & Celebration > Gift Giving > Gift Wrapping > Gift Bags",
     "Christmas character gift bag - medium - Santa", "bag"),
    ("", "Home & Garden > Household Supplies > Household Cleaning Supplies > Cleaning Gloves",
     "Elbow Grease Pink Household Rubber Gloves, 1 Pair - Medium", "gloves"),
    ("", "Health & Beauty > Personal Care > Cosmetics > Cosmetic Tools > Make-up Tools > Face Mirrors",
     "Silver Effect Two Sided Small Shaving Mirror | Mison", "mirror"),
    # A tool backpack is no fashion backpack: found by its words ("tool backpack").
    ("", "Hardware > Hardware Accessories > Tool Storage & Organisation > Tool Bags", "Hultafors Tool Backpack", "backpack"),
)
THEIR_AISLE_HOLDS = (
    ("", "Home & Garden > Household Appliances > Laundry Appliances > Washing Machines",
     "Fixturon 9kg 1400 Spin Washing Machine White", "washing_machine"),
    ("", "Electronics > Video > Televisions", "Fixturon 55 inch 4K Smart TV", "television"),
    ("", "Clothing & Accessories > Clothing > Outerwear > Coats & Jackets", "Fixturon Womens Puffer Jacket Black", "jacket"),
    ("", "Office Supplies > Office Instruments > Writing & Drawing Instruments > Markers & Highlighters",
     "Fixturon Permanent Marker Black 12 Pack", "marker"),
    ("", "Electronics > Video > Computer Monitors", "Fixturon 27 inch IPS Monitor 1440p", "monitor"),
    ("", "Luggage & Bags > Backpacks", "Fixturon School Backpack 20L Navy", "backpack"),
    ("", "Clothing & Accessories > Handbags, Wallets & Cases > Handbags", "Fixturon Leather Shoulder Bag Tan", "handbag"),
    ("Laptops", "Electronics > Computers > Laptops", "Fixturon 15.6 inch Laptop 16GB", "laptop"),
    ("Tablets", "", "Fixturon 10 inch Android Tablet", "tablet"),
    ("", "Mobile Phone Cases", "Fixturon Clear Case for Phone 15", "phone_case"),
    # Riding clothing holds its accessories: riding gloves are gloves.
    ("", "Sporting Goods > Outdoor Recreation > Equestrian > Riding Clothing & Accessories",
     "Fixturon Riding Gloves Black - Large", "gloves"),
)


class TheShelfsKindTests(unittest.TestCase):
    def test_a_type_or_shelf_naming_a_kind_in_another_sense_is_doubtful(self) -> None:
        for product_type, category, title, before in ANOTHER_SENSE:
            with self.subTest(category=category, title=title):
                self.assertEqual(
                    set(annotate_product_concepts(product_type, category.lower(), title)), {UNCERTAIN_MARKER}
                )
                # The build's note reads the kind the rule took away.
                self.assertIn(before, kinds_before_the_aisle_rule(product_type, category.lower(), title))

    def test_the_kinds_their_aisle_holds_stay(self) -> None:
        for product_type, category, title, kind in THEIR_AISLE_HOLDS:
            with self.subTest(category=category, title=title):
                self.assertIn(kind, annotate_product_concepts(product_type, category.lower(), title))


# (id, title, Google's path or a shop's shelf, price)
CATALOGUE = (
    ("a1", "Fixturon 10 inch Android Tablet 64GB", "Electronics > Computers > Tablet Computers", "89.00"),
    ("a2", "Testline Pad 11 Tablet 128GB", "Electronics > Computers > Tablet Computers", "129.00"),
    ("p1", "EvoSport Electrolyte Daily Tablets | Hydration Energy & Gym Support", "Vitamins & Supplements", "3.15"),
    ("p2", "Vitamin D3 1000IU 365 Tablets",
     "Health & Beauty > Health Care > Fitness & Nutrition > Vitamins & Supplements", "4.99"),
    ("j1", "Fixturon Womens Puffer Jacket Black", "Clothing & Accessories > Clothing > Outerwear > Coats & Jackets", "55.00"),
    ("j2", "Fixturon Mens Quilted Jacket Navy", "Clothing & Accessories > Clothing > Outerwear > Coats & Jackets", "62.00"),
    ("l1", "Fit & Float Buoyancy Aid 50N Adult Red Life Jacket",
     "Sporting Goods > Outdoor Recreation > Boating & Water Sports > Boating & Water Sport Clothing > Life Jackets",
     "29.99"),
    ("l2", "Fixturon Child Life Jacket 30-40kg Yellow",
     "Sporting Goods > Outdoor Recreation > Boating & Water Sports > Boating & Water Sport Clothing > Life Jackets",
     "24.99"),
    ("x1", "Fixturon Wireless Optical Mouse",
     "Electronics > Electronics Accessories > Computer Components > Input Devices > Mice & Trackballs", "9.99"),
    ("s1", "Sugar mice", "Sweets & Chocolate", "0.30"),
    ("f1", "Fixturon 16 inch Desk Fan White",
     "Home & Garden > Household Appliances > Climate Control Appliances > Fans > Desk & Pedestal Fans", "19.99"),
    ("e1", "Premade Angel Lashes 5D Closed Fans 16 Row Single Length Trays", "False Eyelashes", "6.25"),
)


class TheWordsSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.get("AWIN_FEED_FILE")
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for number, (pid, title, category, price) in enumerate(CATALOGUE, start=1):
                writer.writerow([pid, title, title.split()[0], "", category,
                                 f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                                 price, "GBP", "1", "Fixture Store One", "1001", fixture_description(), "local_test_fixture",
                                 _ean13(f"62{number:010d}")])
        os.environ["AWIN_FEED_FILE"] = str(path)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop("AWIN_FEED_FILE", None)
        else:
            os.environ["AWIN_FEED_FILE"] = self._previous
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    def _page(self, query: str) -> tuple[list[str], str]:
        page = b"".join(wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/search", "QUERY_STRING": urlencode({"q": query, "shown": "12"}),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            lambda _status, _headers: None,
        )).decode("utf-8")
        ids = re.findall(r'<article class="pw-card[^"]*" data-choice-id="[^"]*?([a-z]\d)"', page)
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script).*?</\1>", " ", page, flags=re.S)))
        return ids, text

    def test_a_search_for_a_kind_lists_that_kind_only(self) -> None:
        for query, expected in (("tablet", {"a1", "a2"}), ("jacket", {"j1", "j2"}), ("mouse", {"x1"}), ("fan", {"f1"})):
            with self.subTest(query=query):
                ids, _text = self._page(query)
                self.assertEqual(set(ids), expected)

    def test_words_no_product_of_the_kind_carries_find_the_doubtful_ones(self) -> None:
        for query, expected in (
            ("vitamin tablets", {"p2"}),
            ("electrolyte tablets", {"p1"}),
            ("life jacket", {"l1", "l2"}),
            ("sugar mice", {"s1"}),
            ("lash fans", {"e1"}),
        ):
            with self.subTest(query=query):
                ids, text = self._page(query)
                self.assertEqual(set(ids), expected)
                self.assertIn(f"Results for: {query}", text)
                self.assertNotIn("could not match", text)

    def test_a_corrected_search_found_by_its_words_names_no_kind(self) -> None:
        # "jaket" is read as jacket through a correction; the life jackets its words find
        # are no jackets, so the page does not say it understood a jacket.
        ids, text = self._page("life jaket")
        self.assertEqual(set(ids), {"l1", "l2"})
        self.assertNotIn("Understood as", text)
        # A corrected search answered by its kind still says what it was read as.
        ids, text = self._page("puffer jaket")
        self.assertEqual(ids, ["j1"])
        self.assertIn("Understood as: jacket", text)

    def test_with_no_doubtful_product_to_find_the_kind_answers_and_says_so(self) -> None:
        # No product carries "eyelash": the desk fan, and the word it could not match.
        ids, text = self._page("eyelash fans")
        self.assertEqual(ids, ["f1"])
        self.assertIn("could not match: eyelash", text)


if __name__ == "__main__":
    unittest.main()
