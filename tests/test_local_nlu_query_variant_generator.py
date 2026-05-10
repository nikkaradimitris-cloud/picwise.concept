from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.query_variant_generator import (  # noqa: E402
    generate_variants_for_training_pack,
    get_default_training_seeds,
)


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


class LocalNLUQueryVariantGeneratorTests(unittest.TestCase):
    def test_default_seeds_non_empty(self) -> None:
        seeds = get_default_training_seeds()
        self.assertIsInstance(seeds, list)
        self.assertGreater(len(seeds), 0)

    def test_variants_generated_for_all_required_seed_families(self) -> None:
        variants = generate_variants_for_training_pack(max_variants_per_seed=50)
        by_seed = {row.get("seed_id") for row in variants}
        for seed_id in {
            "stage19_tyre_goodyear_exact",
            "stage19_tyre_bridgestone_exactish",
            "stage19_tyre_general_octavia",
            "stage19_calculator_exam_casio",
            "stage19_powerbank_iphone",
            "stage19_charger_fast_iphone",
            "stage19_ambiguous_unknown",
        }:
            self.assertIn(seed_id, by_seed)

    def test_records_have_required_fields_and_source(self) -> None:
        variants = generate_variants_for_training_pack(max_variants_per_seed=8)
        self.assertGreater(len(variants), 0)
        for row in variants:
            for key in ("case_id", "input", "expected", "seed_id", "variant_type", "source"):
                self.assertIn(key, row)
            self.assertEqual(row["source"], "local_variant_generator")

    def test_generator_is_deterministic(self) -> None:
        first = generate_variants_for_training_pack(max_variants_per_seed=10)
        second = generate_variants_for_training_pack(max_variants_per_seed=10)
        self.assertEqual(first, second)

    def test_max_variants_per_seed_is_respected(self) -> None:
        variants = generate_variants_for_training_pack(max_variants_per_seed=2)
        per_seed: dict[str, int] = {}
        for row in variants:
            seed_id = row["seed_id"]
            per_seed[seed_id] = per_seed.get(seed_id, 0) + 1
        self.assertTrue(per_seed)
        self.assertTrue(all(count <= 2 for count in per_seed.values()))

    def test_no_product_offer_price_or_affiliate_fields(self) -> None:
        variants = generate_variants_for_training_pack(max_variants_per_seed=30)
        all_keys = _collect_keys(variants)
        forbidden = {"product", "products", "offer", "offers", "price", "prices", "affiliate", "affiliate_url"}
        self.assertTrue(forbidden.isdisjoint(all_keys))

    def test_required_family_examples_are_present(self) -> None:
        variants = generate_variants_for_training_pack(max_variants_per_seed=50)
        merged = " ".join(row["input"].lower() for row in variants)
        self.assertIn("goodyar eficiency grim", merged)
        self.assertIn("brizestone touranza", merged)
        self.assertIn("kompiouteraki panellinies", merged)
        self.assertIn("power bank gia iphone", merged)
        self.assertIn("fortistis iphone", merged)
        self.assertIn("kati kalo gia to aftokinito", merged)

    def test_generated_variants_json_serializable(self) -> None:
        variants = generate_variants_for_training_pack(max_variants_per_seed=10)
        self.assertIsInstance(json.dumps(variants, sort_keys=True), str)


if __name__ == "__main__":
    unittest.main()
