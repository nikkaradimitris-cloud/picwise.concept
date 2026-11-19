"""What a card says of its product's variants at the shop (owner, 2026-11-19).

The owner, shown a drawing of the card: a shop's variants on one page, or each a product
of its own, are one card «δείχνουμε τις διαφορετικές παραλλαγές στην ίδια κάρτα». Pinned
here: from one shop's titles of one product, the colours, sizes, capacities, power and
other options a buyer picks, in an order a buyer reads (sizes small to large, the card's
own colour first); a part several titles share and no variant, left out; and no line at
all when a title differs in two things of a kind or in words that name no variant. The
titles are those seen in the AI's first answers (19/11) and fictional ones.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.variant_names import variant_values  # noqa: E402


class VariantValuesTests(unittest.TestCase):
    def test_colours_sizes_capacities_and_power(self) -> None:
        self.assertEqual(
            variant_values(["Alienware AW420K Tenkeyless Gaming Keyboard - Black",
                            "Alienware AW420K Tenkeyless Gaming Keyboard - White"]),
            (("colours", ("Black", "White")),),
        )
        self.assertEqual(
            variant_values(["Dominate Tracksuit - 2XL", "Dominate Tracksuit - S", "Dominate Tracksuit - M"]),
            (("sizes", ("S", "M", "2XL")),),
        )
        self.assertEqual(
            variant_values(["Fixturon Runner Trainers Black Size 10", "Fixturon Runner Trainers White Size 7",
                            "Fixturon Runner Trainers Black Size 8"]),
            (("colours", ("Black", "White")), ("sizes", ("7", "8", "10"))),
        )
        self.assertEqual(
            variant_values(["Refurbished iPhone 16 Plus 128GB | Unlocked - Black / Premium Refurbished",
                            "Refurbished iPhone 16 Plus 256GB | Unlocked - Green / Premium Refurbished"]),
            (("colours", ("Black", "Green")), ("capacities", ("128GB", "256GB"))),
        )
        self.assertEqual(
            variant_values(["Seasonic CORE GC-850 ATX 3.1 power supply unit 850 W 20+4 pin ATX Black",
                            "Seasonic CORE GC-650 ATX 3.1 power supply unit 650 W 24-pin ATX Black",
                            "Seasonic CORE GC-750 ATX 3.1 power supply unit 750 W 20+4 pin ATX Black"]),
            (("power", ("650 W", "750 W", "850 W")),),
        )
        self.assertEqual(
            variant_values(["Moroccanoil Color Care Shampoo - 250 ml", "Moroccanoil Color Care Shampoo - 70 ml"]),
            (("sizes", ("70 ml", "250 ml")),),
        )
        self.assertEqual(
            variant_values(["Kajo 1 Full Spectrum Infrared Sauna (Hemlock) – 1 Person",
                            "Kajo 2 Full Spectrum Infrared Sauna (Hemlock) – 2 Person"]),
            (("sizes", ("1 Person", "2 Person")),),
        )
        self.assertEqual(
            variant_values(["The Bear Colour Tracksuit - GRAY / 12-18 M", "The Bear Colour Tracksuit - Pink / 3-4 Y"]),
            (("colours", ("Gray", "Pink")), ("sizes", ("3-4 Y", "12-18 M"))),
        )

    def test_prints_and_finishes_are_options_the_card_s_own_first(self) -> None:
        self.assertEqual(
            variant_values(["Satin Sleep Mask - Frosted Cherry Print", "Satin Sleep Mask - Snake Print - Sleep Mask Only",
                            "Satin Sleep Mask - Black - Sleep Mask Only", "Satin Sleep Mask - Cheetah Print - Sleep Mask Only"]),
            (("options", ("Frosted Cherry Print", "Snake Print", "Black", "Cheetah Print")),),
        )
        self.assertEqual(
            variant_values(["Bali 6 Drawer Wide Chest - Grey Oak", "Bali 6 Drawer Wide Chest - Light Oak"]),
            (("options", ("Grey Oak", "Light Oak")),),
        )

    def test_no_line_when_the_titles_do_not_read_as_variants(self) -> None:
        # The same candle listed twice, in other words.
        self.assertEqual(variant_values([
            "New Home Candle - Housewarming Gift | Luxury Vanilla Soy 220g",
            "New Home Candle, New Home Gifts, Funny Housewarming Gifts, Luxury Scented Vanilla Candle Natural Soy 220g",
        ]), ())
        # Two capacities in one title (storage and memory): not one variant.
        self.assertEqual(variant_values([
            "Fixturon Pro 13 Ultra 5 256 GB 16 GB Windows 11 Platinum",
            "Fixturon Pro 13 Ultra 7 512 GB 32 GB Windows 11 Platinum",
        ]), ())
        # A model's number apart, no variant named.
        self.assertEqual(variant_values(["Fixturon Lamp 100", "Fixturon Lamp 200"]), ())
        self.assertEqual(variant_values(["Fixturon Lamp - Black"]), ())
        self.assertEqual(variant_values(["Fixturon Lamp - Black", "Fixturon Lamp - Black"]), ())

    def test_a_value_once_and_a_size_with_its_measure(self) -> None:
        self.assertEqual(
            variant_values(['Blaklader 1449 Cargo Shorts Stone/Black 33" Waist - Stone / Black / 33" Waist',
                            'Blaklader 1449 Cargo Shorts - Stone / Black / 30" Waist']),
            (("sizes", ('30" Waist', '33" Waist')),),
        )
        self.assertEqual(
            variant_values(["Black Faux Fur Duchess Maxi Coat - L-XL / Black / Faux Fur",
                            "Green Faux Fur Duchess Maxi Coat - S-M / Green / Faux Fur"]),
            (("colours", ("Black", "Green")), ("sizes", ("S-M", "L-XL"))),
        )


class CardLineTests(unittest.TestCase):
    def test_the_card_names_six_and_how_many_more(self) -> None:
        from picwise_surface.reference import _variant_lines

        self.assertEqual(
            _variant_lines((("colours", ("Black", "White")), ("sizes", tuple(f"UK {n}" for n in range(3, 12))))),
            ["Colours at the shop: Black, White", "Sizes at the shop: UK 3, UK 4, UK 5, UK 6, UK 7, UK 8 +3 more"],
        )
        self.assertEqual(_variant_lines((("colours", ("Black",)),)), [])
        self.assertEqual(_variant_lines(None), [])


if __name__ == "__main__":
    unittest.main()
