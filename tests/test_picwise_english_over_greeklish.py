"""English before greeklish: step 2 of the owner's build order, 2026-10-16.

Measured on the third real Awin feed the same day: "patio set" and "patio heater"
answered with insoles, because "patio" was read as the greeklish of «πάτοι». A word
PicWise knows as English is not read as the greeklish of a Greek name of another kind
("scales" is not «σκάλες», ladders). A greeklish reading that names the same kind stays
("consoles" and «κονσόλες»), and greeklish that is not an English word is read as before.
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

from picwise_nlu.concept_understanding import understand_product_query  # noqa: E402


def _concept(query: str) -> str | None:
    return understand_product_query(query).concept_id


class EnglishOverGreeklishTests(unittest.TestCase):
    def test_an_english_word_is_not_read_as_greeklish_of_another_kind(self) -> None:
        self.assertEqual(_concept("patio set"), "garden_furniture")
        reading = understand_product_query("patio heater")
        self.assertEqual(reading.concept_id, "heater")
        self.assertIn("patio", reading.filters)
        self.assertEqual(_concept("patio furniture"), "garden_furniture")
        self.assertNotEqual(_concept("patio"), "insoles")
        self.assertNotEqual(_concept("scales"), "ladder")
        self.assertEqual(_concept("kitchen scales"), "kitchen_scale")

    def test_a_greeklish_reading_of_the_same_kind_stays(self) -> None:
        for query, concept in (
            ("consoles", "game_console"),
            ("laptop", "laptop"),
            ("tablet", "tablet"),
            ("mixer", "mixer"),
        ):
            with self.subTest(query=query):
                self.assertEqual(_concept(query), concept)

    def test_greeklish_that_is_not_english_is_read_as_before(self) -> None:
        for query, concept in (
            ("patoi", "insoles"),
            ("anatomikoi patoi", "insoles"),
            ("πάτοι", "insoles"),
            ("skales", "ladder"),
            ("kamera", "camera"),
            ("plintirio rouhon", "washing_machine"),
        ):
            with self.subTest(query=query):
                self.assertEqual(_concept(query), concept)


if __name__ == "__main__":
    unittest.main()
