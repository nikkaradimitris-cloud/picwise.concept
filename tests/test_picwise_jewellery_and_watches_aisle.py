"""An aisle that holds a kind together with something PicWise has no kind for.

Owner, 2026-10-25, «ναι, ξεκίνα με το ρολόι»: on the server's feed of every
Google-format shop, "watch" held 169,271 shown products and 167,551 of their titles named
no watch; the cheapest were piercing aftercare oil and ear expanders on "Body
Jewellery". A breadcrumb is read from the widest aisle down and the first shelf naming a
product decides, so "Jewellery & Watches > Body Jewellery" was a watch: the aisle names
watches, and jewellery is no kind PicWise knows. Such an aisle now gives its kind only
when the title names it; otherwise the narrower shelf decides. The narrowest shelf keeps
its kind as before ("Skillets & Frying Pans" are cookware, and a bare "Jewellery &
Watches" shelf still reads as watches).

The titles are the shops' own, from the server's list of 2026-10-25, or written in the
same shape with fictional brands; the shelves are as the shops most likely file them.
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

from picwise_nlu.concept_understanding import annotate_product_concepts  # noqa: E402


def _kinds(category: str, title: str) -> set[str]:
    return set(annotate_product_concepts("", category.lower(), title))


class AnAisleOfAKindAndAnUnknownThingTests(unittest.TestCase):
    def test_jewellery_under_the_aisle_is_no_watch(self) -> None:
        for category, title in (
            ("Jewellery & Watches > Body Jewellery", "Jojoba Healing Oil Roll-On – Piercing Aftercare"),
            ("Jewellery & Watches > Body Jewellery", "316L Surgical Hollow Ear Expander - 3mm / Single Piece"),
            ("Jewellery & Watches > Pendants", "Fixturon 18K Gold Diamond Heart Pendant"),
            ("Apparel & Accessories > Jewellery & Watches > Body Jewellery", "G23 Titanium Circular Barbell - 6mm"),
        ):
            with self.subTest(category=category, title=title):
                self.assertNotIn("watch", _kinds(category, title))

    def test_the_narrower_shelf_decides(self) -> None:
        for category, title, kind in (
            ("Jewellery & Watches > Rings", "Fixturon 18K Gold Diamond Solitaire Engagement Ring", "ring"),
            ("Jewellery & Watches > Earrings", "Diamond Stud Earrings - 1.00 Carat / G-H / VS1-VS2", "earrings"),
            ("Jewellery & Watches > Watches", "Fixturon F-91W Classic", "watch"),
        ):
            with self.subTest(category=category, title=title):
                self.assertIn(kind, _kinds(category, title))

    def test_a_title_naming_the_aisles_kind_keeps_it(self) -> None:
        self.assertIn(
            "watch",
            _kinds("Jewellery & Watches > Gifts", "Ravel Men's White Dial Brown Leather Strap Watch"),
        )

    def test_the_narrowest_shelf_keeps_its_kind(self) -> None:
        # Nothing narrower can decide: read as before.
        self.assertIn("watch", _kinds("Jewellery & Watches", "Fixturon F-91W Classic"))
        self.assertIn(
            "cookware",
            _kinds(
                "Home & Garden > Kitchen & Dining > Cookware & Bakeware > Cookware > Skillets & Frying Pans",
                "24cm Grey Die-Cast Aluminium Skillet with Durable Coating",
            ),
        )

    def test_an_aisle_of_two_known_kinds_or_of_one_product_is_read_as_before(self) -> None:
        self.assertEqual(_kinds("Fans & Heaters > Tower Fans", "Testline Tower Fan 30 inch"), {"fan"})
        self.assertIn(
            "coffee_machine",
            _kinds(
                "Kitchen Appliances > Coffee Makers & Espresso Machines > Espresso Machines",
                "Fixturon Barista Pro Espresso Machine",
            ),
        )

    def test_an_access_point_is_no_router_and_a_routers_shelf_still_is(self) -> None:
        # Of the 5,595 shelves of Google's taxonomy, read with no title, only two changed
        # (measured 2026-10-25): network bridges and wireless access points under
        # "Bridges & Routers" are no routers any more.
        self.assertNotIn(
            "router",
            _kinds("Electronics > Networking > Bridges & Routers > Wireless Access Points", "Fixturon AX3000"),
        )
        self.assertIn(
            "router",
            _kinds("Electronics > Networking > Bridges & Routers > VoIP Gateways & Routers", "Fixturon VR-2"),
        )


if __name__ == "__main__":
    unittest.main()
