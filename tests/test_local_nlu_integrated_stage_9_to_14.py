from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.evaluation_runner import evaluate_local_nlu_cases  # noqa: E402
from picwise_nlu.mistake_collector import collect_mistakes  # noqa: E402
from picwise_nlu.output_builder import build_local_nlu_intent  # noqa: E402


class LocalNLUIntegratedStage9To14Tests(unittest.TestCase):
    def test_build_intent_for_messy_tyre_query(self) -> None:
        intent = build_local_nlu_intent("goodyar eficiency grim 195 65 15 aneto")
        self.assertEqual(intent["category"], "car_tyres")
        self.assertIn("Goodyear", intent["brand_candidates"])

    def test_build_intent_for_calculator_query(self) -> None:
        intent = build_local_nlu_intent("kompiouteraki casio gia panellinies fx 991")
        self.assertEqual(intent["category"], "calculators")
        self.assertIn("Casio", intent["brand_candidates"])

    def test_build_intent_for_powerbank_query(self) -> None:
        intent = build_local_nlu_intent("power bank iphone 20000mah fast charge")
        self.assertEqual(intent["category"], "power_banks")
        self.assertEqual(intent["specs"].get("capacity_mah"), "20000")

    def test_evaluate_default_dataset_and_collect_mistakes(self) -> None:
        report = evaluate_local_nlu_cases()
        mistakes = collect_mistakes(report)
        self.assertEqual(len(mistakes), report["failed"])
        self.assertGreaterEqual(report["total"], 1)

    def test_no_api_claude_or_live_llm_requirement(self) -> None:
        intent = build_local_nlu_intent("goodyear efficientgrip 195/65 r15 comfort")
        blob = json.dumps(intent, sort_keys=True).lower()
        self.assertNotIn("claude", blob)
        self.assertNotIn("openai", blob)
        self.assertNotIn("api_key", blob)
        self.assertNotIn("live_llm", blob)

    def test_no_product_or_offer_result_fields(self) -> None:
        intent = build_local_nlu_intent("goodyear efficientgrip 195/65 r15 comfort")
        for forbidden in ["products", "offers", "offer_resolver", "price", "affiliate_url"]:
            self.assertNotIn(forbidden, intent)


if __name__ == "__main__":
    unittest.main()
