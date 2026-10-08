"""The misspelling generators produce the errors people actually make, deterministically.

The benchmark built from them is only meaningful if the variants are realistic, so the
known renderings of real words are pinned here.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app.nlu_benchmark import (  # noqa: E402
    BENCHMARK_PRODUCTS,
    HELD_OUT_QUERIES,
    NEGATIVE_QUERIES,
    build_misspelling_benchmark,
)
from picwise_nlu.misspelling_variants import (  # noqa: E402
    english_layout_text_to_greek,
    greek_final_sigma_error,
    greek_typed_on_english_layout,
    greek_vowel_confusion_variants,
    joined_words,
    strip_greek_accents,
    transliterate_greek,
)


class GreekVariantTests(unittest.TestCase):
    def test_accents_are_stripped_and_final_sigma_kept(self) -> None:
        self.assertEqual(strip_greek_accents("πλυντήριο ρούχων"), "πλυντηριο ρουχων")
        self.assertEqual(strip_greek_accents("εκτυπωτής"), "εκτυπωτης")

    def test_vowel_confusion_is_a_homophone_error(self) -> None:
        variants = greek_vowel_confusion_variants("πλυντήριο ρούχων")
        self.assertIn("πλιντηριο ρουχων", variants)
        # The ο of "ου" is part of a different sound and is never swapped for ω.
        self.assertTrue(all("ρωυχ" not in variant for variant in variants))

    def test_final_sigma_error(self) -> None:
        self.assertEqual(greek_final_sigma_error("εκτυπωτής"), "εκτυπωτησ")

    def test_joined_words(self) -> None:
        self.assertEqual(joined_words("κρανος ποδηλατου"), "κρανοςποδηλατου")


class GreeklishTests(unittest.TestCase):
    def test_the_common_transliteration_habits(self) -> None:
        word = "πλυντήριο ρούχων"
        self.assertEqual(transliterate_greek(word, "greeklish_standard"), "plyntirio rouchon")
        self.assertEqual(transliterate_greek(word, "greeklish_phonetic"), "plintirio rouhon")
        self.assertEqual(transliterate_greek(word, "greeklish_visual"), "plynthrio rouxwn")

    def test_word_initial_mp_is_written_b_by_sound(self) -> None:
        self.assertEqual(transliterate_greek("μπαταρία", "greeklish_phonetic"), "bataria")

    def test_wrong_keyboard_layout_round_trips(self) -> None:
        self.assertEqual(greek_typed_on_english_layout("ψυγείο"), "cygeio")
        self.assertEqual(english_layout_text_to_greek("cygeio"), "ψυγειο")
        self.assertEqual(english_layout_text_to_greek("ektypvtiw"), "εκτυπωτις")


class BenchmarkCaseListTests(unittest.TestCase):
    def test_the_case_list_is_deterministic(self) -> None:
        self.assertEqual(build_misspelling_benchmark(), build_misspelling_benchmark())

    def test_every_held_out_query_keeps_its_held_out_label(self) -> None:
        held_out = {
            " ".join(case.query.lower().split())
            for case in build_misspelling_benchmark()
            if case.source == "held_out"
        }
        expected = {" ".join(query.lower().split()) for query, _ in HELD_OUT_QUERIES}
        self.assertEqual(held_out, expected)

    def test_negatives_expect_no_product(self) -> None:
        negatives = [c for c in build_misspelling_benchmark() if c.source == "negative"]
        self.assertEqual(len(negatives), len(NEGATIVE_QUERIES))
        self.assertTrue(all(not c.expected_product_type for c in negatives))

    def test_every_product_type_has_greek_and_greeklish_cases(self) -> None:
        cases = build_misspelling_benchmark()
        for product in BENCHMARK_PRODUCTS:
            languages = {
                c.language for c in cases if c.expected_product_type == product.product_type
            }
            with self.subTest(product=product.product_type):
                self.assertTrue({"en", "el", "greeklish"} <= languages)


if __name__ == "__main__":
    unittest.main()
