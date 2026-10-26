"""Kinds the shops' own types named that the vocabulary did not know.

Owner, 2026-10-26: «Ναι» to adding the kinds of the types the bot's first round found
naming none (run 40329354654: 18,176 rows, most of Back to the Office, so few of its
computers and network products were shown): "PCs/Workstations" (795), "Network
Switches" (708), "Network Media Converters" (590), "Network Cards" (378), "Security
Software" (361), "Outdoor Sauna" (336), "Networking Software" (328), "Video Games" (291).
"Sold Out" and "Made-to-Measure" name no product and stay so.

Pinned here: each type gives its kind, also with its shop's title, and the look-alikes
stay what they were: a console, a sauna's bucket or suit, a Nintendo Switch, a book on
software. The types are the shops' own; the titles are written in their shape, with
fictional brands where they are not the shops'.
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

from picwise_nlu.concept_understanding import ACCESSORY_MARKER, UNCERTAIN_MARKER, annotate_product_concepts  # noqa: E402


def _kinds(product_type: str, title: str, category: str = "") -> set[str]:
    return set(annotate_product_concepts(product_type, category or product_type.lower(), title))


class ShopTypesTests(unittest.TestCase):
    def test_each_type_gives_its_kind(self) -> None:
        for product_type, title, kind in (
            ("PCs/Workstations", "Fixturon Precision Tower Workstation Core i7 32GB", "desktop_pc"),
            ("Network Switches", "Fixturon 8-Port Gigabit Ethernet Switch", "network_switch"),
            ("Network Media Converters", "Fixturon Gigabit Media Converter SFP", "media_converter"),
            ("Network Cards", "Fixturon Quad Port Network Card", "network_card"),
            ("Security Software", "Fixturon Internet Security 5 Devices 1 Year", "software"),
            ("Networking Software", "Fixturon Licence 3 Year", "software"),
            # Once `test_picwise_strict_kind_reading`'s type the lexicon lacked.
            ("Networking Software", "Testline DXS-36 networking software Switch / Router 1 license", "software"),
            ("Video Games", "Fixturon Football 24 PS5", "video_game"),
            ("Outdoor Sauna", "Fixturon Barrel Sauna 4 Person Thermowood", "sauna"),
        ):
            with self.subTest(product_type=product_type):
                self.assertIn(kind, _kinds(product_type, title))
                # The type names it by itself, as the shops' catalogues need.
                self.assertIn(kind, _kinds(product_type, ""))

    def test_look_alikes_stay_what_they_were(self) -> None:
        self.assertEqual(_kinds("", "Sony PlayStation 5 Console", "Electronics > Video Game Consoles"), {"game_console"})
        self.assertEqual(
            _kinds("", "Wooden Sauna Bucket", "Home & Garden > Pool & Spa > Sauna Accessories"), {ACCESSORY_MARKER}
        )
        self.assertEqual(
            _kinds("", "Fixturon Sauna Suit", "Sporting Goods > Exercise & Fitness > Sauna Suits"), {UNCERTAIN_MARKER}
        )
        self.assertEqual(set(annotate_product_concepts("", "", "Nintendo Switch OLED Console")), set())
        self.assertEqual(set(annotate_product_concepts("", "", "Fixturon Software Engineering Handbook")), set())

    def test_the_second_list_of_types_gives_its_kinds(self) -> None:
        # Owner, 2026-10-26: «Ναι παίρνω και αυτά τα είδη», after the note's longer list
        # (run 40351335007).
        for product_type, title, kinds in (
            ("Memory Cards", "Fixturon 128GB microSD Card with Adapter", {"memory_card"}),
            ("Servers", "Fixturon PowerEdge T150 Tower Server", {"server"}),
            ("Console Servers", "Fixturon 16-Port Console Server", {"server"}),
            ("Hardware Firewalls", "Fixturon 40F Firewall", {"firewall"}),
            ("Wireless Access Points", "Fixturon U6 Access Point", {"access_point"}),
            ("Industrial Rechargeable Batteries", "Fixturon 12V 7Ah Rechargeable Battery", {"battery"}),
            ("Household Batteries", "Fixturon AA Batteries 24 Pack", {"battery"}),
            ("Bedding", "Fixturon Duvet 10.5 Tog Double", {"bedding", "duvet"}),
            ("Bedding", "Fixturon Fitted Sheet Double", {"bedding"}),
            ("Sweatshirts", "Fixturon Crew Neck Sweatshirt Grey", {"hoodie"}),
            ("Ballpoint Pens", "Fixturon Ballpoint Pen Blue 50 Pack", {"pen"}),
            ("Markers", "Fixturon Whiteboard Markers 4 Pack", {"marker"}),
            ("Ring Binders", "Fixturon A4 Ring Binder 2 Ring", {"folder"}),
            ("Folders", "Fixturon A4 Document Folder", {"folder"}),
            ("Power Supply Units", "Fixturon 650W Power Supply Unit", {"power_supply"}),
        ):
            with self.subTest(product_type=product_type, title=title):
                self.assertEqual(_kinds(product_type, title), kinds)

    def test_the_second_lists_look_alikes_stay_what_they_were(self) -> None:
        self.assertEqual(
            _kinds("", "Fixturon Salad Servers Bamboo",
                   "Home & Garden > Kitchen & Dining > Tableware > Serveware > Serving Utensils"),
            {UNCERTAIN_MARKER},
        )
        self.assertEqual(
            _kinds("", "Fixturon Plant Markers 50 Pack", "Home & Garden > Lawn & Garden > Gardening > Plant Labels"),
            {UNCERTAIN_MARKER},
        )
        for title, kinds in (
            ("Fixturon Pen Drive 64GB", {"usb_flash_drive"}),
            ("Fixturon Battery Lawn Mower 40V", {"lawn_mower"}),
            ("Fixturon Car Battery 12V 70Ah", {"car_battery"}),
            ("Fixturon External Battery 10000mAh", {"power_bank"}),
        ):
            with self.subTest(title=title):
                self.assertEqual(set(annotate_product_concepts("", "", title)), kinds)
        # A Greek "μπαταρία κουζίνας" is still a tap, not a battery.
        self.assertEqual(set(annotate_product_concepts("", "", "μπαταρία κουζίνας")), {"tap"})

    def test_types_naming_no_product_stay_so(self) -> None:
        for product_type in ("Sold Out", "Made-to-Measure"):
            with self.subTest(product_type=product_type):
                self.assertFalse({kind for kind in _kinds(product_type, "") if not kind.startswith("__")})


if __name__ == "__main__":
    unittest.main()
