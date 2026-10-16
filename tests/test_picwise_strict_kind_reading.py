"""The kind asked for, and only that: the strict kind reading of 2026-10-16.

Owner rule, in their words: «το laptop πρέπει να βγάζει laptop». Measured on the third
real Awin feed (42,076 products, 2026-10-16): the right kind was understood for 109 of
118 English searches, but only 80 showed four right products, because the kind of a
feed row was read too loosely. Tablet casings answered "tablet", desk trays "desk",
label makers "printer", fan speed controllers and PC case fans "fan", UPS replacement
batteries "ups battery backup", temperature sensors titled "Monitor" "monitor", and dog
sofa beds "corner sofa bed". Price order makes this worse, not better: the cheapest
products of any kind are its accessories and look-alikes, so every loose reading is a
wrong card at the top of the page.

Every row is written with fictional brands, in the shape the real feed used. The page
tests are served through api/index.py, the deployed entry point, with `.invalid` URLs.
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
    ACCESSORY_MARKER,
    CAMPING_MARKER,
    CATEGORY_FIELD_SEPARATOR,
    PET_MARKER,
    UNCERTAIN_MARKER,
    annotate_product_concepts,
    understand_product_query,
)
from picwise_providers.awin_adapter import clear_awin_feed_parse_cache  # noqa: E402
from picwise_providers.state import clear_provider_feed_pipeline_cache  # noqa: E402


def _kinds(product_type: str = "", category: str = "", title: str = "") -> set[str]:
    return set(annotate_product_concepts(product_type, category, title))


class ClassificationLastWordTests(unittest.TestCase):
    """A feed's own type or shelf names its product by its last words."""

    def test_an_accessory_word_at_the_end_of_a_type_is_the_product(self) -> None:
        for product_type, title in (
            ("Tablet Cases", "Fixturon Breeze Folio for Tablet Air 11\" (Black)"),
            ("Tablet Security Enclosures", "Fixturon WL15 Tablet casing - 10.9-11\""),
            ("Desk Trays/Organizers", "Testline KF217 desk tray/organizer Plastic Black"),
            ("Desk Drawer Organizers", "Testline Under-Desk Drawer"),
            ("Fan Speed Controllers", "Sampleworks ARGB FAN CONTROLLER fan speed controller"),
            ("UPS Batteries", "Fixturon Replacement UPS Battery Cartridge RBC2"),
            ("Toner Collectors", "Testline MC-20 Maintenance Cartridge"),
            ("Printer Ribbons", "Sampleworks ERC05B Ribbon Cartridge for M-150, black"),
        ):
            with self.subTest(product_type=product_type):
                self.assertEqual(_kinds(product_type, "", title), {ACCESSORY_MARKER})

    def test_last_words_that_name_a_kind_are_that_kind(self) -> None:
        self.assertEqual(
            _kinds("Mobile Phone Cases", "", "Fixturon Evo mobile phone case 17 cm (6.7\") Cover"),
            {"phone_case"},
        )
        self.assertEqual(
            _kinds("Mobile Phone Screen & Back Protectors", "",
                   "Testline GLASS-X5 mobile phone screen/back protector"),
            {"screen_protector"},
        )
        self.assertEqual(
            _kinds("Laptop Docks & Port Replicators", "",
                   "Sampleworks C605A laptop dock/port replicator Wired USB 3.2"),
            {"docking_station"},
        )
        self.assertEqual(
            _kinds("Label Printers", "", "Fixturon LT-200B Bluetooth Label Maker | Label Printer"),
            {"label_printer"},
        )

    def test_a_list_of_one_word_kinds_is_still_read_part_by_part(self) -> None:
        self.assertEqual(_kinds("Fans & Heaters", "", "Testline Tower Fan 30 inch"), {"fan"})
        self.assertEqual(_kinds("Fans & Heaters", "", "Testline 2000W Fan Heater"), {"heater"})

    def test_a_product_title_listing_a_battery_is_still_the_product(self) -> None:
        # Only a classification is read by its last word; a title lists specs.
        self.assertEqual(
            _kinds("Smartphones", "",
                   "Fixturon Nova A17 6.7\" Smartphone (NV-A17) - 128GB, 5000mAh battery"),
            {"smartphone"},
        )


