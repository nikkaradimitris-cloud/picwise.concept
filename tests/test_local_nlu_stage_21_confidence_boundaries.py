from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.confidence import resolve_safe_status  # noqa: E402
from picwise_nlu.output_builder import build_local_nlu_intent  # noqa: E402
from picwise_nlu.training_pack import evaluate_stage_19_training_pack  # noqa: E402

_RESOLVED_SPECIFIC = {"specific_product_resolved"}
_RESOLVED_ANY = {"intent_resolved", "specific_product_resolved", "general_intent_resolved"}
_REVIEW_STATUSES = {
    "ambiguous_needs_review",
    "manual_review_required",
    "insufficient_data",
    "no_safe_result",
    "invalid_intent",
}


class LocalNLUStage21ConfidenceBoundariesTests(unittest.TestCase):
    def test_strong_exact_tyre_query_higher_confidence_than_brand_only(self) -> None:
        strong = build_local_nlu_intent("goodyear efficientgrip 195/65 r15 comfort")
        weak = build_local_nlu_intent("goodyear")
        self.assertGreater(float(strong.get("confidence", 0.0)), float(weak.get("confidence", 0.0)))
        self.assertIn(strong.get("status"), _RESOLVED_ANY)
        self.assertNotIn(weak.get("status"), _RESOLVED_SPECIFIC)

    def test_strong_calculator_query_higher_confidence_than_casio_alone(self) -> None:
        strong = build_local_nlu_intent("casio fx 991 calculator for panellinies")
        weak = build_local_nlu_intent("casio")
        self.assertGreater(float(strong.get("confidence", 0.0)), float(weak.get("confidence", 0.0)))
        self.assertIn(strong.get("status"), _RESOLVED_ANY)
        self.assertNotIn(weak.get("status"), _RESOLVED_SPECIFIC)

    def test_strong_powerbank_query_higher_confidence_than_iphone_alone(self) -> None:
        strong = build_local_nlu_intent("power bank iphone 20000mah fast charge")
        weak = build_local_nlu_intent("iphone")
        self.assertGreater(float(strong.get("confidence", 0.0)), float(weak.get("confidence", 0.0)))
        self.assertIn(strong.get("status"), _RESOLVED_ANY)
        self.assertNotIn(weak.get("status"), _RESOLVED_SPECIFIC)

    def test_specific_product_resolved_requires_enough_evidence(self) -> None:
        brand_only = build_local_nlu_intent("goodyear")
        model_only = build_local_nlu_intent("efficientgrip")
        size_only = build_local_nlu_intent("195 65 15")
        for intent in (brand_only, model_only, size_only):
            self.assertNotIn(intent.get("status"), _RESOLVED_SPECIFIC)

    def test_general_intent_resolved_allowed_for_clear_safe_category_priority(self) -> None:
        intent = build_local_nlu_intent("fast charger iphone usb c")
        self.assertEqual(intent.get("category"), "chargers")
        self.assertIn("fast_charging", intent.get("buying_priority", []))
        self.assertEqual(intent.get("status"), "general_intent_resolved")
        self.assertFalse(bool(intent.get("needs_review")))

    def test_unsafe_statuses_force_needs_review_true(self) -> None:
        for status in _REVIEW_STATUSES:
            with self.subTest(status=status):
                merged = resolve_safe_status({"status": status, "reason_codes": []}, 0.95, raw_query="x")
                self.assertTrue(bool(merged.get("needs_review")))

    def test_low_confidence_cannot_pass_as_resolved(self) -> None:
        merged = resolve_safe_status(
            {
                "query_type": "general_intent",
                "category": "car_tyres",
                "brand_candidates": ["Goodyear"],
                "model_candidates": [],
                "specs": {},
                "buying_priority": [],
                "reason_codes": [],
            },
            0.2,
            raw_query="goodyear tyres",
        )
        self.assertNotIn(merged.get("status"), _RESOLVED_ANY)
        self.assertTrue(bool(merged.get("needs_review")))

    def test_unsafe_passes_remain_zero_in_stage19_20_evaluation(self) -> None:
        report = evaluate_stage_19_training_pack(max_variants_per_seed=200)
        self.assertEqual(report.get("unsafe_passes"), 0)


if __name__ == "__main__":
    unittest.main()
