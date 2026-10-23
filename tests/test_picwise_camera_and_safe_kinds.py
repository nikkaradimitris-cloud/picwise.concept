"""What a camera shop's and a safe shop's products are, read on the owner's file.

Owner, 2026-10-23: «Ναι» to five fixes, after the owner's Google-format file of
Pro-Camera and SafeFort (1,184 rows, the same as live) showed why "camera" listed
lenses and hid 111 of 224 real cameras, and why "phone charger" listed charging safes:

1. a "Camera Body" is the camera sold without a lens, not a body (35 cameras);
2. in a feed's type, what follows a spaced "+" comes with the product (63 cameras sold
   with a mount adapter);
3. a "Camera Kit" is the camera and what comes with it (13 kits);
4. a type that names a kind only before another product's noun ("Canon DSLR Lenses")
   gives way to a category that says otherwise (43 lenses);
5. a title whose lead names nothing is read on after a bar ("... Certified |
   Lithium-Ion Battery Charging Safe"): 6 safes.

The titles, types and shelves of the live cases are the shops' own; the rest are
written in the same shape, with fictional brands.
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
)

_CAMERAS = "Cameras & Optics > Cameras > Digital Cameras"
_LENSES = "Cameras & Optics > Camera & Optic Accessories > Camera & Video Camera Lenses > Camera Lenses"
_CAMERA_PARTS = "Cameras & Optics > Camera & Optic Accessories > Camera Parts & Accessories"
_BATTERY_CHARGERS = (
    "Electronics > Electronics Accessories > Power > Battery Accessories > General Purpose Battery Chargers"
)
_POWER = "Electronics > Electronics Accessories > Power > Power Adapters & Chargers"


def _kinds(product_type: str, category: str, title: str) -> set[str]:
    return set(annotate_product_concepts(product_type, category, title))


class CamerasAreCamerasTests(unittest.TestCase):
    def test_a_camera_body_is_the_camera(self) -> None:
        for product_type, title in (
            ("Cameras > Canon > Canon Mirrorless Cameras > Canon EOS R6 II", "Canon EOS R6 Mark II Mirrorless Camera Body"),
            ("", "Canon EOS R6 Mark II Mirrorless Camera Body"),
            ("", "Fixturon X-T9 Body - Black"),
        ):
            with self.subTest(title=title, product_type=product_type):
                self.assertIn("camera", _kinds(product_type, _CAMERAS, title))

    def test_what_follows_a_plus_in_the_type_comes_with_the_camera(self) -> None:
        for product_type, title in (
            (
                "Cameras > Nikon > Nikon Mirrorless Cameras > Nikon Z6 III + FTZ II mount adapter",
                "Nikon Z6 III Mirrorless Camera with FTZ II Mount Adapter",
            ),
            (
                "Cameras > Canon > Canon Mirrorless Cameras > Canon EOS R5 + EF-EOS R mount adapter",
                "Canon EOS R5 Mirrorless Camera Body with EF-EOS R mount adapter",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn("camera", _kinds(product_type, _CAMERAS, title))
        # The adapter sold alone is still an accessory.
        self.assertEqual(
            _kinds(
                "Accessories > Camera Mount Adapters > Nikon > Nikon FTZ II Mount Adapter",
                _CAMERA_PARTS,
                "Nikon FTZ II Mount Adapter",
            ),
            {ACCESSORY_MARKER},
        )

    def test_a_camera_kit_is_the_camera(self) -> None:
        for product_type, title in (
            (
                "Cameras > Vlogging Camera Kits > Canon > Vlogging Canon EOS R50 Camera Kit",
                "Vlogging Canon EOS R50 Mirrorless Camera Kit",
            ),
            ("", "Beginner Wildlife Photography Fixturon Z50 Mirrorless Camera Kit"),
        ):
            with self.subTest(title=title):
                self.assertIn("camera", _kinds(product_type, _CAMERAS, title))
        # A kit of something else for the camera stays an accessory.
        for title in ("Fixturon Camera Cleaning Kit", "Fixturon Camera Lens Kit"):
            with self.subTest(title=title):
                self.assertEqual(_kinds("", _CAMERAS, title), {ACCESSORY_MARKER})


class LensesAreNotCamerasTests(unittest.TestCase):
    def test_a_type_naming_the_kind_only_before_another_product(self) -> None:
        for product_type, title in (
            (
                "Lenses > Canon > Canon DSLR Lenses > Canon DSLR Standard Prime Lenses > Canon EF 50mm f/1.8 STM",
                "Canon EF 50mm f/1.8 STM Lens",
            ),
            (
                "Lenses > Nikon > Nikon DSLR Lenses > Nikon DSLR Standard Prime Lenses > Nikon AF-S DX 35mm f/1.8G",
                "Nikon AF-S DX 35mm f/1.8G Lens",
            ),
        ):
            with self.subTest(title=title):
                self.assertEqual(_kinds(product_type, _LENSES, title), {ACCESSORY_MARKER})

    def test_the_type_keeps_its_kind_unless_the_category_says_otherwise(self) -> None:
        # The category names the type's kind: the type stands, as before.
        self.assertIn("camera", _kinds("Canon DSLR Lenses", _CAMERAS, "Fixturon EF 50mm Lens"))
        # A category naming nothing leaves the type its kind.
        self.assertIn("laptop", _kinds("Laptop Computers", "Electronics", "Fixturon Book 14"))
        # A type that names the kind as its own noun anywhere keeps it.
        self.assertIn("laptop", _kinds("Laptops > Laptop Computers", "", "Fixturon Book 14"))
        self.assertIn(
            "camera",
            _kinds(
                "Cameras > Canon > Canon DSLR Cameras > Canon EOS 2000D 18-55 III",
                _CAMERAS,
                "Canon EOS 2000D DSLR Camera with EF-S 18-55 mm f/3.5-5.6 III Lens",
            ),
        )


class TheTitleAfterTheBarTests(unittest.TestCase):
    def test_a_lead_that_names_nothing_is_read_on_after_the_bar(self) -> None:
        title = (
            "Batteryguard L-10 HE VDMA 24994 Certified | Lithium-Ion Battery Charging Safe | "
            "230V C - UK - KEY LOCK / SWITCHED"
        )
        self.assertEqual(_kinds("", _BATTERY_CHARGERS, title), {UNCERTAIN_MARKER})

    def test_the_shelf_still_decides_when_the_bar_names_nothing_else(self) -> None:
        for title in (
            # The part after the bar names the shelf's own kind.
            "Fixturon X200 | USB-C Wall Charger | White",
            # It names the shop.
            "Fixturon X200 Certified | Fixturon Store",
            # The lead names the product already.
            "Fixturon 20W USB-C Charger | Fixturon Store",
        ):
            with self.subTest(title=title):
                self.assertIn("phone_charger", _kinds("", _POWER, title))


if __name__ == "__main__":
    unittest.main()
