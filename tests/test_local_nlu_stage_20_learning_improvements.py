from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.output_builder import build_local_nlu_intent  # noqa: E402
from picwise_nlu.training_pack import evaluate_stage_19_training_pack  # noqa: E402

_BASELINE_ACCURACY = 0.3077
_RESOLVED_STATUSES = {"intent_resolved", "specific_product_resolved", "general_intent_resolved"}
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


class LocalNLUStage20LearningImprovementsTests(unittest.TestCase):
    def test_stage_19_accuracy_improves_and_unsafe_remains_zero(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=200)
        self.assertGreater(report.get("accuracy", 0.0), _BASELINE_ACCURACY)
        self.assertEqual(report.get("unsafe_passes"), 0)
        self.assertGreaterEqual(report.get("manual_review_count", 0), 0)
        self.assertLessEqual(report.get("manual_review_count", 0), report.get("total", 0))

    def test_goodyear_messy_query_improves(self) -> None:
        intent = build_local_nlu_intent("goodyar eficiency grim 195 65 15 pio aneto")
        self.assertEqual(intent.get("category"), "car_tyres")
        self.assertIn("Goodyear", intent.get("brand_candidates", []))
        self.assertIn("EfficientGrip", intent.get("model_candidates", []))
        self.assertIn("comfort", intent.get("buying_priority", []))
        self.assertIn(intent.get("status"), _RESOLVED_STATUSES)

    def test_bridgestone_turanza_messy_query_improves(self) -> None:
        intent = build_local_nlu_intent("brizestone touranza iparxi 195 65 r15")
        self.assertEqual(intent.get("category"), "car_tyres")
        self.assertIn("Bridgestone", intent.get("brand_candidates", []))
        self.assertIn("Turanza", intent.get("model_candidates", []))
        self.assertIn(intent.get("status"), _RESOLVED_STATUSES)

    def test_octavia_general_tyre_query_improves(self) -> None:
        intent = build_local_nlu_intent("thelo aneta lastixa gia octavia 195 65 15")
        self.assertEqual(intent.get("category"), "car_tyres")
        self.assertIn("comfort", intent.get("buying_priority", []))
        self.assertEqual(intent.get("status"), "general_intent_resolved")

    def test_calculator_query_improves(self) -> None:
        intent = build_local_nlu_intent("kompiouteraki panellinies casio fx 991")
        self.assertEqual(intent.get("category"), "calculators")
        self.assertIn("Casio", intent.get("brand_candidates", []))
        self.assertIn("fx-991", intent.get("model_candidates", []))
        self.assertIn("exam_approved", intent.get("buying_priority", []))
        self.assertIn(intent.get("status"), _RESOLVED_STATUSES)

    def test_power_bank_query_improves(self) -> None:
        intent = build_local_nlu_intent("power bank gia iphone megali bataria 20000mah")
        self.assertEqual(intent.get("category"), "power_banks")
        self.assertEqual(intent.get("specs", {}).get("capacity_mah"), "20000")
        self.assertTrue(
            {"battery_life", "fast_charging"}.intersection(set(intent.get("buying_priority", [])))
        )
        self.assertIn(intent.get("status"), _RESOLVED_STATUSES)

    def test_charger_query_improves(self) -> None:
        intent = build_local_nlu_intent("fortistis iphone grigoros usb c")
        self.assertEqual(intent.get("category"), "chargers")
        self.assertIn("fast_charging", intent.get("buying_priority", []))
        self.assertEqual(intent.get("status"), "general_intent_resolved")

    def test_ambiguous_query_stays_review_safe(self) -> None:
        intent = build_local_nlu_intent("kati kalo gia to aftokinito")
        self.assertTrue(bool(intent.get("needs_review")))
        self.assertNotIn(intent.get("status"), _RESOLVED_STATUSES)

    def test_no_product_offer_price_affiliate_fields(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=30)
        keys = _collect_keys(report)
        self.assertTrue(_FORBIDDEN_FIELDS.isdisjoint(keys))


if __name__ == "__main__":
    unittest.main()
