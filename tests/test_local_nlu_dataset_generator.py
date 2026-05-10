from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.dataset_generator import (  # noqa: E402
    generate_default_stage_11_dataset,
    generate_query_variants,
)


class LocalNLUDatasetGeneratorTests(unittest.TestCase):
    def test_default_dataset_is_non_empty(self) -> None:
        dataset = generate_default_stage_11_dataset()
        self.assertIsInstance(dataset, list)
        self.assertGreater(len(dataset), 0)

    def test_generated_items_have_required_fields(self) -> None:
        seed = {
            "case_id": "stage11_tyre_goodyear",
            "input": "Goodyear EfficientGrip Performance 2 195/65 R15 comfort",
            "expected": {"category": "car_tyres"},
        }
        items = generate_query_variants(seed)
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertIn("input", item)
            self.assertIn("expected", item)
            self.assertIn("case_id", item)
            self.assertEqual(item["source"], "local_generated")

    def test_dataset_is_deterministic(self) -> None:
        first = generate_default_stage_11_dataset()
        second = generate_default_stage_11_dataset()
        self.assertEqual(first, second)

    def test_no_product_offer_price_or_affiliate_fields(self) -> None:
        dataset = generate_default_stage_11_dataset()
        serialized = json.dumps(dataset, sort_keys=True).lower()
        self.assertNotIn("offers", serialized)
        self.assertNotIn("affiliate", serialized)
        self.assertNotIn("price", serialized)

    def test_includes_required_case_families(self) -> None:
        dataset = generate_default_stage_11_dataset()
        merged = " ".join(item["input"].lower() for item in dataset)
        self.assertIn("goodyar", merged)
        self.assertIn("brizestone", merged)
        self.assertIn("kompiouteraki", merged)
        self.assertIn("powerbank", merged)


if __name__ == "__main__":
    unittest.main()