class UnknownKindLabelTests(unittest.TestCase):
    """A feed type that names a kind PicWise does not know is not overruled by a title."""

    def test_a_kind_label_the_lexicon_lacks_is_not_replaced_by_the_title(self) -> None:
        for product_type, title in (
            ("Temperature & Humidity Sensors", "Fixturon Smart Temperature & Humidity Monitor"),
            ("Networking Software", "Testline DXS-36 networking software Switch / Router 1 license"),
            ("Servers", "Sampleworks ProServe DL325 24c 64GB 8SFF 2x480GB SSD"),
            ("Photo Paper", "Fixturon MP-101 Matte Photo Paper A4 - 50 Sheets"),
        ):
            with self.subTest(product_type=product_type):
                self.assertEqual(_kinds(product_type, "", title), {UNCERTAIN_MARKER})

    def test_a_type_sharing_a_real_word_with_the_title_lets_the_title_decide(self) -> None:
        self.assertEqual(
            _kinds("USB Flash Drives", "", "Testline Extreme USB flash drive 128 GB USB Type-A"),
            {"storage_drive"},
        )
        self.assertEqual(
            _kinds("Computer Cooling Systems", "", "Sampleworks Light Wings 140mm PWM Case Fan Black"),
            {"pc_cooling"},
        )

    def test_a_department_or_device_name_as_type_lets_the_title_decide(self) -> None:
        self.assertIn("robot_vacuum", _kinds("Home", "", "Fixturon Robot Vacuum Cleaner S5"))
        self.assertIn("phone_case", _kinds("iPhone XR", "accessories", "Fixturon iPhone XR Case"))


class TitleLeadTests(unittest.TestCase):
    """The title's own lead -- before "(", ",", " - ", "+", "with", "for" -- is heard."""

    def test_a_title_naming_the_kind_only_to_say_what_it_is_for_is_doubtful(self) -> None:
        self.assertEqual(
            _kinds("Toner Cartridges", "", "Fixturon Color LaserJet B5L37A Toner Collection Unit"),
            {UNCERTAIN_MARKER},
        )
        self.assertEqual(
            _kinds("Standing Desks", "", "Testline Ergo Standing Desk Converter with sliding tray"),
            {UNCERTAIN_MARKER},
        )

    def test_specs_after_the_lead_do_not_change_the_product(self) -> None:
        self.assertEqual(
            _kinds("Laptops", "",
                   "Fixturon Vantage L13 13.3\" Laptop (21LB003) - Core Ultra 5, 16GB RAM, 512GB SSD"),
            {"laptop"},
        )
        self.assertEqual(_kinds("Laptops", "", "Testline 14 Laptop Celeron 4GB 64GB SSD Silver"), {"laptop"})
        # A model name after the kind ("Tablet Air") is not another product.
        self.assertEqual(_kinds("Tablets", "", "Sampleworks Tablet Air 5G M4 512 GB 27.9 cm (11\")"), {"tablet"})
        self.assertEqual(
            _kinds("Headphones & Headsets", "", "Testline Voyager 4310 USB-C Headset +BT700 Adapter"),
            {"headphones"},
        )

    def test_a_misfiled_shelf_gives_way_to_the_title_of_the_same_department(self) -> None:
        kinds = _kinds("", "furniture > chairs > chaises",
                       "Fixturon 3 Seater Sofa with Lift-Up Storage, 228cm Velvet Couch")
        self.assertIn("sofa", kinds)
        self.assertNotIn("chair", kinds)

    def test_a_precise_type_is_not_overruled_by_the_device_its_title_names(self) -> None:
        kinds = _kinds("Mobile Device Chargers", "",
                       "Fixturon Boost Charge Smartphone Black Cigar lighter Auto")
        self.assertEqual(kinds, {UNCERTAIN_MARKER})

    def test_another_department_in_the_title_is_context_not_contradiction(self) -> None:
        self.assertIn(
            "garden_furniture",
            _kinds("", "home & garden > outdoor furniture > outdoor furniture sets",
                   "Testline 8-Seater Outdoor Rattan Sofa Set Conversation Set"),
        )


