"""The catalogue's brands: the list made each night from the feeds, and what a search makes
of a brand's name (the Decision Contract, "The catalogue's brands").

The owner's series of work, step 3 (2026-11-19 at night; taken up on 2026-11-20: «PicWise:
συνέχισε το βήμα 3, τη λίστα brands, όπως γράφει το handoff»), measured first on a copy of
the server's catalogue (run 44626133872): "samsung" alone showed no product, "samsnug"
nothing, "razer" was read as a razor. The owner's answers of 2026-11-20: «Ερώτηση +
προϊόντα» (a brand alone asks "What kind of Samsung product?" above its products, cheapest
first, no Recommended until a kind is chosen) and «Διόρθωση όταν είναι σίγουρο» (a
misspelled brand is read as it when only it is that close, the page saying "Understood as:
Samsung"; else "Did you mean ...?").

Pinned here:
- one name however a brand is written ("Black & Decker", "Black and Decker"), letters a
  shop's file broke mended ("PokÃ©mon"), the feeds' placeholders no brand;
- the list: brands of 3 products or more, named as most of their products write them,
  their kinds counted, accessories and doubtful kinds aside; carried by the prepared feed;
- a brand's name is never corrected into a kind's ("lampo" is no lamp);
- a brand alone: its products of several kinds under the question, the largest kind
  first, cheapest first and no Recommended; of one kind, with a Recommended and no
  question; the brands whose names begin with it too; never its accessories; a search
  naming a kind alone stays the kind's, though a brand is named so;
- a slip of one brand's name read as it, the page saying so; of two, asked about.

Through the deployed entry point (`api/index.py`) on a feed file. Every row is local test
data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from fixture_support import fixture_description  # noqa: E402
from picwise_nlu.concept_understanding import (  # noqa: E402
    ACCESSORY_MARKER,
    UNCERTAIN_MARKER,
    set_brand_names,
    understand_product_query,
)
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.brand_list import (  # noqa: E402
    BrandReader,
    CatalogueBrand,
    brand_key,
    build_brand_list,
    mend_letters,
)
from picwise_providers.contracts import ProviderProduct  # noqa: E402
from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure, write_prepared_catalogue  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache, prepare_feed_catalogue  # noqa: E402

TVS = "Electronics > Video > Televisions"
MONITORS = "Electronics > Computers > Computer Monitors"
CASES = "Electronics > Communications > Telephony > Mobile Phone Accessories > Mobile Phone Cases"
KETTLES = "Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles"
LAMPS = "Home & Garden > Lighting > Lamps"
INK = "Office Supplies > Ink Cartridges"
TONERS = "Office Supplies > Toner Cartridges"
HEADER = [
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock",
    "merchant_name", "description", "data_provenance", "ean",
]


def _ean(number: int) -> str:
    """A barcode of 13 digits whose check digit agrees."""
    body = f"501{number:09d}"
    total = sum(int(digit) * (3 if place % 2 else 1) for place, digit in enumerate(body))
    return body + str((10 - total % 10) % 10)


# (brand as written, title, shelf, how many, the first price)
_ROWS = (
    ("Fixturon", "Fixturon {n}0 inch 4K Smart TV", TVS, 6, 300.0),
    ("FIXTURON", "Fixturon Curved Monitor {n}", MONITORS, 5, 150.0),
    ("Fixturon UK", "Fixturon Phone Case {n}", CASES, 5, 5.0),
    ("Fixturon Pro", "Fixturon Pro Studio Monitor {n}", MONITORS, 3, 400.0),
    # Read as "lamp" by a correction, before the brands were read as written.
    ("Lampo", "Lampo Electric Kettle {n}", KETTLES, 5, 20.0),
    ("Testline", "Testline Electric Kettle {n}", KETTLES, 5, 22.0),
    ("Brightlux", "Brightlux Table Lamp {n}", LAMPS, 5, 30.0),
    # Two brands one slip apart: a slip of both is asked about.
    ("Brandon", "Brandon Electric Kettle {n}", KETTLES, 3, 25.0),
    ("Brandor", "Brandor Electric Kettle {n}", KETTLES, 3, 26.0),
    # A brand named as the kind ("Kettle Co" is "kettle"): "kettle" stays every kettle.
    ("Kettle Co", "Kettle Co Electric Kettle {n}", KETTLES, 3, 27.0),
    # A brand with its kind: its own cartridges, not the cheaper compatibles naming it;
    # one row with no brand, its title beginning with the brand's name, is its own.
    ("Inkorra", "Inkorra 302 Black Ink Cartridge {n}", INK, 4, 18.0),
    ("Jetfix", "Jetfix Compatible Ink Cartridge for Inkorra 302 Printers {n}", INK, 4, 6.0),
    ("", "Inkorra XL Ink Cartridge {n}", INK, 1, 25.0),
    # A brand whose name other brands' kettles carry, selling one kettle itself.
    ("Rosewell", "Rosewell Electric Kettle {n}", KETTLES, 1, 40.0),
    ("Rosewell", "Rosewell Table Lamp {n}", LAMPS, 2, 35.0),
    ("Testline", "Testline Rosewell Pattern Kettle {n}", KETTLES, 5, 23.0),
    # A brand with few of its own, many compatibles naming it as such: its own only.
    ("Tonexa", "Tonexa TX-200 Black Toner {n}", TONERS, 3, 40.0),
    ("DataMax", "DataMax Tonexa TX-200 Black Toner Compatible {n}", TONERS, 7, 9.0),
)


def _rows() -> list[list[str]]:
    rows = []
    number = 0
    for brand, title, category, count, base in _ROWS:
        for step in range(count):
            number += 1
            rows.append(
                [f"p{number}", title.format(n=step + 1), brand, "", category,
                 f"https://fixture.example.invalid/out/p{number}",
                 f"https://fixture.example.invalid/img/p{number}.jpg", f"{base + step * 7:.2f}", "GBP", "1",
                 "Fixture Store One" if number % 2 else "Fixture Store Two", fixture_description(),
                 "local_test_fixture", _ean(number)]
            )
    return rows


def _product(number: int, brand: str, title: str = "") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title or f"Item {number}",
        brand=brand,
        category_text="",
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text="10.00",
        availability_text="in stock",
        currency="GBP",
        raw={},
    )


class BrandNamesTests(unittest.TestCase):
    def test_one_name_however_a_brand_is_written(self) -> None:
        for written in ("SAMSUNG", "Samsung UK", "Samsung", "samsung ltd"):
            self.assertEqual(brand_key(written), "samsung", written)
        for written in ("Black & Decker", "Black+Decker", "Black and Decker", "BLACK & DECKER"):
            self.assertEqual(brand_key(written), "blackdecker", written)
        self.assertEqual(brand_key("The Rugs"), "rugs")
        self.assertEqual(brand_key("-"), "")

    def test_letters_a_shops_file_broke_are_mended(self) -> None:
        self.assertEqual(mend_letters("PokÃ©mon"), "Pokémon")
        self.assertEqual(mend_letters("Starlight Bedsâ„¢"), "Starlight Beds™")
        # The quote's middle byte is a control character: read as Latin letters.
        self.assertEqual(mend_letters("Johnsonâ\u0080\u0099s"), "Johnson’s")
        for whole in ("Café Fixture", "Samsung", "Pokémon", ""):
            self.assertEqual(mend_letters(whole), whole)
        self.assertEqual(brand_key(mend_letters("PokÃ©mon")), brand_key("Pokémon"))


class BrandListTests(unittest.TestCase):
    def test_the_list_counts_each_brand_once_with_its_kinds(self) -> None:
        rows = [
            ("Fixturon", {"television"}), ("Fixturon", {"television"}), ("FIXTURON", {"television"}),
            ("Fixturon UK", {"monitor"}), ("Fixturon", {"phone_case", ACCESSORY_MARKER}),
            ("Fixturon", {"tablet", UNCERTAIN_MARKER}), ("Fixturon", set()),
            ("CafÃ© Fixture", {"kettle"}), ("Café Fixture", {"kettle"}), ("Café Fixture", {"kettle"}),
            ("Generic", {"kettle"}), ("Generic", {"kettle"}), ("Generic", {"kettle"}),
            ("Tinybrand", {"kettle"}), ("Tinybrand", {"kettle"}),
        ]
        products = [_product(number, brand) for number, (brand, _kinds) in enumerate(rows)]
        brands = {brand.key: brand for brand in build_brand_list(products, [frozenset(kinds) for _brand, kinds in rows])}
        fixturon = brands["fixturon"]
        # Every spelling counted, the name as most products write it.
        self.assertEqual(fixturon.products, 7)
        self.assertEqual(fixturon.name, "Fixturon")
        # Accessories, doubtful kinds and no kind are not counted.
        self.assertEqual(fixturon.kinds, (("television", 3), ("monitor", 1)))
        # Broken letters mended, and one brand with the name written right.
        self.assertEqual(brands["cafefixture"].name, "Café Fixture")
        self.assertEqual(brands["cafefixture"].products, 3)
        # A placeholder is no brand; a brand of fewer than three products is not listed.
        self.assertNotIn("generic", brands)
        self.assertNotIn("tinybrand", brands)


def _reader() -> BrandReader:
    return BrandReader(
        (
            CatalogueBrand("fixturon", "Fixturon", 14, (("monitor", 5), ("television", 6), ("phone_charger", 1))),
            CatalogueBrand("fixturonpro", "Fixturon Pro", 3, (("monitor", 3),)),
            CatalogueBrand("fixturonprofessional", "Fixturon Professional", 4, (("drill", 4),)),
            CatalogueBrand("lampo", "Lampo", 5, (("kettle", 5),)),
            CatalogueBrand("brandon", "Brandon", 3, (("kettle", 3),)),
            CatalogueBrand("brandor", "Brandor", 3, (("kettle", 3),)),
            CatalogueBrand("strong", "Strong", 7, (("glue", 7),)),
            CatalogueBrand("gardenmax", "Gardenmax", 9, (("garden_hose", 9),)),
            CatalogueBrand("karchertesthome", "Karchertest Home", 4, (("pressure_washer", 4),)),
            CatalogueBrand("mirasales", "Mira Sales", 6, (("game_controller", 6),)),
            CatalogueBrand("mystore", "My Store", 5, (("shoes", 5),)),
            CatalogueBrand("besthomegadgets", "Best Home Gadgets", 4, (("toy", 4),)),
            CatalogueBrand("workwearnation", "Workwear Nation Ltd", 9, (("trousers", 5), ("jacket", 4))),
            # A brand named by a word the search knows.
            CatalogueBrand("compass", "Compass", 5, (("backpack", 5),)),
            # A brand whose name begins another's: a slip of the word is of both.
            CatalogueBrand("corvane", "Corvane", 4, (("toy", 4),)),
            CatalogueBrand("corvanecameras", "Corvane Cameras", 8, (("photo_frame", 8),)),
        )
    )


class BrandReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reader = _reader()
        single, several = self.reader.reading_names()
        set_brand_names(single, several)

    def tearDown(self) -> None:
        set_brand_names((), ())

    def test_a_brand_alone_with_the_brands_whose_names_begin_with_it(self) -> None:
        alone = self.reader.read("fixturon").alone
        self.assertIsNotNone(alone)
        self.assertEqual(alone.name, "Fixturon")
        self.assertEqual(set(alone.keys), {"fixturon", "fixturonpro", "fixturonprofessional"})
        self.assertEqual(alone.kinds[0], ("monitor", 8))
        # A word that judges or shops is set aside.
        self.assertEqual(self.reader.read("best fixturon uk").alone.name, "Fixturon")
        # A name of several words, whole.
        self.assertEqual(self.reader.read("fixturon pro").alone.keys, ("fixturonpro",))
        # The leading word of names only, not a brand of its own.
        family = self.reader.read("karchertest").alone
        self.assertEqual(family.name, "Karchertest")
        self.assertEqual(family.keys, ("karchertesthome",))

    def test_a_kind_or_a_word_that_says_how_is_no_brand_alone(self) -> None:
        self.assertIsNone(self.reader.read("strong").alone)
        self.assertIsNone(self.reader.read("kettle").alone)
        self.assertIsNone(self.reader.read("fixturon tv").alone)

    def test_the_choices_are_the_brands_kinds_largest_first(self) -> None:
        alone = self.reader.read("fixturon").alone
        # Fixturon Professional's drills too; the charger is one product, no kind of its own.
        self.assertEqual(alone.choices(), ("fixturon monitor", "fixturon tv", "fixturon drill"))
        self.assertEqual(self.reader.read("lampo").alone.choices(), ())

    def test_a_slip_of_one_brand_is_read_as_it(self) -> None:
        search = self.reader.read("fixtuorn")
        self.assertEqual((search.corrected, search.corrected_to), ("fixturon", "Fixturon"))
        search = self.reader.read("fixtuorn tv")
        self.assertEqual((search.corrected, search.corrected_to), ("fixturon tv", "Fixturon"))
        search = self.reader.read("fixturon profesional")
        self.assertEqual((search.corrected, search.corrected_to), ("fixturon professional", "Fixturon Professional"))

    def test_a_slip_inside_a_name_of_several_words_is_read_as_it(self) -> None:
        # The name's other words are in the search: "mira saels" is Mira Sales.
        search = self.reader.read("mira saels controller")
        self.assertEqual((search.corrected, search.corrected_to), ("mira sales controller", "Mira Sales"))
        self.assertEqual(self.reader.read("my stroe").corrected_to, "My Store")
        # Without them, a word one slip from a word of a name is nothing of it.
        self.assertEqual(self.reader.read("saels").corrected, "")
        # A brand named by a word the search knows: its slip read as it.
        self.assertEqual(self.reader.read("compas").corrected_to, "Compass")
        # One word it could be a slip of, two brands: the name's other words say which.
        search = self.reader.read("corvnae cameras")
        self.assertEqual((search.corrected, search.corrected_to), ("corvane cameras", "Corvane Cameras"))
        self.assertEqual(self.reader.read("corvnae").corrected_to, "Corvane")

    def test_a_name_holding_a_word_that_judges_and_a_name_shown_without_ltd(self) -> None:
        self.assertEqual(self.reader.read("best home gadgets").alone.name, "Best Home Gadgets")
        alone = self.reader.read("workwear nation").alone
        self.assertEqual(alone.name, "Workwear Nation")
        self.assertEqual(alone.choices(), ("workwear nation trousers", "workwear nation jacket"))
        self.assertEqual(self.reader.read("best home gadgtes").corrected_to, "Best Home Gadgets")

    def test_a_slip_of_two_brands_is_asked_about(self) -> None:
        search = self.reader.read("brandox")
        self.assertEqual(search.corrected, "")
        self.assertEqual(search.suggestions, ("brandon", "brandor"))

    def test_a_slip_as_close_to_a_word_the_search_knows_is_asked_about(self) -> None:
        # "gardenmix" is one slip from the brand, and from no word the search knows.
        self.assertEqual(self.reader.read("gardenmix").corrected_to, "Gardenmax")
        # "lamps" is a word the search knows: never read as "lampo".
        self.assertEqual(self.reader.read("lamps").corrected, "")
        # "lampa" is one slip from "lampo" and from "lamps", a kind's name: asked.
        search = self.reader.read("lampa")
        self.assertEqual(search.corrected, "")
        self.assertIn("lampo", search.suggestions)

    def test_a_brands_name_is_never_corrected_into_a_kind(self) -> None:
        self.assertIsNone(understand_product_query("lampo").concept_id)
        reading = understand_product_query("lampo kettle")
        self.assertEqual(reading.concept_id, "kettle")
        self.assertIn("lampo", reading.filters)
        set_brand_names((), ())
        # Without the brands, "lampo" is a slip of "lamp".
        self.assertEqual(understand_product_query("lampo").concept_id, "lamp")


class BrandSearchOnThePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="")
        with handle:
            writer = csv.writer(handle)
            writer.writerow(HEADER)
            writer.writerows(_rows())
        cls.feed = handle.name
        cls.previous = {key: os.environ.pop(key, None) for key in ("AWIN_FEED_FILE", "AWIN_FEED_URL")}
        os.environ["AWIN_FEED_FILE"] = cls.feed
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.pop("AWIN_FEED_FILE", None)
        for key, value in cls.previous.items():
            if value is not None:
                os.environ[key] = value
        os.unlink(cls.feed)
        clear_awin_feed_parse_cache()
        clear_provider_feed_pipeline_cache()
        set_brand_names((), ())

    def _get(self, query: str) -> str:
        captured: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            captured["status"] = status

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/search",
                    "QUERY_STRING": f"q={query}",
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        )
        self.assertEqual(captured["status"], "200 OK")
        return body.decode("utf-8")

    @staticmethod
    def _titles(page: str) -> list[str]:
        return re.findall(r'<h2 title="[^"]*" class="pw-card-title">([^<]*)</h2>', page)

    def test_a_brand_of_several_kinds_asks_which_above_its_products(self) -> None:
        page = self._get("fixturon")
        self.assertIn("Results for: fixturon, cheapest first", page)
        self.assertIn('<span class="pw-kind-choices-ask">What kind of Fixturon product?</span>', page)
        start = page.index('<nav class="pw-kind-choices"')
        choices = page[start:page.index("</nav>", start)]
        # The largest kind first, with Fixturon Pro's monitors counted: 8 monitors, 6 TVs.
        self.assertLess(choices.index("fixturon monitor"), choices.index("fixturon tv"))
        self.assertIn('href="/search?q=fixturon%20tv"', choices)
        self.assertLess(start, page.index('<section class="pw-grid"'))
        # Its products below, cheapest first, the brand's whatever its spelling.
        self.assertEqual(
            self._titles(page),
            ["Fixturon Curved Monitor 1", "Fixturon Curved Monitor 2", "Fixturon Curved Monitor 3",
             "Fixturon Curved Monitor 4"],
        )
        self.assertIn('<p class="pw-results-count">4 of 14</p>', page)
        # No Recommended until a kind is chosen, and nothing said of one.
        self.assertNotIn('<article class="pw-card pw-card-recommended"', page)
        self.assertNotIn("No Recommended here", page)
        # Its accessories are not listed with it; nor is "not sure" said.
        self.assertNotIn("Fixturon Phone Case", page)
        self.assertNotIn("not sure", page)

    def test_each_choice_finds_the_brands_kind(self) -> None:
        page = self._get("fixturon%20tv")
        titles = self._titles(page)
        self.assertTrue(titles)
        self.assertTrue(all("Smart TV" in title for title in titles), titles)
        self.assertNotIn('<nav class="pw-kind-choices"', page)

    def test_a_brand_of_one_kind_shows_its_products_with_a_recommended(self) -> None:
        page = self._get("lampo")
        titles = self._titles(page)
        self.assertTrue(titles and all(title.startswith("Lampo Electric Kettle") for title in titles), titles)
        self.assertIn('<article class="pw-card pw-card-recommended"', page)
        self.assertNotIn('<nav class="pw-kind-choices"', page)
        self.assertNotIn("Table Lamp", page)

    def test_a_kind_named_alone_stays_the_kinds(self) -> None:
        page = self._get("kettle")
        self.assertIn('<p class="pw-results-count">4 of 25</p>', page)

    def test_a_brand_with_its_kind_lists_its_own_products_only(self) -> None:
        # Owner, 2026-11-20: «Μόνο της Canon».
        page = self._get("inkorra%20ink%20cartridge")
        titles = self._titles(page)
        # After the Recommended, the cheapest of its own, not the cheaper compatibles.
        self.assertEqual(titles[1], "Inkorra 302 Black Ink Cartridge 1")
        self.assertFalse(any("Jetfix" in title for title in titles), titles)
        # Its four, and the one with no brand whose title begins with its name.
        self.assertIn('<p class="pw-results-count">4 of 5</p>', page)
        self.assertNotIn("Jetfix", page)

    def test_the_others_naming_a_brand_when_the_search_asks_for_them(self) -> None:
        # Named after "for": the cartridges for Inkorra printers, cheapest first.
        page = self._get("ink%20cartridge%20for%20inkorra")
        self.assertIn('<p class="pw-results-count">4 of 9</p>', page)
        # After the Recommended, the cheapest: the compatibles.
        self.assertTrue(self._titles(page)[1].startswith("Jetfix Compatible Ink Cartridge"), self._titles(page))
        # Asked for compatibles: those.
        page = self._get("inkorra%20compatible%20ink%20cartridge")
        titles = self._titles(page)
        self.assertTrue(titles and all(title.startswith("Jetfix Compatible") for title in titles), titles)

    def test_compatibles_naming_a_brand_are_left_out_however_many(self) -> None:
        # Seven compatibles say they are compatible: the brand's three alone.
        page = self._get("tonexa%20toner")
        self.assertIn('<p class="pw-results-count">3 of 3</p>', page)
        self.assertNotIn("DataMax", page)

    def test_a_brand_word_the_others_carry_most_is_read_as_before(self) -> None:
        # Rosewell sells one kettle; five of another brand carry its name: all six.
        page = self._get("rosewell%20kettle")
        self.assertIn('<p class="pw-results-count">4 of 6</p>', page)

    def test_a_slip_of_one_brand_is_read_as_it_and_said(self) -> None:
        page = self._get("fixtuorn")
        self.assertIn("Results for: fixtuorn, cheapest first  ·  Understood as: Fixturon", page)
        self.assertIn("What kind of Fixturon product?", page)
        page = self._get("fixtuorn%20tv")
        self.assertIn("Understood as: Fixturon", page)
        titles = self._titles(page)
        self.assertTrue(titles and all("Smart TV" in title for title in titles), titles)

    def test_a_slip_of_two_brands_is_asked_about(self) -> None:
        page = self._get("brandox")
        self.assertIn("Did you mean: ", page)
        self.assertIn('<a href="/search?q=brandon">brandon</a>', page)
        self.assertIn('<a href="/search?q=brandor">brandor</a>', page)
        self.assertNotIn('class="pw-card', page)

    def test_the_prepared_feed_carries_the_brands(self) -> None:
        prepared = prepare_feed_catalogue(now=datetime(2026, 11, 20, 3, 0, tzinfo=timezone.utc))
        self.assertIsNotNone(prepared)
        brands = {brand.key: brand for brand in prepared.brands}
        self.assertEqual(brands["fixturon"].products, 16)
        self.assertEqual(brands["fixturon"].kinds[:2], (("television", 6), ("monitor", 5)))
        self.assertIn("lampo", brands)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalogue.json.gz"
            write_prepared_catalogue(prepared, path)
            read = read_prepared_catalogue_to_measure(path)
        self.assertEqual(read.brands, prepared.brands)


if __name__ == "__main__":
    unittest.main()
