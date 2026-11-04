"""A search for a kind shows that kind, not another thing its word names (owner, 2026-11-03).

«Στα tablets .. tablet... Βγάζει και χάπια... Εφόσον το κύριο είδος είναι tablet ... αυτό
πρέπει να συμβαίνει γενικά παντού». On the live site (run 41621931827) "tablet", "tablets"
and "ipad" showed one tablet and eleven toothpaste, mouthwash, electrolyte and supplement
tablets of InStock UK's among their first twelve: their titles name "Tablets", and their
shelves ("Vitamins & Supplements", "Mouthwash", "Toothpaste", "Fish Food") name nothing
PicWise has a kind for, so the title decided. Pinned here:

- a shop's own shelf is looked up among Google's shelves by its name, and the aisle it is
  in says which departments the product may be of (`_shelf_aisles`, `_AISLE_HOLDS`): no
  computer in Health & Beauty, among pet supplies or sweets;
- real tablets keep their kind, on a tablets shelf, an electronics one, a shop's own or
  none;
- the search page: "tablet" and "ipad" list the tablets only.

The titles are the shops' own from the live site and the server's list, or written in
the same shape with fictional brands; every shop is fictional.
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
from picwise_nlu.concept_understanding import UNCERTAIN_MARKER, annotate_product_concepts  # noqa: E402
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402
from test_picwise_offers_first import _COLUMNS, _ean13  # noqa: E402

PILLS = (
    ("Vitamins & Supplements", "Milk Thistle Extract Tablets 4000mg 80% Silymarins High Strength"),
    ("Vitamins & Supplements", "Chromium Picolinate Daily Tablets | Blood Sugar & Daily Support"),
    ("Vitamins & Supplements", "Coconut Oil Biotin Tablets | Hair Beauty & Skin Support"),
    ("Mouthwash", "Eco Natural Mouthwash Tablets - NMT-150L"),
    ("Toothpaste", "Eco Natural Toothpaste Tablets - Charcoal Thyme"),
    ("Sports Nutrition", "EvoSport Electrolyte Daily Tablets | Hydration Energy & Gym"),
    ("Fish Food", "Tetra FunTips Tablets 20 - RSP £1.89"),
    ("Health & Beauty > Health Care > Fitness & Nutrition > Vitamins & Supplements", "Vitamin D3 1000IU 365 Tablets"),
)
TABLETS = (
    ("", "Lenovo Tab M11 Android Tablet 128GB"),
    ("Tablets", "Samsung Galaxy Tab A9+ 11 inch Android Tablet"),
    ("Computers & Tablets", "Fixturon Fire HD 10 Tablet 32GB"),
    ("E-Readers", 'Hannspree Lumo 7.8" Reader Tablet 64GB, Wi-Fi - Black'),
    ("Electronics", "Fixturon 10 inch Android Tablet"),
    ("Electronics > Computers > Tablet Computers", "Testline Pad 11 Tablet 256GB"),
)


def _kinds(category: str, title: str) -> set[str]:
    return set(annotate_product_concepts("", category.lower(), title))


class TheKindsOfTitlesNamingTabletsTests(unittest.TestCase):
    def test_tablets_a_shop_files_under_health_pets_or_sweets_are_no_tablets(self) -> None:
        for category, title in PILLS:
            with self.subTest(category=category, title=title):
                self.assertEqual(_kinds(category, title), {UNCERTAIN_MARKER})

    def test_tablets_stay_tablets(self) -> None:
        for category, title in TABLETS:
            with self.subTest(category=category, title=title):
                self.assertIn("tablet", _kinds(category, title))

    def test_other_homonyms_on_another_aisle(self) -> None:
        # The same rule everywhere: a mouse in a pet-food aisle, a cable among sweets.
        self.assertEqual(_kinds("Cat Food", "Fixturon Catnip Mouse Treats 50g"), {UNCERTAIN_MARKER})
        self.assertEqual(_kinds("Sweets & Chocolate", "Giant Apple Cable"), {UNCERTAIN_MARKER})
        # And the kinds that are what their aisle holds keep it.
        self.assertIn("mouse", _kinds("Computer Accessories", "Fixturon Wireless Optical Mouse"))
        self.assertIn("kettle", _kinds("Small Appliances", "Fixturon 1.7L Electric Kettle"))


class TheTabletSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.get("AWIN_FEED_FILE")
        # A card needs a category that says what the product is: neither none nor
        # "Electronics" alone does (`missing_product_type_or_category_evidence`).
        shown = [(category, title) for category, title in TABLETS if category not in ("", "Electronics")]
        self.expected = [f"t{index}" for index in range(1, len(shown) + 1)]
        rows = [(f"t{index}", title, category, f"{120 + 40 * index}.00")
                for index, (category, title) in enumerate(shown, start=1)]
        rows += [(f"p{index}", title, category, f"{4 + index}.99")
                 for index, (category, title) in enumerate(PILLS, start=1)]
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for number, (pid, title, category, price) in enumerate(rows, start=1):
                writer.writerow([pid, title, title.split()[0], "", category,
                                 f"https://fixture.example.invalid/out/{pid}", f"https://fixture.example.invalid/img/{pid}.jpg",
                                 price, "GBP", "1", "Fixture Store One", "1001", fixture_description(), "local_test_fixture",
                                 _ean13(f"60{number:010d}")])
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

    def _ids(self, query: str) -> list[str]:
        page = b"".join(wsgi_app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/search", "QUERY_STRING": urlencode({"q": query, "shown": "12"}),
             "wsgi.input": io.BytesIO(b""), "wsgi.url_scheme": "https"},
            lambda _status, _headers: None,
        )).decode("utf-8")
        return re.findall(r'<article class="pw-card[^"]*" data-choice-id="[^"]*?(t\d+|p\d+)"', page)

    def test_tablet_and_ipad_list_the_tablets_only(self) -> None:
        for query in ("tablet", "tablets", "ipad"):
            with self.subTest(query=query):
                ids = self._ids(query)
                self.assertTrue(ids)
                self.assertEqual([pid for pid in ids if pid.startswith("p")], [])
                self.assertEqual(sorted(ids), self.expected)


if __name__ == "__main__":
    unittest.main()
