from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.expected_dataset import get_expected_intent_cases  # noqa: E402


class LocalNLUExpectedDatasetTests(unittest.TestCase):
    def test_expected_dataset_non_empty(self) -> None:
        dataset = get_expected_intent_cases()
        self.assertIsInstance(dataset, list)
        self.assertGreater(len(dataset), 0)

    def test_every_case_has_input_and_expected(self) -> None:
        dataset = get_expected_intent_cases()
        for case in dataset:
            self.assertIn("input", case)
            self.assertIn("expected", case)
            self.assertTrue(case["input"])
            self.assertIsInstance(case["expected"], dict)

    def test_contains_required_case_types(self) -> None:
        dataset = get_expected_intent_cases()
        blob = json.dumps(dataset, sort_keys=True).lower()
        self.assertIn("tyre", blob)
        self.assertIn("calculator", blob)
        self.assertIn("power", blob)
        self.assertIn("ambiguous", blob)

    def test_json_serializable(self) -> None:
        dataset = get_expected_intent_cases()
        self.assertIsInstance(json.dumps(dataset, sort_keys=True), str)

    def test_no_fake_product_offer_fields(self) -> None:
        blob = json.dumps(get_expected_intent_cases(), sort_keys=True).lower()
        self.assertNotIn("offers", blob)
        self.assertNotIn("affiliate", blob)
        self.assertNotIn("price", blob)


if __name__ == "__main__":
    unittest.main()
