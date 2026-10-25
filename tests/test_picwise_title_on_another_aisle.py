"""A title's kind on an aisle of Google's that holds no kind of that department.

Owner, 2026-10-25, «προχώρα στο επόμενο λάθος»: after the watch fix, the server's list of
products whose title alone names their kind (neither their type nor their shelf does)
showed chocolate mice as mice and sweets named "Cable" or "Tablets" on "Sweets &
Chocolate", piercing barbells as barbells on "Body Jewellery", the books "Colleen Hoover"
and "Make Your Bed" as a vacuum cleaner and a bed, incontinence "Pants" as trousers, a
model paint's "Protective Coat" as a jacket. When the shelf names no kind, the title
decides; now, when the category is an aisle of Google's whose shelves name no kind of
that department (`mega_category_id`), the title's kind is doubtful: the product is found
by its words, never by its kind. Google's British aisle names count as its US ones. A
category that is no aisle of Google's, or none at all, leaves the title to decide, and
clothing on a clothing aisle, or a dog bed among pet supplies, keep their kinds; so
does a kind whose broader kind's department the aisle holds: a smartwatch where watches
are. The aisle's shelves are also read in the singular, an aisle naming no kind at its
first two levels counts at its top, and an aisle whose name names the kind holds it:
the first version doubted dining sets, futon beds, tote bags, toys and massagers too.

The titles are the shops' own, from the server's list of 2026-10-25, or written in the
same shape with fictional brands; the shelves are as the shops file them.
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

_SWEETS = "Food, Beverages & Tobacco > Food Items > Sweets & Chocolate"
_BOOKS = "Media > Books > Print Books"
_BODY_JEWELLERY = "Clothing & Accessories > Jewellery & Watches > Body Jewellery"


def _kinds(category: str, title: str) -> set[str]:
    return set(annotate_product_concepts("", category.lower(), title))


class ATitlesKindOnAnotherDepartmentsAisleTests(unittest.TestCase):
    def test_the_titles_kind_is_doubtful(self) -> None:
        for category, title in (
            (_SWEETS, "Build Your Own - 100g Pick and Mix Sweets - Chocolate Mice"),
            (_SWEETS, "Giant Apple Cable"),
            (_SWEETS, "Voice Tablets - 225g Sweet Pouch"),
            (_BOOKS, "Colleen Hoover 6 Book Collection Set - Heart Bones, Ugly Love & More"),
            (_BOOKS, "Make Your Bed: Little Things That Can Change Your Life"),
            (_BODY_JEWELLERY, "G23 Titanium Gold Anodised Circular Barbell with Ball - 6mm"),
            ("Health & Beauty > Healthcare > Incontinence Aids", "Nundies Youth Pants 8-15 Years - Pack of 12"),
            (
                "Arts & Entertainment > Hobbies & Creative Arts > Model Making",
                "Vallejo Model Air - Russian AF Grey Protective Coat",
            ),
        ):
            with self.subTest(category=category, title=title):
                self.assertEqual(_kinds(category, title), {UNCERTAIN_MARKER})

    def test_a_kind_of_the_aisles_department_is_kept(self) -> None:
        for category, title, kind in (
            ("Clothing & Accessories > Clothing > Shirts & Tops", "Daisy Street Button Heart Grey Hoodie - UK 10",
             "hoodie"),
            ("Clothing & Accessories > Clothing > Activewear", "Fixturon Contrast Breathable T-Shirt - 2XL", "t_shirt"),
            ("Apparel & Accessories > Clothing > Activewear", "Fixturon Contrast Breathable T-Shirt - 2XL", "t_shirt"),
            ("Animals & Pet Supplies > Pet Supplies > Dog Supplies", "Fixturon Orthopaedic Dog Bed", "bed"),
        ):
            with self.subTest(category=category, title=title):
                self.assertIn(kind, _kinds(category, title))

    def test_a_broader_kinds_department_counts_too(self) -> None:
        # A smartwatch is a watch too: an aisle that holds watches may hold one (on the
        # server, two real smartwatches had left the "smartwatch" page).
        for category in ("Sporting Goods > Exercise & Fitness", "Clothing & Accessories > Clothing Accessories"):
            with self.subTest(category=category):
                self.assertIn(
                    "smartwatch",
                    _kinds(category, "V69 IP68 1.85-inch Bluetooth Smart Watch with Voice Calling - Black"),
                )

    def test_what_the_first_version_took_away_wrongly_is_kept(self) -> None:
        # The server's list of the products this rule made doubtful (2,062) showed dining
        # sets, sofa suites, futon beds, tote bags, toys and every electric massager among
        # them: aisles whose shelves the lexicon cannot read ("Electric Massagers", with
        # no plural in it), or that name no kind at all at their first two levels.
        for category, title, kind in (
            ("Furniture > Furniture Sets > Kitchen & Dining Furniture Sets",
             "Bolitzo Oak Dining Table & 2 Black Benches For Family Dining Room", "table"),
            ("Furniture > Furniture Sets > Living Room Furniture Sets",
             "Ascot Green 3+2 Sofa Set – Fabric Living Room Sofa Suite", "sofa"),
            ("Furniture > Futon Pads", "Kids Foldable Z Bed Kids Futon Sofa Bed Folding Mattress", "bed"),
            ("Luggage & Bags > Shopping Totes", "Organic Cotton Blue Crochet Tote Bag", "bag"),
            ("Toys & Games > Outdoor Play Equipment > Play Tents & Tunnels",
             "Children's 5 Piece Colourful Outdoor Plastic Golf Set Toy", "toy"),
            ("Health & Beauty > Personal Care > Massage & Relaxation > Massagers > Electric Massagers",
             "Handheld Body Massager - Deep Tissue Percussion Massager", "massager"),
        ):
            with self.subTest(title=title):
                self.assertIn(kind, _kinds(category, title))

    def test_no_aisle_of_googles_leaves_the_title_to_decide(self) -> None:
        # A shop's own shelf, and no category at all, as before.
        self.assertIn(
            "barbell", _kinds("Body Jewellery", "G23 Titanium Gold Anodised Circular Barbell with Ball - 6mm")
        )
        self.assertIn("kettle", _kinds("", "Fixturon Electric Kettle"))

    def test_a_shelf_that_names_the_kind_still_decides(self) -> None:
        # The rule is the title's only: a shelf naming a kind is read as before.
        self.assertIn(
            "kettle",
            _kinds("Home & Garden > Kitchen & Dining > Kitchen Appliances > Kettles", "Fixturon 1.7L Rapid Boil"),
        )


if __name__ == "__main__":
    unittest.main()