class ContextTests(unittest.TestCase):
    """Pet and camping products carry their context."""

    def test_pet_and_camping_products_are_marked(self) -> None:
        dog = _kinds("", "animals & pet supplies > pet supplies > dog supplies > dog beds",
                     "Fixturon Dog Sofa Bed, Washable Pet Bed with Removable Cover")
        self.assertIn(PET_MARKER, dog)
        cot = _kinds("", "sporting goods > outdoor recreation > camping & hiking > camp furniture",
                     "Testline Double Camping Cot Bed, with Bag - Black")
        self.assertIn(CAMPING_MARKER, cot)
        tent = _kinds("", "sporting goods > outdoor recreation > camping & hiking > tents",
                      "Sampleworks 2-Person Camping Tent: Portable with Zip Doors")
        self.assertIn("tent", tent)

    def test_a_cushion_shelf_holds_cushions_not_chairs(self) -> None:
        self.assertEqual(
            _kinds("", "home & garden > decor > chair & sofa cushions",
                   "Fixturon Chair Shield: Waterproof Outdoor Furniture Cover"),
            {ACCESSORY_MARKER},
        )


class QueryReadingTests(unittest.TestCase):
    """A word that says which type of the product the buyer wants stays a filter."""

    def test_type_words_are_filters_not_part_of_the_name(self) -> None:
        for query, concept, word in (
            ("floor lamp", "lamp", "floor"),
            ("dining table", "table", "dining"),
            ("laser printer", "printer", "laser"),
            ("gaming chair", "chair", "gaming"),
            ("ceiling fan", "fan", "ceiling"),
            ("standing desk", "desk", "standing"),
        ):
            with self.subTest(query=query):
                reading = understand_product_query(query)
                self.assertEqual(reading.concept_id, concept)
                self.assertIn(word, reading.filters)

    def test_new_kinds_are_their_own(self) -> None:
        self.assertEqual(understand_product_query("sofa bed").concept_id, "sofa_bed")
        self.assertEqual(understand_product_query("corner sofa bed").concept_id, "sofa_bed")
        self.assertEqual(understand_product_query("label printer").concept_id, "label_printer")
        self.assertEqual(understand_product_query("case fan").concept_id, "pc_cooling")
        for query, concept in (
            ("ip phone", "desk_phone"),
            ("conference phone", "desk_phone"),
            ("phone", "mobile_phone"),
            ("foosball table", "game_table"),
            ("play tent", "play_tent"),
            ("shower chair", "shower_seat"),
            ("raised garden bed", "flower_pot"),
            ("greenhouse", "greenhouse"),
        ):
            with self.subTest(query=query):
                self.assertEqual(understand_product_query(query).concept_id, concept)


class PhoneKindTests(unittest.TestCase):
    """Owner's rule of 2026-10-16: «Smartphone να δείχνεις smartphone... Τα υπόλοιπα
    είναι mobile phone», and "mobile phone", «κινητό» and "phone" show only those."""

    def test_the_title_says_which_phone_a_mobile_phones_type_holds(self) -> None:
        for title in (
            "Fixturon CORE-S5 2.4\" Mobile Phone (1001) - Black",
            "Testline Leva E22 2.8\" Flip Phone (8992) - Red",
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("Mobile Phones", "", title), {"mobile_phone"})
        for title in (
            "Sampleworks Pulse 5G Smartphone 128GB",
            "Fixturon Wave 256GB Blue",
            "Testline Nova 6.5\" Dual SIM Black",
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("Mobile Phones", "", title), {"smartphone"})
        self.assertEqual(
            _kinds("Smartphones", "", "Sampleworks K70 SE 6.56\" 4G Smartphone"), {"smartphone"}
        )

    def test_queries_name_one_phone_or_the_other(self) -> None:
        for query, concept in (
            ("smartphone", "smartphone"),
            ("smart phone", "smartphone"),
            ("unlocked android phone", "smartphone"),
            ("mobile phone", "mobile_phone"),
            ("cell phone", "mobile_phone"),
            ("phone", "mobile_phone"),
            ("κινητό", "mobile_phone"),
            ("flip phone", "mobile_phone"),
            ("phone case", "phone_case"),
        ):
            with self.subTest(query=query):
                self.assertEqual(understand_product_query(query).concept_id, concept)


