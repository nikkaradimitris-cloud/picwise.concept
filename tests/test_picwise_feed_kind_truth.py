"""What a feed product is, read from a real catalogue's own wording.

Every case here comes from the first real Awin feed PicWise was given (11,573
electronics products, 2026-10-11), where the kind reading answered searches with the
wrong kind of product: 899 table runners and placemats under "τραπέζι", lens caps
under "καπέλο", disco balls under "μπάλα", lens rings and ring lights under
"δαχτυλίδι", USB cables under "οθόνη", a truck bed extender under "κρεβάτι", smart
switches under "κουρτίνες", desktop microphones under "υπολογιστής", DJ consoles under
"μίξερ". PROJECT_RULES and the mission allow none of that: a wrong kind of product is
the one answer PicWise must never give.

The rows are written with fictional brands, in the shape the real feed used.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_nlu.concept_understanding import (  # noqa: E402
    ACCESSORY_MARKER,
    UNCERTAIN_MARKER,
    annotate_product_concepts,
    understand_product_query,
)
from picwise_nlu.product_concepts import get_product_concepts  # noqa: E402


def _kinds(product_type: str = "", category: str = "", title: str = "") -> set[str]:
    return set(annotate_product_concepts(product_type, category, title))


class WeakNameTests(unittest.TestCase):
    """A name that is also an ordinary word inside other products' names."""

    def test_a_weak_name_never_says_what_a_feed_product_is(self) -> None:
        for product_type, title, must_not_be in (
            ("Lens Cap 67mm", "Fixturon 67mm Clip on Lens Cap", "hat"),
            ("Mirror Ball", "Fixturon Mirror Ball 30cm Gold", "football"),
            ("Step Down Rings", "Fixturon 62 to 67mm Step Up lens ring", "ring"),
            ("Compact Mixer", "Testline PRO:2 DJ Mixer 2 Channel", "mixer"),
            ("Tripod Quick Release Plate", "Fixturon Mountable Plate", "selfie_stick"),
            ("", "Sampleworks Wireless Carplay Screen 10 inch", "monitor"),
            ("Desktop 3.5mm", "Testline Microphone for Desktop", "desktop_pc"),
            ("", "Sampleworks Smart Curtain Switch Controller", "game_controller"),
        ):
            with self.subTest(product_type=product_type or title):
                self.assertNotIn(must_not_be, _kinds(product_type, "", title))

    def test_a_buyer_who_types_the_weak_name_is_still_understood(self) -> None:
        # The word is only weak in feed text. A query is the buyer saying what they
        # want, and "cap", "ball", "ring", "mixer" there mean the product.
        for query, expected in (
            ("cap", "hat"),
            ("καπέλο", "hat"),
            ("ball", "football"),
            ("ring", "ring"),
            ("δαχτυλίδι", "ring"),
            ("mixer", "mixer"),
            ("μίξερ", "mixer"),
            ("screen", "monitor"),
            ("tripod", "selfie_stick"),
            ("controller", "game_controller"),
        ):
            with self.subTest(query=query):
                self.assertEqual(understand_product_query(query).concept_id, expected)

    def test_the_full_name_still_classifies_a_feed_product(self) -> None:
        self.assertIn("hat", _kinds("Hats", "", "Fixturon Wool Hat"))
        self.assertIn("football", _kinds("Footballs", "", "Fixturon Match Football"))
        self.assertIn("mixer", _kinds("Stand Mixer", "", "Fixturon Stand Mixer 1000W"))
        self.assertIn("monitor", _kinds("Monitors", "", "Testline 27 inch Monitor"))


class ModifierTailTests(unittest.TestCase):
    """A product name followed by a word that says it is something else."""

    def test_a_tail_word_turns_the_name_into_a_description(self) -> None:
        for title, product_type in (
            ("Fixturon Red Plaid Valentine Table Runner", ""),
            ("Fixturon Christmas Set of 4 Placemats Table Mats", ""),
            ("Testline Cable Ties 100 pack", "Cable Ties"),
            ("Sampleworks Speaker Stands pair", "Speaker Stands"),
            ("Fixturon Man Stuff Shoe Restore Kit", ""),
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds(product_type, "", title), {ACCESSORY_MARKER})

    def test_an_accessory_word_counts_even_when_it_is_also_a_product_name(self) -> None:
        # "cover" is one of the names of a phone case, which used to make it invisible
        # to the accessory reading: "Luggage Cover" was filed under suitcases.
        self.assertEqual(_kinds("", "", "Fixturon Turtle Luggage Cover"), {ACCESSORY_MARKER})

    def test_a_product_type_word_is_not_a_tail(self) -> None:
        self.assertIn("speaker", _kinds("Portable Speaker System", "", "Testline Speaker 40W"))
        self.assertIn("vacuum_cleaner", _kinds("", "", "Fixturon YC1 Cordless Vacuum Cleaner"))


