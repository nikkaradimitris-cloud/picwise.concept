"""Kinds fixed from the build's first list of products whose title does not name their kind.

Owner, 2026-10-23, after the first live list in `/prepared.json` (`kinds`): «Όχι τα
κομοδίνα είναι κομοδίνα προχώρα». Its cheapest suspects showed bath mats as rugs,
bedside cabinets as tables, bedspreads as duvets, RAM as a processor, a punchbag as a
bag, a garden set and a bonfire as heaters, and a subscription as a coffee machine.
Bedside tables, bath mats, bedspreads and punching bags are kinds of their own now, a
"DIMM" is RAM, a subscription and a bonfire are other products, and only a path's
narrowest shelf says that it holds a title's noun.

The titles are the shops' own, from the live list; the shelves are Google's, as the
shops most likely file them; the rest are written in the same shape, with fictional
brands.
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

from picwise_nlu.concept_understanding import UNCERTAIN_MARKER, annotate_product_concepts  # noqa: E402

_BATH_MATS = "Home & Garden > Bathroom Accessories > Bath Mats & Rugs"
_RUGS = "Home & Garden > Decor > Rugs"
_NIGHTSTANDS = "Furniture > Tables > Nightstands"
_DINING_TABLES = "Furniture > Tables > Kitchen & Dining Room Tables"
_QUILTS = "Home & Garden > Linens & Bedding > Bedding > Quilts & Comforters"
_PROCESSORS = "Electronics > Electronics Accessories > Computer Components > Computer Processors"
_PUNCHING_BAGS = (
    "Sporting Goods > Athletics > Boxing & Martial Arts > Boxing & Martial Arts Training Equipment"
    " > Punching & Training Bags"
)
_HANDBAGS = "Apparel & Accessories > Handbags, Wallets & Cases > Handbags"
_PATIO_HEATERS = "Home & Garden > Household Appliances > Climate Control Appliances > Patio Heaters"
_ESPRESSO = (
    "Home & Garden > Kitchen & Dining > Kitchen Appliances > Coffee Makers & Espresso Machines > Espresso Machines"
)


def _kinds(category: str, title: str) -> set[str]:
    return set(annotate_product_concepts("", category, title))


class KindsOfTheirOwnTests(unittest.TestCase):
    def test_a_bedside_table_is_not_a_table(self) -> None:
        for title in (
            "Prague Graduated Bedside Cabinet Black Ash Elegant and Spacious Bedroom Storage",
            "Chestnut Semi Circle Bedside",
            "Extra Mini Wall Mounted Curved Oak-ish Bedside with Open Slot",
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds(_NIGHTSTANDS, title), {"bedside_table"})
        for title in ("Fixturon Oak Dining Table 6 Seater", "Fixturon Round Coffee Table"):
            with self.subTest(title=title):
                self.assertEqual(_kinds(_DINING_TABLES, title), {"table"})

    def test_a_bath_mat_is_not_a_rug(self) -> None:
        for category in (_BATH_MATS, _RUGS):
            with self.subTest(category=category):
                self.assertEqual(_kinds(category, "Noodle Bath Mats - 40x60cm / Black"), {"bath_mat"})
        self.assertEqual(_kinds(_BATH_MATS, "Fixturon Cotton Bath Rug - Grey"), {"bath_mat"})
        self.assertEqual(_kinds(_RUGS, "Fixturon Moroccan Wool Rug 160x230cm"), {"rug"})
        self.assertEqual(_kinds(_BATH_MATS, "Fixturon Shaggy Rug - Cream"), {"rug"})

    def test_a_bedspread_is_not_a_duvet(self) -> None:
        self.assertEqual(_kinds(_QUILTS, "Catherine Lansfield Tilly Floral Bedspread - Blue"), {"bedspread"})
        self.assertEqual(_kinds(_QUILTS, "Fixturon 10.5 Tog Duvet - King"), {"duvet"})

    def test_a_dimm_is_ram_on_any_shelf(self) -> None:
        self.assertEqual(
            _kinds(_PROCESSORS, "Kingston Technology FURY Beast 32GB 5600MT/s DDR5 CL36 DIMM (Kit of 2) Black"),
            {"ram_memory"},
        )
        self.assertEqual(_kinds(_PROCESSORS, "AMD Ryzen 7 5800 XT 8 Core AM4 CPU/Processor"), {"processor"})


class NotTheShelfsKindTests(unittest.TestCase):
    def test_a_punching_bag_is_not_a_bag(self) -> None:
        for category, title in (
            (_PUNCHING_BAGS, "Pro Power 3 ft Punchbag With Gloves Boxing Set Home Sport"),
            (_HANDBAGS, "Pro Power 3 ft Punchbag With Gloves Boxing Set Home Sport"),
            (_PUNCHING_BAGS, "Fixturon 4ft Heavy Punching Bag"),
        ):
            with self.subTest(category=category, title=title):
                self.assertNotIn("bag", _kinds(category, title))
        self.assertIn("bag", _kinds(_HANDBAGS, "Fixturon Leather Tote Bag - Tan"))

    def test_what_is_not_the_shelfs_product(self) -> None:
        # Only the narrowest shelf holds a title's noun: "Home & Garden" does not hold a
        # garden set on the patio heaters shelf.
        for category, title in (
            (_PATIO_HEATERS, "Family Garden Set"),
            (_PATIO_HEATERS, "Crakl Bonfire"),
            (_ESPRESSO, "Rocket Club Subscription"),
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds(category, title), {UNCERTAIN_MARKER})
        self.assertEqual(_kinds(_PATIO_HEATERS, "Fixturon 2kW Electric Patio Heater"), {"heater"})
        self.assertEqual(_kinds(_ESPRESSO, "Rocket Espresso Appartamento 2.0 - White"), {"coffee_machine"})


if __name__ == "__main__":
    unittest.main()