def _crumbs(*fields: str) -> str:
    """Several category fields of one feed row, joined the way the search joins them."""
    return CATEGORY_FIELD_SEPARATOR.join(fields)


class LookAlikeKindTests(unittest.TestCase):
    """Kinds that share words with a common kind, from the cheapest products of each kind
    on the third feed (2026-10-16): IP phones answered "smartphone", printer labels and
    drums "printer", raised garden beds "bed", a foosball table "table", a kids' play tent
    "tent", a shower seat "chair", a grow tent "tent", weight plates "plates"."""

    def test_desk_phones_are_not_smartphones(self) -> None:
        self.assertEqual(_kinds("IP Phones", "", "Fixturon Edge B10 IP Phone with Power Supply"), {"desk_phone"})
        self.assertEqual(
            _kinds("Conference Phones", "", "Testline Trio C60 IP Conference Phone for Teams"),
            {"desk_phone"},
        )
        # A title saying only "Phone" agrees with the IP phones type, it does not contradict it.
        self.assertEqual(
            _kinds("IP Phones", "", "Sampleworks IP Business Phone 7821, 3.5-inch Greyscale Display"),
            {"desk_phone"},
        )

    def test_printer_supplies_are_not_printers(self) -> None:
        for product_type, title in (
            ("Printer Labels", "Fixturon Premium Matte Label - Continuous Roll: 76mm x 35m"),
            ("Printer Drums", "Testline 44318506 printer drum Original 1 pc(s)"),
            ("Printer Cleaning", "Sampleworks printer cleaning kit"),
        ):
            with self.subTest(product_type=product_type):
                self.assertEqual(_kinds(product_type, "", title), {ACCESSORY_MARKER})
        self.assertEqual(
            _kinds("Laser Printers", "", "Fixturon HL-L5210DW laser printer 1200 x 1200 DPI A4 Wi-Fi"),
            {"printer"},
        )

    def test_garden_game_play_and_bath_kinds_are_their_own(self) -> None:
        self.assertEqual(
            _kinds("", _crumbs("garden & outdoor > garden planters & stands > pots & planters",
                               "home & garden > lawn & garden > gardening > pots & planters"),
                   "Fixturon Wooden Raised Garden Bed, 120 x 50 x 45cm Elevated Planter Box"),
            {"flower_pot"},
        )
        self.assertEqual(
            _kinds("", "sports & leisure > game room > game tables",
                   "Testline 20 in Table-top Football Table with Stainless Steel Rods"),
            {"game_table"},
        )
        self.assertEqual(
            _kinds("", "play tents", "Sampleworks Indoor Kids Play Tent Yellow Grid Teepee Tent"),
            {"play_tent", "toy"},
        )
        # A camping tipi is still a tent.
        self.assertIn(
            "tent",
            _kinds("", "camping > tents", "Fixturon 6 Man Tipi Tent, Camping Teepee Family Tent"),
        )
        self.assertEqual(
            _kinds("", "health & beauty > mobility aids & equipment > shower seats",
                   "Testline Swivel Shower Seat, Adjustable Height, Safe Support Chair for Home"),
            {"shower_seat"},
        )
        self.assertEqual(
            _kinds("", "garden & outdoor > garden buildings > greenhouse > grow tents",
                   "Sampleworks Fruit Cage Bird Netting, Plant Protection Tent with Zipped Door"),
            {"greenhouse"},
        )
        self.assertEqual(
            _kinds("", "sports & leisure > strength training > barbells & weight plates",
                   "Fixturon 4 PCS Olympic Weight Plates Grip Plate Sets for Strength"),
            {"barbell"},
        )