class TitleEvidenceTests(unittest.TestCase):
    """When only a title says what the product is, it must say it plainly."""

    def test_a_name_followed_by_an_unreadable_word_is_not_the_product(self) -> None:
        # Since the strict reading of 2026-10-16 such a title is doubtful rather than
        # kindless: neither the kind nor the "names the kind in its own words" fallback
        # lets it answer "bed" or "curtains".
        self.assertEqual(
            _kinds("", "", "Fixturon Universal Truck Bed Tailgate Extender"), {UNCERTAIN_MARKER}
        )
        self.assertEqual(_kinds("", "", "Sampleworks WiFi Smart Curtain Switch"), {UNCERTAIN_MARKER})

    def test_a_colour_a_spec_or_a_pack_word_still_reads_as_the_product(self) -> None:
        self.assertIn("smartwatch", _kinds("", "", "Testline APP 7 MAX Smartwatch Black Dial"))
        self.assertIn("speaker", _kinds("", "", "Testline Bluetooth Speaker 40W Portable"))
        self.assertIn("backpack", _kinds("", "", "Fixturon Custom Name Backpack"))
        self.assertIn("power_bank", _kinds("", "", "Testline PBQ-4000 Powerbank with QI"))


class CategoryBreadcrumbTests(unittest.TestCase):
    """A category is a path from the widest aisle to the narrowest shelf."""

    def test_the_first_shelf_that_names_a_product_decides(self) -> None:
        # The cables are kept under the monitors; they are still cables -- of no kind
        # the shelf or the title says (2026-10-27: no charging cable by "cables" alone).
        self.assertIn(
            "cable",
            _kinds("", "electronics & accessories > cables > monitor > summer deals",
                   "Testline USB 2.0 to USB-A Mini-B - 18 m"),
        )

    def test_a_shelf_of_accessories_decides_for_the_whole_path(self) -> None:
        self.assertEqual(
            _kinds("Rail Rod Mount", "cameras & optics > camera & optic accessories",
                   "Fixturon Cold Shoe Rod Clamp"),
            {ACCESSORY_MARKER},
        )
        self.assertEqual(
            _kinds("", "home > household > car & bike > other car accessories",
                   "Fixturon Car Organiser 2 pcs"),
            {ACCESSORY_MARKER},
        )

    def test_a_bare_accessories_category_names_nothing_by_itself(self) -> None:
        # A merchant's catch-all aisle. The title still decides, or 706 phone cases
        # of this feed would vanish.
        self.assertIn("phone_case", _kinds("iPhone XR", "accessories", "Fixturon iPhone XR Case"))

    def test_a_product_named_in_passing_by_a_shelf_is_not_read(self) -> None:
        # A coin cell on the "Power banks and batteries" shelf is not a power bank.
        self.assertEqual(
            _kinds("", "electronics > power banks and batteries > batteries > cell coin battery",
                   "Testline Lithium Battery CR2016 3V"),
            set(),
        )

    def test_a_shelf_of_two_kinds_is_decided_by_the_title(self) -> None:
        self.assertIn("fan", _kinds("", "fans & heaters", "Testline Desk Fan 30cm White"))
        self.assertIn("heater", _kinds("", "fans & heaters", "Testline Convector Heater 2000W"))
        self.assertEqual(_kinds("", "fans & heaters", "Testline Model 7 2000W"), set())


class CompatibilityTypeTests(unittest.TestCase):
    """A product type that names what the product plugs into, not what it is."""

    def test_the_title_and_category_together_outrank_a_compatibility_type(self) -> None:
        kinds = _kinds(
            "Smartphone USB-C",
            "electronics > audio > audio components > microphones",
            "Testline Microphone | Used for: Notebook / Smartphone / Tablet",
        )
        self.assertIn("microphone", kinds)
        self.assertNotIn("smartphone", kinds)

    def test_a_type_the_title_confirms_still_decides(self) -> None:
        self.assertIn(
            "vacuum_cleaner",
            _kinds("Vacuum Cleaners", "home > floorcare", "Fixturon Robot Vacuum Cleaner"),
        )


class LexiconShapeTests(unittest.TestCase):
    def test_every_weak_name_is_also_a_name_of_its_product(self) -> None:
        for concept in get_product_concepts():
            for form in concept.weak:
                with self.subTest(concept=concept.concept_id, form=form):
                    self.assertIn(form, concept.english + concept.greek)


if __name__ == "__main__":
    unittest.main()
