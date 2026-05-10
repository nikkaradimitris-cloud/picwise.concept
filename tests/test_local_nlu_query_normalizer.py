from __future__ import annotations

import unittest

from src.picwise_nlu.normalizer import (
    collapse_query_whitespace,
    normalize_query,
    normalize_tire_size_text,
    strip_diacritics,
)


class LocalNLUQueryNormalizerTests(unittest.TestCase):
    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(normalize_query(""), "")

    def test_whitespace_only_returns_empty(self) -> None:
        self.assertEqual(normalize_query(" \t \n "), "")

    def test_none_input_safe_behavior(self) -> None:
        self.assertEqual(normalize_query(None), "")

    def test_repeated_spaces_tabs_newlines_collapsed(self) -> None:
        self.assertEqual(
            collapse_query_whitespace("best\t\tdeals\n\nfor   tyres"),
            "best deals for tyres",
        )

    def test_lowercase_normalization(self) -> None:
        self.assertEqual(normalize_query("BEST Tyres NOW"), "best tyres now")

    def test_greek_tonos_stripping(self) -> None:
        self.assertEqual(strip_diacritics("λάστιχα για αυτοκίνητο"), "λαστιχα για αυτοκινητο")

    def test_mixed_greek_english_query_cleanup(self) -> None:
        result = normalize_query("  ΘΕΛΩ  Tyres\t195 65 r15 !!! ")
        self.assertEqual(result, "θελω tyres 195/65 R15")

    def test_tire_size_spaces_format(self) -> None:
        self.assertEqual(normalize_query("195 65 15"), "195/65 R15")

    def test_tire_size_slashes_format(self) -> None:
        self.assertEqual(normalize_query("195/65/15"), "195/65 R15")

    def test_tire_size_dashes_format(self) -> None:
        self.assertEqual(normalize_query("195-65-15"), "195/65 R15")

    def test_tire_size_with_r_spacing_format(self) -> None:
        self.assertEqual(normalize_query("195 65 r15"), "195/65 R15")
        self.assertEqual(normalize_query("195 65 R 15"), "195/65 R15")

    def test_tire_size_compact_r_format(self) -> None:
        self.assertEqual(normalize_query("195/65R15"), "195/65 R15")

    def test_noisy_punctuation_around_tire_size(self) -> None:
        self.assertEqual(normalize_query("### (195-65-15) !!!"), "195/65 R15")

    def test_no_typo_correction_yet_goodyar_unchanged(self) -> None:
        self.assertEqual(normalize_query("Goodyar 195 65 15"), "goodyar 195/65 R15")

    def test_no_brand_model_category_guessing(self) -> None:
        result = normalize_query("θελω goodyar corola 195 65 15")
        self.assertIn("goodyar", result)
        self.assertIn("corola", result)
        self.assertNotIn("goodyear", result)
        self.assertNotIn("bridgestone", result)
        self.assertEqual(result, "θελω goodyar corola 195/65 R15")

    def test_non_plausible_three_numbers_not_forced_to_tire_size(self) -> None:
        self.assertEqual(normalize_tire_size_text("2024 05 10"), "2024 05 10")


if __name__ == "__main__":
    unittest.main()