class TypeListAndEndingTests(unittest.TestCase):
    """What a feed type lists, and the noun it ends in, bound what its titles can say."""

    def test_a_type_listing_an_unknown_kind_needs_the_title_to_name_the_known_one(self) -> None:
        self.assertEqual(
            _kinds("Industrial Environmental Sensors & Monitors", "", "Fixturon USL-Environmental Multisensor"),
            {UNCERTAIN_MARKER},
        )
        self.assertEqual(
            _kinds("Power Adapters & Inverters", "", "Testline 65W USB-C Power Adapter"), {"phone_charger"}
        )
        self.assertEqual(
            _kinds("Power Adapters & Inverters", "",
                   "Sampleworks 4X20S56721 power adapter/inverter Indoor 230 W Black"),
            {"phone_charger"},
        )
        self.assertEqual(
            _kinds("Power Adapters & Inverters", "", "Fixturon 300W Power Inverter with USB Charger"),
            {UNCERTAIN_MARKER},
        )
        self.assertIn(
            "car_charger",
            _kinds("Power Adapters & Inverters", "", "Testline 100W USB-C Car charger with self adjusting output"),
        )

    def test_a_type_ending_in_an_accessory_word_is_not_the_kind_its_title_names(self) -> None:
        self.assertEqual(
            _kinds("Storage Drive Enclosures", "", "Fixturon 2.5in SATA SSD/HDD Enclosure"), {UNCERTAIN_MARKER}
        )
        self.assertEqual(_kinds("Equipment Cases", "", "Testline 1510 Protector Case"), {UNCERTAIN_MARKER})
        self.assertEqual(_kinds("Chair Back Supports", "", "Sampleworks Ergo Back Support"), {ACCESSORY_MARKER})
        # Unless that noun is the kind's own name.
        self.assertEqual(
            _kinds("Gaming Controllers", "", "Fixturon Wolverine V3 Pro Black USB Gamepad"),
            {"game_controller"},
        )


class CategoryFieldTests(unittest.TestCase):
    """Each category field of a feed row is its own breadcrumb."""

    def test_the_shops_own_path_speaks_before_the_networks_aisle(self) -> None:
        self.assertEqual(
            _kinds("", _crumbs("home goods > bathroom furniture > laundry > tumble dryers",
                               "home & garden > bathroom accessories", "bathrooms & accessories"),
                   "Fixturon 4kg Vented Tumble Dryer with Smart Mode"),
            {"tumble_dryer"},
        )
        self.assertEqual(
            _kinds("", _crumbs("home goods > hallway furniture > console tables",
                               "home & garden > household supplies > storage & organisation"),
                   "Testline Console Table Modern Sofa Side Desk with Storage Shelves"),
            {"table"},
        )

    def test_a_product_misfiled_into_another_department_is_doubtful(self) -> None:
        self.assertEqual(
            _kinds("", _crumbs("toys & games > baby products > baby nursery furniture",
                               "furniture > baby & toddler furniture > changing tables"),
                   "Fixturon I-Size Booster Seat with ISOFIX, Car Seat with Washable Cover"),
            {UNCERTAIN_MARKER},
        )
        # An aisle-like kind holds other departments' products: these stay where filed.
        self.assertIn(
            "toy", _kinds("", "toys & games > outdoor toys > ride ons", "Testline Kids Scooter with Height-Adjustable Handlebar")
        )
        self.assertIn(
            "garden_furniture",
            _kinds("", "garden & outdoor > garden furniture > garden tables",
                   "Sampleworks Metal Square Outdoor Garden Bistro Table Black"),
        )

    def test_a_kind_inside_the_heads_phrase_only_describes_it_on_a_shelf(self) -> None:
        self.assertEqual(
            _kinds("", "home goods > kids furniture > kids desks",
                   "Fixturon 2 PCS Kids Desk Chairs, 3 Level Height Adjustable"),
            {"chair"},
        )
        # A product type puts the type first and a feature after it.
        self.assertEqual(
            _kinds("Keyboards", "", "Testline WKB-1320CB keyboard Mouse included Home RF Wireless QWERTY"),
            {"keyboard"},
        )


