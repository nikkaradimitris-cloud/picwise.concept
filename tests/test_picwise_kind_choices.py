"""The choices a search for a general word could offer, from the catalogue itself.

Owner, 2026-10-28: «Το search όταν του βάζεις καλώδιο πρέπει να συμπληρώνει προτάσεις τι
καλώδιο ζητάει ... το ίδιο με όλες αυτές τις γενικές λέξεις»; 2026-10-29: one logic for all
of them, never word by word (`picwise_providers.kind_choices`, measured only).

Pinned here: a kind's products are grouped by the words their titles name it with (the
word right before the noun of its name and that noun, as written: "sofa bed" under
sofas, a hyphenated word whole: "zip-up hoodie"), by their narrower kinds and by their
shelves; a group is a choice from a number of products, whatever share of the kind it
is; a kind is general with two choices of one way; a word before the nouns of many kinds
("black") is no choice, and neither is a number, the product's brand or a connective; a
kind of too few products is not read; accessories and doubtful products count for no
kind. Every row is local test data: fictional brands and shops, `.invalid` addresses.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from picwise_nlu.concept_understanding import ACCESSORY_MARKER  # noqa: E402
from picwise_providers import kind_choices  # noqa: E402
from picwise_providers.contracts import ProviderProduct  # noqa: E402

CABLES = "Electronics > Electronics Accessories > Cables"


def _product(number: int, title: str, *, category: str = "", brand: str = "Fictbrand") -> ProviderProduct:
    return ProviderProduct(
        provider_key="awin",
        provider_product_id=f"row-{number}",
        title=title,
        brand=brand,
        category_text=category,
        product_url=f"https://shop.invalid/p/{number}",
        image_url=f"https://shop.invalid/i/{number}.jpg",
        price_text="9.99",
        availability_text="in stock",
        currency="GBP",
        raw={"merchant_name": "Fictional Store"},
    )


def _measure(rows: list[tuple[str, str, set[str]]], brand: str = "Fictbrand") -> kind_choices.ChoicesMeasure:
    products = [_product(number, title, category=category, brand=brand) for number, (title, category, _kinds) in enumerate(rows)]
    return kind_choices.measure_kind_choices(products, [kinds for _title, _category, kinds in rows])


def _entry(measure: kind_choices.ChoicesMeasure, kind: str) -> kind_choices.KindChoices:
    return next(entry for entry in measure.kinds if entry.kind == kind)


class KindChoicesTests(unittest.TestCase):
    def _cables_and_rings(self) -> list[tuple[str, str, set[str]]]:
        return (
            [("Fictional HDMI Cable 2m", CABLES + " > Audio & Video Cables", {"cable"})] * 30
            + [("Fictional Satellite Coaxial Cable 10m", CABLES + " > Audio & Video Cables", {"cable"})] * 25
            + [("Fictional Cat6 Ethernet Cable 5m", CABLES + " > Network Cables", {"cable"})] * 22
            + [("Fictional USB Charging Cable 1m", CABLES, {"charging_cable", "cable"})] * 21
            + [("Fictional 2m Cable", CABLES, {"cable"})] * 3
            + [("Fictional Diamond Engagement Ring", "Apparel & Accessories > Jewelry > Rings", {"ring"})] * 55
            + [("Fictional Wedding Ring 9ct", "Apparel & Accessories > Jewelry > Rings", {"ring"})] * 5
            + [("Fictional Cable Tidy Clips", CABLES, {ACCESSORY_MARKER})] * 30
        )

    def test_a_kind_is_grouped_three_ways(self) -> None:
        cable = _entry(_measure(self._cables_and_rings()), "cable")
        # The accessories count for no kind: 101 cables, not 131.
        self.assertEqual(cable.products, 101)
        self.assertEqual(cable.noun, "cable")
        self.assertEqual(cable.named, 101)
        # "Cat6" has a number and "2m" is a spec: the word before the noun counts only
        # when it could be a choice ("ethernet").
        self.assertEqual(
            cable.words,
            (("hdmi cable", 30), ("coaxial cable", 25), ("ethernet cable", 22), ("charging cable", 21)),
        )
        self.assertEqual(cable.narrower, (("charging_cable", 21),))
        self.assertEqual(cable.shelves, (("Audio & Video Cables", 55), ("Cables", 24), ("Network Cables", 22)))
        self.assertTrue(cable.general_by_words)
        self.assertTrue(cable.general_by_shelves)

    def test_a_choice_counts_its_products_not_its_share(self) -> None:
        # One range holding most of a kind does not hide the others (on the server's
        # catalogue of 2026-10-29, fabric extension leads were 81% of the cables).
        rows = (
            [("Fictional Fabric Extension Cable 3m", CABLES, {"cable"})] * 900
            + [("Fictional HDMI Cable 2m", CABLES, {"cable"})] * 25
            + [("Fictional Speaker Cable 20m", CABLES, {"cable"})] * 21
        )
        cable = _entry(_measure(rows), "cable")
        self.assertEqual(cable.words, (("extension cable", 900), ("hdmi cable", 25), ("speaker cable", 21)))
        self.assertTrue(cable.general_by_words)

    def test_one_choice_is_not_general(self) -> None:
        measure = _measure(self._cables_and_rings())
        ring = _entry(measure, "ring")
        # Five wedding rings are under the twenty a choice needs; one shelf only.
        self.assertEqual(ring.words, (("engagement ring", 55),))
        self.assertFalse(ring.general)
        # A kind of too few products is not read at all: the 21 charging cables.
        self.assertNotIn("charging_cable", {entry.kind for entry in measure.kinds})

    def test_the_words_as_the_title_writes_them(self) -> None:
        rows = (
            [("Fixturon Corner Sofa", "", {"sofa"})] * 30
            + [("Fixturon Velvet Sofa Bed", "", {"sofa_bed", "sofa"})] * 25
            + [("Fixturon Zip-Up Hoodie", "", {"hoodie"})] * 30
            + [("Fixturon Oversized Hoodie", "", {"hoodie"})] * 25
        )
        measure = _measure(rows, brand="Fixturon")
        # Under sofas, a sofa bed is named "sofa bed": its own noun, not the sofa's.
        self.assertEqual(_entry(measure, "sofa").words, (("corner sofa", 30), ("sofa bed", 25)))
        self.assertEqual(_entry(measure, "hoodie").words, (("zip-up hoodie", 30), ("oversized hoodie", 25)))

    def test_a_word_before_the_nouns_of_many_kinds_is_no_choice(self) -> None:
        rows: list[tuple[str, str, set[str]]] = []
        nouns = (
            ("Cable", "cable"), ("Ring", "ring"), ("Laptop", "laptop"), ("Kettle", "kettle"),
            ("Toaster", "toaster"), ("Smartwatch", "smartwatch"), ("Mouse", "mouse"), ("Monitor", "monitor"),
            ("Keyboard", "keyboard"),
        )
        for position, (noun, kind) in enumerate(nouns):
            title_name = "Engagement Ring" if kind == "ring" else noun
            # A word of its own before each kind's noun, and "Black" before all of them.
            own = "Fict" + "abcdefghi"[position] * 2
            for word, count in (("Black", 30), (own, 20)):
                rows += [(f"Fixturon {word} {title_name}", "", {kind})] * count
        measure = _measure(rows, brand="Fixturon")
        self.assertEqual(measure.generic_words, (("black", 8),))
        # "black" came before the nouns of 8 kinds and is left out everywhere; "Fixturon"
        # is the brand. The ring's titles put "engagement" before its noun.
        self.assertEqual(_entry(measure, "laptop").words, (("fictcc laptop", 20),))
        self.assertEqual(_entry(measure, "ring").words, (("engagement ring", 50),))


if __name__ == "__main__":
    unittest.main()
