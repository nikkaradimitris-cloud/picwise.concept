"""A shelf's kind holds only when the product's own title does not name another product.

Owner, 2026-10-22: «Ναι, δούλεψε τον κανόνα για τα είδη», after the live site on the
Google-format link showed SafeFort's battery-charging safes for "phone charger" and a
pair of DJI propellers and Canon lenses for "camera". A shelf ("Cameras", "Power
Adapters & Chargers", "Keyboards", "Tables") gave its kind to titles that named another
product in words PicWise has no kind for: a lens, propellers, a safe, a keyboard plate,
a stool, a bench. The noun a title's lead ends with is now read against the nouns of
Google's product taxonomy: when it names a product that is not the shelf's kind, and
the shelf does not name it either, the product's kind is doubtful and no search shows
it by its kind (it is still found by its own words).

The titles of the live cases are the shops' own; the rest are written in the same
shape, with fictional brands.
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


def _kinds(category: str, title: str, product_type: str = "") -> set[str]:
    return set(annotate_product_concepts(product_type, category, title))


class AnotherProductOnTheShelfTests(unittest.TestCase):
    def test_the_live_cases_are_no_longer_their_shelf_kind(self) -> None:
        for category, title, shelf_kind in (
            ("Cameras & Optics > Cameras > Digital Cameras", "Canon EF 50mm f/1.8 STM Lens", "camera"),
            ("Cameras & Optics > Cameras", "DJI Flip Propellers (Pair)", "camera"),
            (
                "Electronics > Electronics Accessories > Power > Power Adapters & Chargers",
                "Batteryguard XL20 Lithium-Ion Battery Charging Safe – VDMA 24994 Certified",
                "phone_charger",
            ),
            (
                "Electronics > Electronics Accessories > Computer Components > Input Devices > Keyboards",
                "MonsGeek M2 Plate - POM",
                "keyboard",
            ),
            ("Furniture > Tables > Kitchen & Dining Room Tables", "Pine Bench All White", "table"),
            (
                "Cameras & Optics > Cameras > Surveillance Cameras",
                "Nedis Home Security Motion Detector Chime | 8 Ringtones",
                "camera",
            ),
            (
                "Electronics > Electronics Accessories > Power > Power Adapters & Chargers",
                "Mercury Rewireable IEC C13 Female Inline Socket Plug 6A 250V",
                "phone_charger",
            ),
        ):
            with self.subTest(title=title):
                kinds = _kinds(category, title)
                self.assertNotIn(shelf_kind, kinds)
                self.assertEqual(kinds, {UNCERTAIN_MARKER})

    def test_a_kind_named_only_to_describe_the_noun_after_it(self) -> None:
        title = "Modern Velvet Dressing Table Stool with Solid Wood Legs - White / 1 Unit"
        # On a shelf of stools the stool is the shelf's own product.
        self.assertEqual(_kinds("Furniture > Chairs > Table & Bar Stools", title), {"chair"})
        # On a shelf that does not hold stools it is doubtful, and never a table.
        self.assertEqual(_kinds("Furniture > Chairs", title), {UNCERTAIN_MARKER})
        self.assertEqual(
            _kinds("Furniture > Tables", "Fixturon Corduroy Modular Chaise Sofa Block - Corner"),
            {UNCERTAIN_MARKER},
        )
        self.assertEqual(
            _kinds("Furniture > Sofas", "Fixturon Corduroy Modular Chaise Sofa Block - Corner"),
            {UNCERTAIN_MARKER},
        )

    def test_what_is_said_of_the_product_is_read_past(self) -> None:
        # "Food Safe" is not a safe; the noun before it is the product's.
        self.assertEqual(
            _kinds(
                "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles",
                "Fixturon Glass Pitcher Food Safe",
            ),
            {UNCERTAIN_MARKER},
        )

    def test_pads_close_a_lead_as_an_accessory(self) -> None:
        self.assertEqual(
            _kinds(
                "Furniture > Outdoor Furniture > Outdoor Seating",
                "Water-Resistant Garden 4-Seater Bench Seat Pads for Patio Durable Bench Cushions",
            ),
            {ACCESSORY_MARKER},
        )


class TheShelfStillDecidesTests(unittest.TestCase):
    def test_a_lead_that_ends_in_a_model_name_or_a_spec(self) -> None:
        for category, title, kind in (
            (
                "Electronics > Electronics Accessories > Computer Components > Input Devices > Keyboards",
                "My Sweet Piano 3108RF - Fixturon Frost Pink / Dual Mode",
                "keyboard",
            ),
            ("Home & Garden > Household Appliances > Vacuums", "Fixturon V15 Detect", "vacuum_cleaner"),
            ("Electronics > Audio > Audio Components > Speakers", "Fixturon Rockbox 40W Black", "speaker"),
        ):
            with self.subTest(title=title):
                self.assertIn(kind, _kinds(category, title))

    def test_a_noun_the_shelf_names_too(self) -> None:
        for category, title, kind in (
            (
                "Furniture > Outdoor Furniture > Outdoor Seating > Sunloungers",
                "Provence Collection Outdoor Sun Lounger Set",
                "garden_furniture",
            ),
            (
                "Home & Garden > Kitchen & Dining > Kitchen Appliances > Coffee Makers & Espresso Machines"
                " > Electric & Stove-Top Espresso Pots",
                "9 Cup Stainless Steel Stove Top Percolator Espresso Pot",
                "coffee_machine",
            ),
            (
                "Home & Garden > Kitchen & Dining > Cookware & Bakeware > Cookware > Skillets & Frying Pans",
                "24cm Grey Die-Cast Aluminium Skillet with Durable Coating",
                "cookware",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(kind, _kinds(category, title))

    def test_a_noun_that_only_describes_the_product(self) -> None:
        for category, title, kind in (
            # A count of the noun is a spec.
            (
                "Home & Garden > Household Appliances > Climate Control Appliances > Space Heaters",
                "7-Fin, 9-Fin and 11-Fin Oil Filled Radiator Heaters - 11-Fin (2500W)",
                "heater",
            ),
            # "Food Safe" is said of the product.
            (
                "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles",
                "Fixturon Rapid Boil 1.7L Food Safe",
                "kettle",
            ),
            # A list of names for one product.
            (
                "Home & Garden > Kitchen & Dining > Kitchen Appliances > Juicers",
                "100W Silver Electric Juice Maker & Citrus Squeezer",
                "juicer",
            ),
            # A lead cut at the first item of a list.
            (
                "Home & Garden > Kitchen & Dining > Food Storage > Food Storage Containers",
                "4-Piece Tea, Coffee, Sugar Canister Set Retrovive In Black",
                "food_storage",
            ),
            # Two known kinds in a run: the last one is the product, as before.
            ("Home & Garden > Household Appliances > Fans & Heaters", "Testline 2000W Fan Heater", "heater"),
        ):
            with self.subTest(title=title):
                self.assertIn(kind, _kinds(category, title))

    def test_a_product_type_keeps_its_authority(self) -> None:
        # Only a shelf is read against the title's noun: a feed's own product type is
        # precise, and its titles often end in the device they fit.
        self.assertIn("camera", _kinds("", "Canon EF 50mm f/1.8 STM Lens", product_type="Digital Cameras"))


if __name__ == "__main__":
    unittest.main()
