"""Kinds the check of far prices found wrong, read right.

Owner, 2026-10-27: «Διόρθω τους κανόνες», after the check of the prices far from their
kind's and their own shop's (`deployment/server/print_prices.py`) listed products read as
the wrong kind: Finediam's earring backs as earrings (113), InStock UK's aerial and
satellite coaxial cables as charging cables (265), Steam & Oak's sauna stones as saunas,
and InStock UK's photo frames with a mirror as mirrors (19).

Pinned here: earring backs are an accessory, whether the type, the shelf or neither says
earrings; a plain cable is a cable, and only one its title or shelf names as charging,
USB, Type-C or Lightning is a charging cable, which is still a cable; sauna stones are an
accessory; a title that ends in a photo frame is a photo frame, the new kind; and the
look-alikes stay what they were: earrings with screw backs, the same shop's cheap
earrings, real charging cables, saunas and their heaters, mirrors with a frame, a bed
frame, a stone bracelet; the two new kinds compare as their products' kinds did. The
titles are the shops' own or written in their shape.
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
    annotate_product_concepts,
    understand_product_query,
)
from picwise_taxonomy.comparison_rules import comparison_rule  # noqa: E402

EARRINGS = "clothing & accessories > jewellery & watches > earrings"
CABLES = "electronics > electronics accessories > cables"


def _kinds(product_type: str, category: str, title: str) -> set[str]:
    return set(annotate_product_concepts(product_type, category, title))


class EarringBacksTests(unittest.TestCase):
    def test_earring_backs_are_an_accessory(self) -> None:
        title = "LOX Locking Earring Backs – Colour Collection & Classic Finishes | Secure Fit"
        for product_type, category in (("Earrings", ""), ("Earrings", EARRINGS), ("", EARRINGS), ("Earring Backs", EARRINGS)):
            with self.subTest(product_type=product_type, category=category):
                self.assertEqual(_kinds(product_type, category, title), {ACCESSORY_MARKER})
        self.assertEqual(_kinds("Earrings", EARRINGS, "Fixturon Silicone Earring Backs (100 Pairs)"), {ACCESSORY_MARKER})
        self.assertEqual(_kinds("Earrings", EARRINGS, "Fixturon Butterfly Earring Backs 9ct Gold"), {ACCESSORY_MARKER})

    def test_earrings_stay_earrings(self) -> None:
        for title in (
            "9ct Gold Diamond Stud Earrings",
            "Diamond Stud Earrings with Screw Backs | 18ct White Gold",
            "Diamond Stud Earrings Screw Backs 0.50ct",
            "Round Diamond Drop Earrings – Lab-Grown & Natural",
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("Earrings", EARRINGS, title), {"earrings"})
        self.assertEqual(_kinds("", "", "Sterling Silver Hoop Earrings"), {"earrings"})


class CablesTests(unittest.TestCase):
    def test_a_plain_cable_is_a_cable_not_a_charging_cable(self) -> None:
        for category, title in (
            (CABLES, "Maplin F Type Connector RG58U Satellite Aerial Coaxial Cable - Pack of 2"),
            ("", "Maplin F Type Connector RG58U Satellite Aerial Coaxial Cable - Pack of 2"),
            (CABLES + " > audio & video cables", "Maplin 10m Black Satellite Coaxial Cable"),
            ("", "Maplin HDMI Cable 2m 4K"),
            ("", "Fixturon Cat6 Ethernet Cable 10m"),
            ("", "Fixturon Speaker Cable 20m"),
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("", category, title), {"cable"})

    def test_a_charging_cable_is_still_one_and_a_cable(self) -> None:
        for product_type, category, title in (
            ("", "", "Anker USB C to USB C Cable 2m"),
            ("", "", "Apple USB-C to Lightning Cable (1 m)"),
            ("", "", "Fixturon USB Charging Cable 3 Pack"),
            ("", "", "Fixturon Type C Cable 1m Braided"),
            ("", CABLES, "Fixturon Micro USB Cable 2m"),
            ("", "", "Fixturon Phone Charger Cable 2m"),
            ("", "", "Fixturon USB Charger Cable 1m"),
            ("", "", "Fixturon iPhone Cable 2m"),
            ("Cables", "", "Maplin USB-A to USB-C Cable 1m Black"),
            ("Charging Cables", "", "Maplin USB-A to USB-C Braided Cable"),
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds(product_type, category, title), {"charging_cable", "cable"})

    def test_a_buyer_asking_for_a_cable_or_a_charging_cable(self) -> None:
        # "Cable" answers with every cable, charging ones too; "charging cable" only
        # with those.
        self.assertEqual(understand_product_query("καλώδιο").concept_id, "cable")
        self.assertEqual(understand_product_query("cable").concept_id, "cable")
        self.assertEqual(understand_product_query("καλώδιο φόρτισης").concept_id, "charging_cable")
        self.assertEqual(understand_product_query("usb cable").concept_id, "charging_cable")


class SaunaStonesTests(unittest.TestCase):
    def test_sauna_stones_are_an_accessory(self) -> None:
        title = "Harvia Sauna Stones 5-10 cm - 20 kg Box (AC3000)"
        for product_type, category in (
            ("Sauna Stones", ""),
            ("Sauna Stones", "home & garden > pool & spa > sauna accessories"),
            ("Sauna", ""),
            ("", ""),
        ):
            with self.subTest(product_type=product_type):
                self.assertEqual(_kinds(product_type, category, title), {ACCESSORY_MARKER})
        self.assertEqual(_kinds("Outdoor Sauna", "", "Harvia Sauna Stones Olivine Diabase 20kg"), {ACCESSORY_MARKER})

    def test_saunas_and_stone_bracelets_stay_what_they_were(self) -> None:
        self.assertEqual(_kinds("", "", "Fixturon Outdoor Sauna 4 Person Barrel"), {"sauna"})
        self.assertEqual(_kinds("Outdoor Sauna", "", "Fixturon Barrel Sauna 4 Person Thermowood"), {"sauna"})
        self.assertEqual(_kinds("Sauna", "", "Harvia Sauna Heater with Stones 9kW"), {"sauna"})
        self.assertEqual(_kinds("", "", "Fixturon Chakra Bracelet 7 Stones Healing"), {"bracelet"})


class PhotoFramesTests(unittest.TestCase):
    def test_a_title_ending_in_a_photo_frame_is_a_photo_frame(self) -> None:
        for category, title in (
            ("home & garden > decor > picture frames", "Son 3D Word Glass & Mirror 6x4 Photo Frame"),
            ("", "Son 3D Word Glass & Mirror 6x4 Photo Frame"),
            ("", "Fixturon Mirror Photo Frame 5x7"),
            ("", "Fixturon Mirrored Glass Photo Frame 4x6"),
            ("", "Fixturon Digital Photo Frame 10 inch WiFi"),
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("", category, title), {"photo_frame"})
        self.assertEqual(understand_product_query("κορνίζα").concept_id, "photo_frame")

    def test_mirrors_and_beds_with_a_frame_stay_what_they_were(self) -> None:
        for category, title in (
            ("", "Round Wall Mirror with Wooden Frame"),
            ("home & garden > decor > mirrors", "Gold Framed Wall Mirror 60cm"),
            ("", "Fixturon Arched Mirror Black Frame 120cm"),
            ("", "Fixturon Full Length Mirror Gold Frame"),
            ("", "Fixturon Wall Mirror with Photo Frame"),
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds("", category, title), {"mirror"})
        self.assertEqual(
            _kinds("", "furniture > beds & accessories > beds & bed frames", "Double Bed Frame with Storage"), {"bed"}
        )


class NewKindsCompareAsTheirProductsDidTests(unittest.TestCase):
    def test_a_cable_and_a_photo_frame_fit_as_before(self) -> None:
        # The plain cables were charging cables and the photo frames mirrors: their
        # cards keep the length and the size, and claim no best.
        for new, old in (("cable", "charging_cable"), ("photo_frame", "mirror")):
            with self.subTest(kind=new):
                rule, before = comparison_rule(new), comparison_rule(old)
                self.assertEqual(rule.comparison_class, "fit")
                self.assertEqual(rule.matching_criteria, before.matching_criteria)
                self.assertEqual(rule.ranking_criteria, tuple())


if __name__ == "__main__":
    unittest.main()
