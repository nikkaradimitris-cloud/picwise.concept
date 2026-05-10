from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.output_builder import build_local_nlu_intent  # noqa: E402
from picwise_nlu.query_variant_generator import generate_variants_for_training_pack  # noqa: E402

_RESOLVED_STATUSES = {"intent_resolved", "specific_product_resolved", "general_intent_resolved"}


class LocalNLUStage19RealisticExamplesTests(unittest.TestCase):
    def test_realistic_example_inputs_exist_in_generated_variants(self) -> None:
        cases = generate_variants_for_training_pack(max_variants_per_seed=40)
        merged = " || ".join(row["input"].lower() for row in cases)
        self.assertIn("goodyar eficiency grim 195 65 15 pio aneto", merged)
        self.assertIn("brizestone touranza iparxi 195 65 r15", merged)
        self.assertIn("thelo aneta lastixa gia octavia 195 65 15", merged)
        self.assertIn("kompiouteraki panellinies casio fx 991", merged)
        self.assertIn("power bank gia iphone megali bataria 20000mah", merged)
        self.assertIn("fortistis iphone grigoros usb c", merged)
        self.assertIn("kati kalo gia to aftokinito", merged)

    def test_realistic_examples_produce_intent_payload_without_crash(self) -> None:
        examples = [
            "goodyar eficiency grim 195 65 15 pio aneto",
            "brizestone touranza iparxi 195 65 r15",
            "thelo aneta lastixa gia octavia 195 65 15",
            "kompiouteraki panellinies casio fx 991",
            "power bank gia iphone megali bataria 20000mah",
            "fortistis iphone grigoros usb c",
            "kati kalo gia to aftokinito",
        ]
        for query in examples:
            intent = build_local_nlu_intent(query)
            self.assertIsInstance(intent, dict)
            self.assertIn("status", intent)
            self.assertIn("confidence", intent)
            self.assertIn("needs_review", intent)

    def test_ambiguous_example_is_review_safe(self) -> None:
        intent = build_local_nlu_intent("kati kalo gia to aftokinito")
        status = str(intent.get("status", ""))
        confidence = float(intent.get("confidence", 0.0))
        self.assertTrue(
            bool(intent.get("needs_review"))
            or status not in _RESOLVED_STATUSES
            or confidence < 0.7
        )


if __name__ == "__main__":
    unittest.main()
