from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.query_variant_generator import (  # noqa: E402
    generate_generic_english_noisy_variants,
    generate_noisy_variants_for_term,
)

_FORBIDDEN_FIELDS = {"product", "products", "offer", "offers", "price", "prices", "affiliate", "affiliate_url"}


def _collect_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key).lower())
            keys |= _collect_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            keys |= _collect_keys(nested)
    return keys


class Stage3GenericEnglishNoisyVariantGeneratorTests(unittest.TestCase):
    def test_term_level_generator_produces_required_variant_shapes(self) -> None:
        coffee_variants = generate_noisy_variants_for_term("coffee grinder", "home_living")
        by_type = {row["variant_type"] for row in coffee_variants}
        self.assertIn("missing_letter", by_type)
        self.assertIn("extra_letter", by_type)
        self.assertIn("swapped_adjacent_letters", by_type)
        self.assertIn("repeated_letter", by_type)
        self.assertIn("joined_words", by_type)
        self.assertIn("vowel_drop", by_type)

    def test_us_uk_variant_generation(self) -> None:
        tyre_variants = generate_noisy_variants_for_term("car tyre", "auto_moto")
        uk_us_rows = [row for row in tyre_variants if row["variant_type"] == "us_uk_spelling"]
        self.assertGreater(len(uk_us_rows), 0)
        self.assertIn("car tire", {row["variant"] for row in uk_us_rows})

    def test_deduplication_by_canonical_variant_and_category(self) -> None:
        vocab = {
            "auto_moto": {"car tyre", "car tyre", "car    tyre"},
        }
        rows = generate_generic_english_noisy_variants(vocab)
        signatures = {(row["canonical_term"], row["variant"], row["mega_category_id"]) for row in rows}
        self.assertEqual(len(rows), len(signatures))

    def test_safe_minimum_length_guard(self) -> None:
        rows = generate_noisy_variants_for_term("usb", "tech_electronics", min_variant_length=4)
        self.assertEqual(rows, [])

    def test_canonical_mapping_preserved_on_all_rows(self) -> None:
        rows = generate_noisy_variants_for_term("vacuum cleaner", "home_living")
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(row["canonical_term"] == "vacuum cleaner" for row in rows))

    def test_multiple_mega_categories_supported(self) -> None:
        vocab = {
            "home_living": {"coffee grinder", "vacuum cleaner"},
            "tech_electronics": {"bluetooth speaker", "gaming mouse", "usb cable"},
            "auto_moto": {"car battery"},
            "sports_outdoor": {"bike helmet"},
            "tools_garden": {"garden shears"},
            "fashion": {"winter jacket"},
            "baby_family": {"baby car seat"},
        }
        rows = generate_generic_english_noisy_variants(vocab)
        categories = {row["mega_category_id"] for row in rows}
        self.assertEqual(
            categories,
            {"home_living", "tech_electronics", "auto_moto", "sports_outdoor", "tools_garden", "fashion", "baby_family"},
        )

    def test_output_contract_fields_present(self) -> None:
        rows = generate_noisy_variants_for_term("gaming mouse", "tech_electronics")
        self.assertGreater(len(rows), 0)
        required = {"canonical_term", "variant", "mega_category_id", "variant_type", "source", "generator_version"}
        for row in rows:
            self.assertEqual(set(row.keys()), required)

    def test_no_product_offer_price_or_affiliate_fields(self) -> None:
        rows = generate_noisy_variants_for_term("baby car seat", "baby_family")
        keys = _collect_keys(rows)
        self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(keys))


if __name__ == "__main__":
    unittest.main()