class TitleFallbackTests(unittest.TestCase):
    """A title read when neither the type nor the category names a kind."""

    def test_w_slash_is_with(self) -> None:
        kinds = _kinds(
            "",
            _crumbs("seasonal > christmas trees > tabletop christmas trees",
                    "home & garden > decor > seasonal & holiday decorations"),
            "Fixturon 2FT Pre-lit Artificial Christmas Tree Tabletop Fibre Optic Xmas Decoration "
            "w/ LED Lights Pot Table Desk - Green",
        )
        self.assertFalse(kinds & {"desk", "table", "cookware"})

    def test_a_lead_naming_a_kind_in_passing_is_doubtful(self) -> None:
        for category, title in (
            ("home goods > home furniture", "Testline Bamboo Sofa Arm Tray, Foldable Anti-Slip Armrest Tray"),
            ("home goods > hallway furniture > coat racks & stands",
             "Fixturon Wall-Mounted Coat Rack: 4 Hooks, Rail & Shelf for Hallway"),
            (_crumbs("garden & outdoor > garden buildings > garden sheds", "home & garden > lawn & garden"),
             "Sampleworks 8 x 6.5 ft Outdoor Garden Storage Shed, Waterproof Bike Tent w/ Zipper Door"),
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("", category, title), {UNCERTAIN_MARKER})

    def test_a_later_plain_name_still_says_what_the_product_is(self) -> None:
        self.assertEqual(
            _kinds("", "", "Testline Eco Friendly Rattan Pendant Light Handwoven Rustic Farmhouse Ceiling Light"),
            {"lamp"},
        )
        self.assertEqual(_kinds("", "", "Fixturon X200, Wireless Gaming Mouse, Black"), {"mouse"})

    def test_a_lead_ending_in_an_accessory_noun_is_that_accessory(self) -> None:
        # The cheapest "tablet", "toy" and "bed" on the third feed, filed by type or shelf.
        self.assertEqual(
            _kinds("Tablets", "", "Fixturon Tab 11\" Folio Case - Grey (Grade A - Good)"), {ACCESSORY_MARKER}
        )
        self.assertEqual(
            _kinds("", "toys & games > outdoor toys", "Testline Sandbox Cover, Square Sandpit Cover Waterproof"),
            {ACCESSORY_MARKER},
        )
        self.assertEqual(
            _kinds("", "toys & games > outdoor toys", "Sampleworks 4Pcs Trampoline Anchor Kit, 32 cm Stakes"),
            {ACCESSORY_MARKER},
        )
        self.assertEqual(
            _kinds("", "home goods > bedroom furniture > beds", "Fixturon Safety Bed Rail, Height Adjustable"),
            {UNCERTAIN_MARKER},
        )
        # A lead that names the kind itself is read word by word: the watch's own case.
        self.assertIn(
            "watch",
            _kinds("Smartwatches", "",
                   "Testline Watch Series 11 GPS 42mm Jet Black Aluminium Case with Black Sport Band"),
        )
        self.assertEqual(_kinds("", "toys & games > musical toys", "Sampleworks Kids Drum Kit with Stool"), {"toy"})

    def test_an_accessory_named_after_the_product_is_an_accessory(self) -> None:
        self.assertEqual(
            _kinds("", "toys & games > toys for kids > musical toys & instruments",
                   "Sampleworks Studio Microphone Isolation Shield with Pop Filter and Tripod Stand"),
            {ACCESSORY_MARKER},
        )
        # "Tray" on a processor is its packaging, not an accessory.
        self.assertEqual(
            _kinds("Processors", "", "Testline Core i3-12100 processor 12 MB Smart Cache Tray"), {"processor"}
        )


_COLUMNS = (
    "aw_product_id", "product_name", "brand_name", "product_type", "merchant_category",
    "aw_deep_link", "aw_image_url", "search_price", "currency", "in_stock", "merchant_name",
    "description", "data_provenance", "merchant_product_category_path",
)


