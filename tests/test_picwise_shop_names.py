"""A shop's name as a buyer knows it (owner, 2026-11-13; `picwise_surface.shop_names`).

The button read "View at Geepas Partner Program": Awin names a shop after its affiliate
programme. Only the programme's words come off; nothing is added.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_surface.shop_names import shop_display_name  # noqa: E402
from test_picwise_design_2026_10_31 import _FeedMixin, _call, _cards, _ean13, _text  # noqa: E402

# The 75 shops of the night of 12/11 (`prepared.json`, `balance.by_shop`).
_LIVE_SHOPS = (
    "Active Silver", "Affiliates - Spoiled Brat", "All Oils", "Angel Barocco",
    "Atenai London Affiliation Marketing", "Back to the Office", "Bad Shirt Club", "BioGaia",
    "Biobees", "Cheap Furniture Warehouse", "Cottsbury", "Craft Buddy Shop", "Curo Skin",
    "Doulton", "EXG Pro", "Extreme Comfort", "FLOWERFIX", "Fila UK", "Finediam",
    "Fitness Options", "Five Star Direct", "Game Over", "Gardenista", "Geepas Partner Program",
    "Greenera (UK)", "Harfi", "Homespace Direct", "InStock UK", "JOLTBOLT", "Juicy Couture UK",
    "King & Country", "Laud Sleep", "Lets Buy Books", "Living and Home", "Living with Luxury",
    "MALOA", "MONÉ UK Affiliate Programme", "Ma Lin", "Mint Outdoor",
    "MonsterPiercing -Quality Piercing Jewellery", "Mr Farts", "Needs No Label", "NeuroScent",
    "No.98 Beauty", "Optimum Nutrition UK", "Opulensi Perfumes Lattafa Sapil Anfar",
    "Pixie Dixie", "Pro Espresso", "Pro-Camera", "Raw Beauty Lab", "Ready Steady Bed",
    "Red Run", "SUNJOY UK", "SafeFort (UK)", "Scottish Fine Soaps UK",
    "Shopping Ads: Google & Bing", "Spacelift Creators", "Starlight Beds", "Steam & Oak",
    "Susan Caplan", "THEGATHER", "The Brush & Broom", "The Foam People",
    "The Gerry Anderson Store", "The Sleep People", "Truthbrush", "Viaduct Clothing",
    "WATCH & WATCH", "WAU", "Watch Enclave Affiliate Programme", "Wilder Botanics", "Zilch",
    "eFans Direct", "sitre", "usmile",
)
_READ_AS = {
    "Affiliates - Spoiled Brat": "Spoiled Brat",
    "Atenai London Affiliation Marketing": "Atenai London",
    "Geepas Partner Program": "Geepas",
    "Greenera (UK)": "Greenera",
    "MONÉ UK Affiliate Programme": "MONÉ UK",
    "MonsterPiercing -Quality Piercing Jewellery": "MonsterPiercing",
    "SafeFort (UK)": "SafeFort",
    "Watch Enclave Affiliate Programme": "Watch Enclave",
}


class ShopNameTests(unittest.TestCase):
    def test_the_programme_s_words_come_off_and_nothing_else(self) -> None:
        self.assertEqual(len(_LIVE_SHOPS), 75)
        for name in _LIVE_SHOPS:
            self.assertEqual(shop_display_name(name), _READ_AS.get(name, name), name)

    def test_nothing_is_added_and_a_name_is_never_emptied(self) -> None:
        for name in _LIVE_SHOPS:
            self.assertTrue(set(shop_display_name(name).split()) <= set(name.split()), name)
        self.assertEqual(shop_display_name("Affiliate Programme"), "Affiliate Programme")
        self.assertEqual(shop_display_name("  Geepas   Partner Program "), "Geepas")
        # A dash with a space on both sides may belong to the name.
        self.assertEqual(shop_display_name("Salt - Pepper"), "Salt - Pepper")
        self.assertEqual(shop_display_name(""), "")


class CardTests(_FeedMixin, unittest.TestCase):
    def test_the_card_and_its_button_name_the_shop_as_a_buyer_knows_it(self) -> None:
        self._serve([
            {"pid": f"k{index}", "title": f"Fixturon Kettle Model {index} 1.7L", "price": f"{10 + index}.00",
             "ean": _ean13(f"52{index:010d}"), "shop": "Geepas Partner Program"}
            for index in range(1, 6)
        ])
        page = _call("/search", {"q": "kettle"})
        cards = _cards(page)
        self.assertEqual(len(cards), 4)
        for card in cards:
            self.assertEqual(_text(re.search(r'<p class="pw-card-shop">(.*?)</p>', card).group(1)), "Geepas via Awin")
            self.assertIn("View at Geepas", _text(card))
        self.assertNotIn("Partner Program", page)


if __name__ == "__main__":
    unittest.main()
