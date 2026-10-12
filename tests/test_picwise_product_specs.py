"""What the feed states about a product, and which of it may rank the four.

Owner instruction, 2026-10-12: always read a product's specifications when the feed
carries them, cross-checking a number against a second source where that is feasible.
It is not feasible in the feed PicWise has -- of the numbers that appear only in a
description, none is repeated by any other column (0 of 107 for speakers, 0 of 90 for
headphones, 0 of 28 for cameras). So the corroboration used instead is that the feed
must state the number **as a property**: directly in `specifications`, or in a title
or product type, which a merchant writes on purpose, or in a description where a word
names the property just before the number.

Which properties may decide a recommendation is a separate matter, and the owner left
it to PicWise after seeing the coverage: only where "more is better" is beyond dispute
(storage, battery, playtime). Power does not rank -- a louder amplifier is not a
better one -- and length does not rank by the owner's explicit answer: a buyer wants
the cable that fits, not the longest, so it is shown and decides nothing.

Rows here are local test data, in the shapes the first real feed used.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.product_specs import (  # noqa: E402
    RANKING_PROPERTIES,
    read_product_specs,
    ranking_spec,
)


def _specs(title: str = "", **raw: str) -> dict[str, object]:
    return {spec.property_id: spec for spec in read_product_specs(raw, title=title)}


class DeclaredFieldTests(unittest.TestCase):
    """A title or product type is words the merchant chose: no label needed."""

    def test_a_number_with_a_unit_in_the_title_is_a_specification(self) -> None:
        found = _specs("Nedis Balanced Audio Cable | 2x XLR 3-Pin Male | 1.5 m")
        self.assertIn("length", found)
        self.assertAlmostEqual(found["length"].value, 1.5)
        self.assertEqual(found["length"].unit, "m")
        self.assertEqual(found["length"].source, "title")

    def test_millimetres_and_centimetres_become_metres(self) -> None:
        self.assertAlmostEqual(_specs("Fixturon Driver 40 mm")["length"].value, 0.04)
        self.assertAlmostEqual(_specs("Fixturon Stand 30cm")["length"].value, 0.30)

    def test_terabytes_become_gigabytes(self) -> None:
        self.assertAlmostEqual(_specs("Testline Drive 2TB")["storage"].value, 2048.0)

    def test_the_product_type_is_read_like_a_title(self) -> None:
        found = _specs("Testline Model 7", product_type="Monitors 27 inch")
        self.assertEqual(found["screen"].source, "product_type")
        self.assertAlmostEqual(found["screen"].value, 27.0)

    def test_a_ram_figure_is_not_storage(self) -> None:
        # The kind whose recommendation storage decides writes both in its title, and
        # ranking by the 4 instead of the 64 would rank the wrong number.
        found = _specs("G96 Android TV Box 4GB RAM 64GB ROM")
        self.assertAlmostEqual(found["storage"].value, 64.0)
        self.assertAlmostEqual(found["memory"].value, 4.0)
        self.assertEqual(ranking_spec(tuple(found.values())).value, 64.0)

    def test_a_unit_inside_a_longer_word_is_not_a_unit(self) -> None:
        # "2 Win", "4 Games": the letter is the start of a word, not a watt.
        self.assertNotIn("power", _specs("Fixturon Console 4 Games Included"))
        self.assertNotIn("power", _specs("Fixturon Deal 2 Winter Bundles"))


class SpecificationColumnTests(unittest.TestCase):
    """The column states properties by construction, so its numbers are read."""

    def test_a_key_and_value_pair_is_read(self) -> None:
        found = _specs("Fixturon Box", specifications="Storage: 64 GB, Power output: 50W")
        self.assertAlmostEqual(found["storage"].value, 64.0)
        self.assertAlmostEqual(found["power"].value, 50.0)
        self.assertEqual(found["storage"].source, "specifications")

    def test_a_unit_written_in_the_key_still_reads(self) -> None:
        # The real feed's shape: "Colour -: Black, Extended Length (mm): 610".
        found = _specs("Fixturon Bar", specifications="Colour -: Black, Extended Length (mm): 610")
        self.assertAlmostEqual(found["length"].value, 0.61)
        self.assertEqual(found["length"].source, "specifications")

    def test_a_pair_with_no_number_states_nothing(self) -> None:
        self.assertEqual(_specs("Fixturon Bar", specifications="Colour: Black, Finish: Matte"), {})

    def test_the_column_outranks_a_description(self) -> None:
        found = _specs(
            "Fixturon Box",
            specifications="Storage: 64 GB",
            description="Storage 16 GB of onboard space for your apps and games.",
        )
        self.assertAlmostEqual(found["storage"].value, 64.0)
        self.assertEqual(found["storage"].source, "specifications")


class DescriptionTests(unittest.TestCase):
    """Marketing copy: only a number a word names counts."""

    def test_a_labelled_number_is_a_specification(self) -> None:
        # The real feed's own wording, from a headphone description.
        found = _specs(
            "Nedis Headphones HPWD1100BK",
            description="Driver Diameter 40 mm Impedance 32 Ohm Frequency Response 20Hz-20KHz",
        )
        self.assertAlmostEqual(found["impedance"].value, 32.0)
        self.assertAlmostEqual(found["frequency"].value, 20.0)
        self.assertEqual(found["impedance"].source, "description")

    def test_an_unlabelled_number_in_prose_states_nothing(self) -> None:
        self.assertEqual(
            _specs("Testline Speaker", description="Take it anywhere, 3 of your friends will too."),
            {},
        )

    def test_a_hedged_number_states_nothing(self) -> None:
        for prose in (
            "Battery life: up to 9 hours of playback",
            "Louder than 50 W of the nearest rival",
            "Compatible with 3.5 mm devices",
            "Works with 128 GB cards",
            "Suitable for 32 inch screens",
        ):
            with self.subTest(prose=prose):
                self.assertEqual(_specs("Testline Earbuds", description=prose), {})

    def test_a_plain_statement_of_the_property_is_read(self) -> None:
        found = _specs("Testline Earbuds", description="Battery: 3000mAh. Playtime 9 hours.")
        self.assertAlmostEqual(found["battery"].value, 3000.0)
        self.assertAlmostEqual(found["playtime"].value, 9.0)

    def test_a_comparison_is_never_read_as_the_product_s_own_number(self) -> None:
        self.assertEqual(_specs("Fixturon TV", description="Better than 32 inch models."), {})

    def test_the_short_description_is_read_too(self) -> None:
        found = _specs("Testline Cable", product_short_description="Cable length 3 m, braided.")
        self.assertAlmostEqual(found["length"].value, 3.0)


class RankingTests(unittest.TestCase):
    def test_only_the_owner_s_properties_rank(self) -> None:
        self.assertEqual(RANKING_PROPERTIES, frozenset({"storage", "battery", "playtime"}))

    def test_power_is_read_but_never_ranks(self) -> None:
        # A louder amplifier is not a better one, so the figure is shown, not ranked.
        found = _specs("Fixturon Amplifier 2x50W")
        self.assertAlmostEqual(found["power"].value, 50.0)
        self.assertFalse(found["power"].ranks)
        self.assertIsNone(ranking_spec(tuple(found.values())))

    def test_length_is_read_but_never_ranks(self) -> None:
        # Owner's answer, 2026-10-12: shown on the card, decides nothing.
        found = _specs("Nedis Cable 1.5 m")
        self.assertAlmostEqual(found["length"].value, 1.5)
        self.assertFalse(found["length"].ranks)
        self.assertIsNone(ranking_spec(tuple(found.values())))

    def test_storage_and_battery_rank(self) -> None:
        self.assertTrue(_specs("Testline Box 64GB")["storage"].ranks)
        self.assertTrue(_specs("Testline Bank 20000mAh")["battery"].ranks)

    def test_a_product_with_nothing_stated_ranks_by_nothing(self) -> None:
        self.assertIsNone(ranking_spec(read_product_specs({}, title="Fixturon Tote Bag")))

    def test_the_same_property_is_chosen_for_every_product(self) -> None:
        # Two products each stating storage and playtime must rank on the same one,
        # or the four are compared on different measures and the rank means nothing.
        one = ranking_spec(read_product_specs(
            {"description": "Storage 64 GB. Playtime 9 hours."}, title="Testline A"))
        two = ranking_spec(read_product_specs(
            {"description": "Playtime 20 hours. Storage 32 GB."}, title="Testline B"))
        self.assertEqual(one.property_id, two.property_id)


if __name__ == "__main__":
    unittest.main()