class StrictKindPageTests(unittest.TestCase):
    """The page shows the kind asked for, and nothing that only resembles it."""

    def _serve(self, rows: list[tuple[str, ...]]) -> None:
        path = Path(tempfile.mkdtemp()) / "feed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(_COLUMNS)
            for pid, title, product_type, category, price, *shop_path in rows:
                writer.writerow(
                    [pid, title, title.split()[0], product_type, category,
                     f"https://fixture.example.invalid/out/{pid}",
                     f"https://fixture.example.invalid/img/{pid}.jpg", price, "GBP", "1",
                     "Fixture Store One", fixture_description(), "local_test_fixture",
                     shop_path[0] if shop_path else ""]
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

        self.addCleanup(restore)

    def _shown(self, query: str) -> list[str]:
        def start_response(_status: str, _headers: list[tuple[str, str]]) -> None:
            return None

        body = b"".join(
            wsgi_app(
                {
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": "/search",
                    "QUERY_STRING": urlencode({"q": query}),
                    "wsgi.input": io.BytesIO(b""),
                    "wsgi.url_scheme": "https",
                },
                start_response,
            )
        ).decode("utf-8")
        return re.findall(r'<article class="pw-card[^"]*" data-choice-id="([^"]+)"', body)

    def test_tablet_casings_never_answer_tablet(self) -> None:
        self._serve(
            [
                ("t1", "Fixturon Tab 10 Tablet 64GB", "Tablets", "Computers", "149.00"),
                ("t2", "Testline Slate 11 Tablet 128GB", "Tablets", "Computers", "249.00"),
                ("t3", "Sampleworks Pad Pro 12 Tablet 256GB", "Tablets", "Computers", "449.00"),
                ("t4", "Fixturon Tab Mini 8 Tablet 32GB", "Tablets", "Computers", "99.00"),
                ("c1", "Testline WL15 Tablet casing - 10.9-11\"", "Tablet Security Enclosures", "Computers", "37.99"),
                ("c2", "Sampleworks Folio for Tablet Air 11\"", "Tablet Cases", "Computers", "19.99"),
            ]
        )
        shown = self._shown("tablet")
        self.assertEqual(sorted(shown), ["t1", "t2", "t3", "t4"])

    def test_a_plain_bed_search_shows_no_pet_or_camping_beds_and_dog_bed_does(self) -> None:
        self._serve(
            [
                ("b1", "Fixturon Double Bed Frame Oak", "", "furniture > beds", "199.00"),
                ("b2", "Testline King Size Bed Frame Grey", "", "furniture > beds", "299.00"),
                ("b3", "Sampleworks Single Bed Frame White", "", "furniture > beds", "149.00"),
                ("b4", "Fixturon Storage Bed Frame Double", "", "furniture > beds", "349.00"),
                ("d1", "Testline Elevated Dog Bed Grey", "", "animals & pet supplies > pet supplies > dog supplies > dog beds", "25.99"),
                ("d2", "Sampleworks Dog Bed Washable", "", "animals & pet supplies > pet supplies > dog supplies > dog beds", "19.99"),
                ("d3", "Fixturon Calming Dog Bed Round", "", "animals & pet supplies > pet supplies > dog supplies > dog beds", "29.99"),
                ("d4", "Testline Orthopaedic Dog Bed Large", "", "animals & pet supplies > pet supplies > dog supplies > dog beds", "39.99"),
                ("k1", "Sampleworks Double Camping Cot Bed, with Bag", "", "sporting goods > outdoor recreation > camping & hiking > camp furniture", "51.99"),
            ]
        )
        self.assertEqual(sorted(self._shown("bed")), ["b1", "b2", "b3", "b4"])
        self.assertEqual(sorted(self._shown("dog bed")), ["d1", "d2", "d3", "d4"])

    def test_label_makers_answer_label_printer_not_printer(self) -> None:
        self._serve(
            [
                ("p1", "Fixturon OfficeJet 9125 Wireless Colour Printer", "Printers", "Computers", "200.99"),
                ("p2", "Testline LaserPro 150 Laser Printer", "Printers", "Computers", "279.99"),
                ("p3", "Sampleworks Home 3200 Inkjet Printer", "Printers", "Computers", "66.99"),
                ("p4", "Fixturon Tank 210 Wireless Printer", "Printers", "Computers", "165.99"),
                ("l1", "Testline LT-200B Bluetooth Label Maker", "Label Printers", "Computers", "27.99"),
                ("l2", "Sampleworks QL-820 label printer", "Label Printers", "Computers", "212.99"),
                ("l3", "Fixturon LabelManager 210 Label Maker", "Label Printers", "Computers", "74.99"),
                ("l4", "Testline LabelManager 280 Label Maker", "Label Printers", "Computers", "83.99"),
            ]
        )
        self.assertEqual(sorted(self._shown("printer")), ["p1", "p2", "p3", "p4"])
        self.assertEqual(sorted(self._shown("label printer")), ["l1", "l2", "l3", "l4"])

    def test_cheaper_look_alikes_never_answer_the_kind(self) -> None:
        self._serve(
            [
                ("s1", "Fixturon Nova A17 6.7\" 5G Smartphone 128GB", "Smartphones", "Computers", "216.99"),
                ("s2", "Testline Edge 70 6.8\" 5G Smartphone 256GB", "Smartphones", "Computers", "375.99"),
                ("s3", "Sampleworks Pixel 10 6.3\" 5G Smartphone", "Smartphones", "Computers", "991.99"),
                ("s4", "Fixturon K70 SE 6.56\" 4G Smartphone", "Smartphones", "Computers", "113.99"),
                ("i1", "Testline VVX 250 4-Line IP Phone and PSU", "IP Phones", "Computers", "63.99"),
                ("i2", "Sampleworks Trio C60 IP Conference Phone", "Conference Phones", "Computers", "590.99"),
                ("p1", "Fixturon OfficeJet 9125 Wireless Colour Printer", "Printers", "Computers", "200.99"),
                ("p2", "Testline LaserPro 150 Laser Printer", "Printers", "Computers", "279.99"),
                ("p3", "Sampleworks Home 3200 Inkjet Printer", "Printers", "Computers", "66.99"),
                ("p4", "Fixturon Tank 210 Wireless Printer", "Printers", "Computers", "165.99"),
                ("x1", "Testline Premium Matte Label - Continuous Roll: 76mm x 35m", "Printer Labels", "Computers", "8.99"),
                ("x2", "Sampleworks 44318506 printer drum Original 1 pc(s)", "Printer Drums", "Computers", "182.99"),
            ]
        )
        self.assertEqual(sorted(self._shown("smartphone")), ["s1", "s2", "s3", "s4"])
        self.assertEqual(sorted(self._shown("printer")), ["p1", "p2", "p3", "p4"])

    def test_smartphone_and_mobile_phone_show_different_phones(self) -> None:
        self._serve(
            [
                ("s1", "Fixturon Nova A17 6.7\" 5G Smartphone 128GB", "Mobile Phones", "Computers", "216.99"),
                ("s2", "Testline Edge 70 6.8\" 5G Smartphone 256GB", "Mobile Phones", "Computers", "375.99"),
                ("s3", "Sampleworks Pixel 10 6.3\" 5G Smartphone", "Mobile Phones", "Computers", "991.99"),
                ("s4", "Fixturon K70 SE 6.56\" 4G Smartphone", "Mobile Phones", "Computers", "113.99"),
                ("m1", "Testline CORE-S5 2.4\" Mobile Phone - Black", "Mobile Phones", "Computers", "67.99"),
                ("m2", "Sampleworks Leva E10 2.4\" Mobile Phone - Red", "Mobile Phones", "Computers", "71.99"),
                ("m3", "Fixturon Leva E22 2.8\" Flip Phone - Red", "Mobile Phones", "Computers", "79.99"),
                ("m4", "Testline Big Button 1.8\" Mobile Phone - Grey", "Mobile Phones", "Computers", "39.99"),
            ]
        )
        self.assertEqual(sorted(self._shown("smartphone")), ["s1", "s2", "s3", "s4"])
        self.assertEqual(sorted(self._shown("mobile phone")), ["m1", "m2", "m3", "m4"])

    def test_the_shops_own_category_path_is_read_on_its_own(self) -> None:
        beds = "home goods > bedroom furniture > beds"
        planters = "garden & outdoor > garden planters & stands > pots & planters"
        self._serve(
            [
                ("b1", "Fixturon Double Bed Frame Oak", "", "furniture", "199.00", beds),
                ("b2", "Testline King Size Bed Frame Grey", "", "furniture", "299.00", beds),
                ("b3", "Sampleworks Single Metal Bed Frame White", "", "furniture", "149.00", beds),
                ("b4", "Fixturon Storage Bed Frame Double", "", "furniture", "349.00", beds),
                ("g1", "Testline Wooden Raised Garden Bed, 120 x 50cm Planter Box", "", "garden", "54.99", planters),
                ("g2", "Sampleworks Raised Garden Bed with Trellis", "", "garden", "39.99", planters),
            ]
        )
        self.assertEqual(sorted(self._shown("bed")), ["b1", "b2", "b3", "b4"])


if __name__ == "__main__":
    unittest.main()
