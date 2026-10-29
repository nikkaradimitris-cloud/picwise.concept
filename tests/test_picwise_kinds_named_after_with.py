"""A kind a title names only after "with", read as the product when its shelf names it too.

Owner, 2026-10-28: «Ξεκινάμε με το 1», the first of the three things to finish before a
deployment: 3,075 of Finediam's engagement rings, on its shelf of rings, were read as
accessories of a ring, so no search for a ring showed them. Their titles describe the
ring past a "With" before they name it: "2.00 Ct Lab Grown 3 Stone With Side Halo
Diamond Engagement Ring Platinum", and only the words before a purpose word named the
product.

Pinned here: a title that names no kind before its first "with" (or "w/") is the kind it
names after it, when the shop's narrowest shelf names that kind too, past one "with" or
more; English words only (owner, 2026-10-29: «Η διορθώσεις πρέπει να αφορούν αγγλικό
λεξιλόγιο»); a metal right after the kind's name describes it, as gold and silver do
("... Engagement Ring Platinum"); and the look-alikes stay what they were: a title naming a kind only
after "for", or after an accessory's noun ("Display Stand with ..."), or on no shelf
naming it, is still an accessory; a kind named before "with" is still the product ("Pram
with Car Seat", "Vacuum cleaner with filter", "Diamond Engagement Ring with Gift Box").
The titles are the shops' own or written in their shape.
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

from picwise_nlu.concept_understanding import ACCESSORY_MARKER, annotate_product_concepts  # noqa: E402

RINGS = "Clothing & Accessories > Jewellery & Watches > Rings"
GOOGLE_RINGS = "Apparel & Accessories > Jewelry > Rings"


def _kinds(product_type: str, category: str, title: str) -> set[str]:
    return set(annotate_product_concepts(product_type, category, title))


class NamedAfterWithTests(unittest.TestCase):
    def test_a_ring_described_past_with_is_a_ring_on_a_shelf_of_rings(self) -> None:
        for title in (
            "2.00 Ct Lab Grown 3 Stone With Side Halo Diamond Engagement Ring",
            "2.00 Ct Lab Grown 3 Stone With Side Halo Diamond Engagement Ring 18K White Gold",
            "2.00 Ct Lab Grown 3 Stone With Side Halo Diamond Engagement Ring | UK Hallmarked",
            "Emerald Cut Blue Sapphire Halo Ring with Round Natural Pave Band | 1.50 Carat Engagement Ring",
            "Oval Cut With Hidden Halo With Split Shank Diamond Engagement Ring",
            "Lab Grown 1.00 Ct w/ Halo Diamond Engagement Ring",
            "Oval With Halo Engagement Ring for Women",
        ):
            for category in (RINGS, GOOGLE_RINGS):
                with self.subTest(title=title, category=category):
                    self.assertEqual(_kinds("", category, title), {"ring"})

    def test_a_metal_after_the_name_describes_it(self) -> None:
        # Measured on the server's catalogue of 2026-10-29: 32 of Finediam's rings named
        # past "With" were still accessories, "Platinum" right after the ring's name
        # voiding it as a word PicWise could not read.
        title = "2.00 Ct Lab Grown 3 Stone With Side Halo Diamond Engagement Ring Platinum - Sterling Silver / 0.50 Carat"
        self.assertEqual(_kinds("", RINGS, title), {"ring"})
        for title in (
            "Fixturon Halo Diamond Engagement Ring Platinum",
            "Fixturon Diamond Engagement Ring Sterling Silver Cubic Zirconia",
            "Fixturon Diamond Engagement Ring Titanium 4mm",
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("", "", title), {"ring"})

    def test_without_a_shelf_naming_the_kind_it_is_still_an_accessory(self) -> None:
        title = "2.00 Ct Lab Grown 3 Stone With Side Halo Diamond Engagement Ring 18K White Gold"
        for category in ("", "Apparel & Accessories > Jewelry"):
            with self.subTest(category=category):
                self.assertEqual(_kinds("", category, title), {ACCESSORY_MARKER})

    def test_after_for_or_an_accessory_noun_it_is_still_an_accessory(self) -> None:
        for title in (
            "Fixturon Lab Grown With Halo For Engagement Ring",
            "Fixturon Display Stand with Engagement Ring",
            "Fixturon Ring Stand with Engagement Ring",
            "Fixturon Ring Box with Engagement Ring Holder",
            "Fixturon Velvet Box with Engagement Ring Slot",
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("", RINGS, title), {ACCESSORY_MARKER})

    def test_a_kind_named_before_with_stays_the_product(self) -> None:
        self.assertEqual(_kinds("", RINGS, "Diamond Engagement Ring with Gift Box"), {"ring"})
        self.assertEqual(_kinds("", "", "Pram with Car Seat"), {"baby_stroller"})
        self.assertEqual(_kinds("", "", "Case with Stand for iPad"), {"phone_case"})
        self.assertEqual(_kinds("", "", "Vacuum cleaner with filter"), {"vacuum_cleaner"})
        self.assertEqual(_kinds("", "", "Filter for coffee machine"), {ACCESSORY_MARKER})
        # A model's name before "with", on a shelf of its own kind: what comes with it is
        # still not the product.
        for category in ("Electronics > E-Book Readers", ""):
            with self.subTest(category=category):
                self.assertEqual(_kinds("", category, "Fixturon Paperwhite with Case"), {ACCESSORY_MARKER})


if __name__ == "__main__":
    unittest.main()
