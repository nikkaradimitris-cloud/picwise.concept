"""The choices a search for a general word could offer, from the catalogue itself.

Owner, 2026-10-28: «Το search όταν του βάζεις καλώδιο πρέπει να συμπληρώνει προτάσεις τι
καλώδιο ζητάει ... το ίδιο με όλες αυτές τις γενικές λέξεις»; 2026-10-29: one logic for all
of them, never word by word (`picwise_providers.kind_choices`, measured only).

Pinned here: a kind's products are grouped by the word their titles put right before
its noun, by their narrower kinds and by their shelves; a kind is general when two such
groups each hold enough of it; a word before the nouns of many kinds ("black") is no
choice, and neither is a number, the product's brand or a connective; a kind of too few
products is not read; accessories and doubtful products count for no kind. Every row is
local test data: fictional brands and shops, `.invalid` addresses.
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


class KindChoicesTests(unittest.TestCase):
    def _cables_and_rings(self) -> tuple[list[ProviderProduct], list[set[str]]]:
        products: list[ProviderProduct] = []
        kinds: list[set[str]] = []
        rows = (
            [("Fictional HDMI Cable 2m", CABLES + " > Audio & Video Cables", {"cable"})] * 25
            + [("Fictional Satellite Coaxial Cable 10m", CABLES + " > Audio & Video Cables", {"cable"})] * 20
            + [("Fictional Cat6 Ethernet Cable 5m", CABLES + " > Network Cables", {"cable"})] * 15
            + [("Fictional USB Charging Cable 1m", CABLES, {"charging_cable", "cable"})] * 12
            + [("Fictional 2m Cable", CABLES, {"cable"})] * 3
            + [("Fictional Diamond Engagement Ring", "Apparel & Accessories > Jewelry > Rings", {"ring"})] * 55
            + [("Fictional Wedding Ring 9ct", "Apparel & Accessories > Jewelry > Rings", {"ring"})] * 5
            + [("Fictional Cable Tidy Clips", CABLES, {ACCESSORY_MARKER})] * 30
        )
        for number, (title, category, product_kinds) in enumerate(rows):
            products.append(_product(number, title, category=category))
            kinds.append(product_kinds)
        return products, kinds

    def test_a_kind_is_grouped_three_ways(self) -> None:
        products, kinds = self._cables_and_rings()
        measure = kind_choices.measure_kind_choices(products, kinds)
        cable = next(entry for entry in measure.kinds if entry.kind == "cable")
        # The accessories count for no kind: 75 cables, not 105.
        self.assertEqual(cable.products, 75)
        self.assertEqual(cable.noun, "cable")
        self.assertEqual(cable.named, 75)
        # "Cat6" has a number and "2m" is a spec: the word before the noun counts only
        # when it could be a choice ("ethernet").
        self.assertEqual(
            cable.words, (("hdmi", 25), ("coaxial", 20), ("ethernet", 15), ("charging", 12))
        )
        self.assertEqual(cable.narrower, (("charging_cable", 12),))
        self.assertEqual(cable.shelves[:2], (("Audio & Video Cables", 45), ("Cables", 15)))
        self.assertTrue(cable.general_by_words)
        self.assertTrue(cable.general_by_shelves)
        self.assertTrue(cable.general)

    def test_one_large_group_is_not_general(self) -> None:
        products, kinds = self._cables_and_rings()
        measure = kind_choices.measure_kind_choices(products, kinds)
        ring = next(entry for entry in measure.kinds if entry.kind == "ring")
        self.assertEqual(ring.words, (("engagement", 55), ("wedding", 5)))
        # Five wedding rings are under the ten a choice needs; one shelf only.
        self.assertFalse(ring.general_by_words)
        self.assertFalse(ring.general_by_shelves)
        # A kind of too few products is not read at all: the 12 charging cables.
        self.assertNotIn("charging_cable", {entry.kind for entry in measure.kinds})

    def test_a_word_before_the_nouns_of_many_kinds_is_no_choice(self) -> None:
        products: list[ProviderProduct] = []
        kinds: list[set[str]] = []
        nouns = (
            ("Cable", "cable"), ("Ring", "ring"), ("Laptop", "laptop"), ("Kettle", "kettle"),
            ("Toaster", "toaster"), ("Smartwatch", "smartwatch"), ("Mouse", "mouse"), ("Monitor", "monitor"),
            ("Keyboard", "keyboard"),
        )
        number = 0
        for position, (noun, kind) in enumerate(nouns):
            title_name = "Engagement Ring" if kind == "ring" else noun
            # A word of its own before each kind's noun, and "Black" before all of them.
            own = "Fict" + "abcdefghi"[position] * 2
            for word, count in (("Black", 30), (own, 20)):
                for _ in range(count):
                    products.append(_product(number, f"Fixturon {word} {title_name}", brand="Fixturon"))
                    kinds.append({kind})
                    number += 1
        measure = kind_choices.measure_kind_choices(products, kinds)
        self.assertEqual(measure.generic_words, (("black", 8),))
        laptop = next(entry for entry in measure.kinds if entry.kind == "laptop")
        # "black" came before the nouns of 8 kinds and is left out everywhere; "Fixturon"
        # is the brand. The ring's titles put "engagement" before its noun.
        self.assertEqual(laptop.words, (("fictcc", 20),))
        ring = next(entry for entry in measure.kinds if entry.kind == "ring")
        self.assertEqual(ring.words, (("engagement", 50),))


if __name__ == "__main__":
    unittest.main()
