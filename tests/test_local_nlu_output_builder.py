from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu import validate_local_nlu_intent  # noqa: E402
from picwise_nlu.output_builder import build_local_nlu_intent  # noqa: E402


class LocalNLUOutputBuilderTests(unittest.TestCase):
    def test_build_local_nlu_intent_is_contract_valid(self) -> None:
        intent = build_local_nlu_intent("goodyear efficientgrip 195/65 r15 comfort")
        validated = validate_local_nlu_intent(intent)
        self.assertEqual(validated["source"], "local_nlu")
        self.assertEqual(validated["schema_version"], "1.0.0")

    def test_messy_goodyear_query(self) -> None:
        intent = build_local_nlu_intent("goodyar eficiency grim 195 65 15 aneto")
        self.assertEqual(intent["category"], "car_tyres")
        self.assertIn("Goodyear", intent["brand_candidates"])
        self.assertTrue(
            "EfficientGrip" in intent["model_candidates"]
            or "EfficientGrip Performance 2" in intent["model_candidates"]
        )
        self.assertEqual(intent["specs"].get("width"), "195")
        self.assertEqual(intent["specs"].get("profile"), "65")
        self.assertEqual(intent["specs"].get("rim"), "R15")
        self.assertIn("comfort", intent["buying_priority"])
        self.assertEqual(intent["source"], "local_nlu")
        self.assertIsInstance(json.dumps(intent, sort_keys=True), str)

    def test_bridgestone_turanza_low_noise_query(self) -> None:
        intent = build_local_nlu_intent("brizestone touransa 195/65/15 isixo")
        self.assertIn("Bridgestone", intent["brand_candidates"])
        self.assertIn("Turanza", intent["model_candidates"])
        self.assertIn("low_noise", intent["buying_priority"])

    def test_calculator_exam_query(self) -> None:
        intent = build_local_nlu_intent("kompiouteraki casio gia panellinies fx 991")
        self.assertEqual(intent["category"], "calculators")
        self.assertIn("Casio", intent["brand_candidates"])
        self.assertIn("fx-991", intent["model_candidates"])
        self.assertIn("exam_approved", intent["buying_priority"])

    def test_powerbank_query(self) -> None:
        intent = build_local_nlu_intent("power bank iphone 20000mah fast charge")
        self.assertEqual(intent["category"], "power_banks")
        self.assertEqual(intent["specs"].get("capacity_mah"), "20000")
        self.assertTrue(
            "fast_charging" in intent["buying_priority"]
            or "battery_life" in intent["buying_priority"]
        )

    def test_unknown_query_safe_review_status(self) -> None:
        intent = build_local_nlu_intent("zzzz asdf ???")
        self.assertIn(
            intent["status"],
            {"manual_review_required", "insufficient_data", "no_safe_result", "ambiguous_needs_review", "invalid_intent"},
        )
        self.assertTrue(intent["needs_review"])

    def test_no_product_offer_price_affiliate_fields(self) -> None:
        intent = build_local_nlu_intent("goodyear efficientgrip 195/65 r15 comfort")
        forbidden = {"products", "offers", "price", "prices", "affiliate_url", "offer_resolver"}
        self.assertTrue(forbidden.isdisjoint(intent.keys()))


if __name__ == "__main__":
    unittest.main()
